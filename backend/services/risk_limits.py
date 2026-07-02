"""M17 — Risk Limits Engine (pure Python, in-memory).

Pre-trade risk management: 12 limit types, hard rejection and soft warning
thresholds, configurable per portfolio or per strategy.  Used by the order
management and paper-trading layers before any order is accepted.

No SQLAlchemy, no external libraries — stdlib + dataclasses only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class LimitType(str, Enum):
    MAX_POSITION_SIZE = "MAX_POSITION_SIZE"
    MAX_ORDER_SIZE = "MAX_ORDER_SIZE"
    MAX_SECTOR_WEIGHT = "MAX_SECTOR_WEIGHT"
    MAX_COUNTRY_WEIGHT = "MAX_COUNTRY_WEIGHT"
    MAX_LEVERAGE = "MAX_LEVERAGE"
    MAX_GROSS_LEVERAGE = "MAX_GROSS_LEVERAGE"
    MAX_NET_LEVERAGE = "MAX_NET_LEVERAGE"
    MAX_DRAWDOWN = "MAX_DRAWDOWN"
    MAX_TURNOVER_DAILY = "MAX_TURNOVER_DAILY"
    MAX_BETA = "MAX_BETA"
    MAX_VAR = "MAX_VAR"
    MAX_CONCENTRATION = "MAX_CONCENTRATION"


class LimitSeverity(str, Enum):
    HARD = "HARD"
    SOFT = "SOFT"


class CheckResult(str, Enum):
    PASS = "PASS"
    SOFT_WARNING = "SOFT_WARNING"
    HARD_REJECT = "HARD_REJECT"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class RiskLimit:
    """Configuration for a single risk limit.

    Args:
        limit_id: Unique identifier.
        limit_type: Type of risk limit.
        hard_limit: Value at or above which the order is rejected.
        soft_limit: Value at or above which a warning is raised.
        severity: HARD or SOFT (used when only one threshold is set).
        description: Human-readable description.
        enabled: Whether the limit is active.
        asset_filter: Optional dict with filter criteria (e.g. {"sector": "TECHNOLOGY"}).
    """

    limit_id: str
    limit_type: LimitType
    hard_limit: float
    soft_limit: float
    severity: LimitSeverity = LimitSeverity.HARD
    description: str = ""
    enabled: bool = True
    asset_filter: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "limit_id": self.limit_id,
            "limit_type": self.limit_type.value,
            "hard_limit": self.hard_limit,
            "soft_limit": self.soft_limit,
            "severity": self.severity.value,
            "description": self.description,
            "enabled": self.enabled,
            "asset_filter": dict(self.asset_filter),
        }


@dataclass
class LimitViolation:
    """Details of a single limit violation.

    Args:
        limit_id: The limit that was violated.
        limit_type: Type of the violated limit.
        result: SOFT_WARNING or HARD_REJECT.
        current_value: The computed value that triggered the violation.
        limit_value: The threshold that was breached.
        message: Human-readable explanation.
    """

    limit_id: str
    limit_type: LimitType
    result: CheckResult
    current_value: float
    limit_value: float
    message: str

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "limit_id": self.limit_id,
            "limit_type": self.limit_type.value,
            "result": self.result.value,
            "current_value": round(self.current_value, 6),
            "limit_value": round(self.limit_value, 6),
            "message": self.message,
        }


@dataclass
class PreTradeCheckResult:
    """Aggregated result of all pre-trade risk checks.

    Args:
        passed: True if no HARD violations were triggered.
        result: Overall CheckResult (PASS, SOFT_WARNING, or HARD_REJECT).
        violations: List of all limit violations.
        hard_violations: Violations that block the order.
        soft_violations: Warnings that do not block the order.
        order_allowed: Whether the order is permitted to proceed.
    """

    passed: bool
    result: CheckResult
    violations: List[LimitViolation]
    hard_violations: List[LimitViolation]
    soft_violations: List[LimitViolation]
    order_allowed: bool

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "passed": self.passed,
            "result": self.result.value,
            "order_allowed": self.order_allowed,
            "violations": [v.to_dict() for v in self.violations],
            "hard_violations": [v.to_dict() for v in self.hard_violations],
            "soft_violations": [v.to_dict() for v in self.soft_violations],
        }


# ---------------------------------------------------------------------------
# Risk context (provided by caller)
# ---------------------------------------------------------------------------

@dataclass
class RiskContext:
    """Portfolio state snapshot for pre-trade evaluation.

    Args:
        nav: Net asset value in USD.
        cash: Available cash.
        current_positions: Dict mapping ticker → current signed quantity.
        current_market_values: Dict mapping ticker → current market value.
        sector_weights: Dict mapping sector → portfolio weight (0–1).
        country_weights: Dict mapping country → portfolio weight (0–1).
        gross_leverage: Current gross leverage ratio.
        net_leverage: Current net leverage ratio.
        portfolio_beta: Current portfolio beta to benchmark.
        portfolio_var_pct: Current portfolio VaR (95%, 1-day) as decimal.
        current_drawdown: Current drawdown from HWM as decimal (negative).
        daily_turnover: Turnover executed today as fraction of NAV.
        top_position_weight: Largest single-position weight as decimal.
    """

    nav: float
    cash: float
    current_positions: Dict[str, float] = field(default_factory=dict)
    current_market_values: Dict[str, float] = field(default_factory=dict)
    sector_weights: Dict[str, float] = field(default_factory=dict)
    country_weights: Dict[str, float] = field(default_factory=dict)
    gross_leverage: float = 0.0
    net_leverage: float = 0.0
    portfolio_beta: float = 0.0
    portfolio_var_pct: float = 0.0
    current_drawdown: float = 0.0
    daily_turnover: float = 0.0
    top_position_weight: float = 0.0


@dataclass
class ProposedOrder:
    """An order being evaluated by the risk engine.

    Args:
        ticker: Instrument symbol.
        side: "BUY" or "SELL".
        quantity: Proposed quantity.
        price: Estimated execution price.
        sector: Instrument's sector (optional, for sector weight checks).
        country: Instrument's country (optional, for country weight checks).
        asset_beta: Instrument beta (optional, for portfolio beta checks).
    """

    ticker: str
    side: str
    quantity: float
    price: float
    sector: Optional[str] = None
    country: Optional[str] = None
    asset_beta: float = 1.0


# ---------------------------------------------------------------------------
# Risk Limits Engine
# ---------------------------------------------------------------------------

import uuid as _uuid_mod


class RiskLimitsEngine:
    """Institutional pre-trade risk management engine (pure Python).

    Evaluates proposed orders against a configured set of risk limits and
    returns PASS / SOFT_WARNING / HARD_REJECT decisions.

    Supports 12 limit types:
        MAX_POSITION_SIZE, MAX_ORDER_SIZE, MAX_SECTOR_WEIGHT,
        MAX_COUNTRY_WEIGHT, MAX_LEVERAGE, MAX_GROSS_LEVERAGE,
        MAX_NET_LEVERAGE, MAX_DRAWDOWN, MAX_TURNOVER_DAILY,
        MAX_BETA, MAX_VAR, MAX_CONCENTRATION.
    """

    def __init__(self) -> None:
        self._limits: Dict[str, RiskLimit] = {}

    # ------------------------------------------------------------------
    # Limit configuration
    # ------------------------------------------------------------------

    def add_limit(
        self,
        limit_type: LimitType,
        hard_limit: float,
        soft_limit: Optional[float] = None,
        *,
        limit_id: Optional[str] = None,
        description: str = "",
        asset_filter: Optional[Dict] = None,
    ) -> RiskLimit:
        """Register a new risk limit.

        Args:
            limit_type: Type of limit.
            hard_limit: Hard rejection threshold.
            soft_limit: Soft warning threshold; defaults to 90% of hard_limit.
            limit_id: Optional explicit ID.
            description: Human-readable description.
            asset_filter: Optional filter for limit applicability.

        Returns:
            Created RiskLimit.
        """
        lid = limit_id or str(_uuid_mod.uuid4())
        sl = soft_limit if soft_limit is not None else hard_limit * 0.9
        lim = RiskLimit(
            limit_id=lid,
            limit_type=limit_type,
            hard_limit=hard_limit,
            soft_limit=sl,
            description=description or f"{limit_type.value} limit",
            asset_filter=asset_filter or {},
        )
        self._limits[lid] = lim
        return lim

    def remove_limit(self, limit_id: str) -> None:
        """Remove a limit by ID.

        Args:
            limit_id: ID of the limit to remove.

        Raises:
            KeyError: If limit_id not found.
        """
        if limit_id not in self._limits:
            raise KeyError(f"Limit {limit_id!r} not found")
        del self._limits[limit_id]

    def enable_limit(self, limit_id: str) -> None:
        """Enable a disabled limit.

        Args:
            limit_id: Limit identifier.
        """
        self._limits[limit_id].enabled = True

    def disable_limit(self, limit_id: str) -> None:
        """Disable a limit without removing it.

        Args:
            limit_id: Limit identifier.
        """
        self._limits[limit_id].enabled = False

    def get_all_limits(self) -> List[RiskLimit]:
        """Return all registered limits.

        Returns:
            List of RiskLimit objects.
        """
        return list(self._limits.values())

    # ------------------------------------------------------------------
    # Pre-trade check
    # ------------------------------------------------------------------

    def check_order(
        self,
        order: ProposedOrder,
        context: RiskContext,
    ) -> PreTradeCheckResult:
        """Run all enabled pre-trade risk checks for a proposed order.

        Args:
            order: The proposed order to evaluate.
            context: Current portfolio state.

        Returns:
            PreTradeCheckResult with pass/fail and all violation details.
        """
        violations: List[LimitViolation] = []

        for lim in self._limits.values():
            if not lim.enabled:
                continue
            violation = self._evaluate_limit(lim, order, context)
            if violation is not None:
                violations.append(violation)

        hard = [v for v in violations if v.result == CheckResult.HARD_REJECT]
        soft = [v for v in violations if v.result == CheckResult.SOFT_WARNING]

        if hard:
            overall = CheckResult.HARD_REJECT
        elif soft:
            overall = CheckResult.SOFT_WARNING
        else:
            overall = CheckResult.PASS

        return PreTradeCheckResult(
            passed=len(hard) == 0,
            result=overall,
            violations=violations,
            hard_violations=hard,
            soft_violations=soft,
            order_allowed=len(hard) == 0,
        )

    def _evaluate_limit(
        self,
        lim: RiskLimit,
        order: ProposedOrder,
        ctx: RiskContext,
    ) -> Optional[LimitViolation]:
        """Evaluate a single limit against the proposed order + context.

        Returns a LimitViolation if breached, else None.
        """
        lt = lim.limit_type

        if lt == LimitType.MAX_ORDER_SIZE:
            value = order.quantity * order.price
            return self._check(lim, value, f"Order value ${value:.2f} vs limit ${lim.hard_limit:.2f}")

        elif lt == LimitType.MAX_POSITION_SIZE:
            is_buy = order.side.upper() in ("BUY", "BUY_TO_COVER")
            current_qty = ctx.current_positions.get(order.ticker, 0.0)
            new_qty = current_qty + (order.quantity if is_buy else -order.quantity)
            position_value = abs(new_qty) * order.price
            return self._check(lim, position_value,
                f"Position value ${position_value:.2f} for {order.ticker} vs limit ${lim.hard_limit:.2f}")

        elif lt == LimitType.MAX_SECTOR_WEIGHT:
            if order.sector is None:
                return None
            order_value = order.quantity * order.price
            current_weight = ctx.sector_weights.get(order.sector, 0.0)
            incremental_weight = order_value / ctx.nav if ctx.nav > 0 else 0.0
            new_weight = current_weight + incremental_weight
            return self._check(lim, new_weight,
                f"Sector {order.sector} weight {new_weight:.2%} vs limit {lim.hard_limit:.2%}")

        elif lt == LimitType.MAX_COUNTRY_WEIGHT:
            if order.country is None:
                return None
            order_value = order.quantity * order.price
            current_weight = ctx.country_weights.get(order.country, 0.0)
            incremental_weight = order_value / ctx.nav if ctx.nav > 0 else 0.0
            new_weight = current_weight + incremental_weight
            return self._check(lim, new_weight,
                f"Country {order.country} weight {new_weight:.2%} vs limit {lim.hard_limit:.2%}")

        elif lt == LimitType.MAX_LEVERAGE:
            is_buy = order.side.upper() in ("BUY", "BUY_TO_COVER")
            order_value = order.quantity * order.price
            if is_buy:
                new_gross = ctx.gross_leverage + order_value / ctx.nav
            else:
                new_gross = ctx.gross_leverage
            return self._check(lim, new_gross,
                f"Leverage {new_gross:.2f}x vs limit {lim.hard_limit:.2f}x")

        elif lt == LimitType.MAX_GROSS_LEVERAGE:
            order_value = order.quantity * order.price
            new_gross = ctx.gross_leverage + order_value / ctx.nav if ctx.nav > 0 else 0.0
            return self._check(lim, new_gross,
                f"Gross leverage {new_gross:.2f}x vs limit {lim.hard_limit:.2f}x")

        elif lt == LimitType.MAX_NET_LEVERAGE:
            is_buy = order.side.upper() in ("BUY", "BUY_TO_COVER")
            order_value = order.quantity * order.price / ctx.nav if ctx.nav > 0 else 0.0
            new_net = ctx.net_leverage + (order_value if is_buy else -order_value)
            return self._check(lim, abs(new_net),
                f"Net leverage |{new_net:.2f}|x vs limit {lim.hard_limit:.2f}x")

        elif lt == LimitType.MAX_DRAWDOWN:
            value = abs(ctx.current_drawdown)
            return self._check(lim, value,
                f"Drawdown {ctx.current_drawdown:.2%} vs limit {lim.hard_limit:.2%}")

        elif lt == LimitType.MAX_TURNOVER_DAILY:
            order_turnover = (order.quantity * order.price) / ctx.nav if ctx.nav > 0 else 0.0
            new_turnover = ctx.daily_turnover + order_turnover
            return self._check(lim, new_turnover,
                f"Daily turnover {new_turnover:.2%} vs limit {lim.hard_limit:.2%}")

        elif lt == LimitType.MAX_BETA:
            is_buy = order.side.upper() in ("BUY", "BUY_TO_COVER")
            order_weight = order.quantity * order.price / ctx.nav if ctx.nav > 0 else 0.0
            delta_beta = order_weight * order.asset_beta * (1.0 if is_buy else -1.0)
            new_beta = ctx.portfolio_beta + delta_beta
            return self._check(lim, abs(new_beta),
                f"Portfolio beta |{new_beta:.2f}| vs limit {lim.hard_limit:.2f}")

        elif lt == LimitType.MAX_VAR:
            return self._check(lim, ctx.portfolio_var_pct,
                f"Portfolio VaR {ctx.portfolio_var_pct:.2%} vs limit {lim.hard_limit:.2%}")

        elif lt == LimitType.MAX_CONCENTRATION:
            order_value = order.quantity * order.price
            current_mv = ctx.current_market_values.get(order.ticker, 0.0)
            new_mv = current_mv + order_value
            position_weight = new_mv / ctx.nav if ctx.nav > 0 else 0.0
            new_top = max(ctx.top_position_weight, position_weight)
            return self._check(lim, new_top,
                f"Top position weight {new_top:.2%} for {order.ticker} vs limit {lim.hard_limit:.2%}")

        return None

    def _check(
        self,
        lim: RiskLimit,
        value: float,
        message: str,
    ) -> Optional[LimitViolation]:
        if value >= lim.hard_limit:
            return LimitViolation(
                limit_id=lim.limit_id,
                limit_type=lim.limit_type,
                result=CheckResult.HARD_REJECT,
                current_value=value,
                limit_value=lim.hard_limit,
                message=f"HARD REJECT: {message}",
            )
        if value >= lim.soft_limit:
            return LimitViolation(
                limit_id=lim.limit_id,
                limit_type=lim.limit_type,
                result=CheckResult.SOFT_WARNING,
                current_value=value,
                limit_value=lim.soft_limit,
                message=f"SOFT WARNING: {message}",
            )
        return None

    # ------------------------------------------------------------------
    # Convenience builders
    # ------------------------------------------------------------------

    @classmethod
    def default_limits(cls) -> "RiskLimitsEngine":
        """Create a RiskLimitsEngine with a standard institutional limit set.

        Returns:
            RiskLimitsEngine configured with 8 default limits.
        """
        eng = cls()
        eng.add_limit(LimitType.MAX_POSITION_SIZE, hard_limit=1_000_000, soft_limit=800_000,
                      description="Max single position $1M")
        eng.add_limit(LimitType.MAX_ORDER_SIZE, hard_limit=500_000, soft_limit=400_000,
                      description="Max single order $500K")
        eng.add_limit(LimitType.MAX_SECTOR_WEIGHT, hard_limit=0.40, soft_limit=0.35,
                      description="Max sector weight 40%")
        eng.add_limit(LimitType.MAX_COUNTRY_WEIGHT, hard_limit=0.60, soft_limit=0.50,
                      description="Max country weight 60%")
        eng.add_limit(LimitType.MAX_GROSS_LEVERAGE, hard_limit=3.0, soft_limit=2.5,
                      description="Max gross leverage 3x")
        eng.add_limit(LimitType.MAX_DRAWDOWN, hard_limit=0.20, soft_limit=0.15,
                      description="Max drawdown 20%")
        eng.add_limit(LimitType.MAX_CONCENTRATION, hard_limit=0.20, soft_limit=0.15,
                      description="Max single-position weight 20%")
        eng.add_limit(LimitType.MAX_VAR, hard_limit=0.03, soft_limit=0.025,
                      description="Max VaR (95%, 1-day) 3%")
        return eng


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_risk_limits: Optional[RiskLimitsEngine] = None


def get_risk_limits_engine() -> RiskLimitsEngine:
    """Return the singleton RiskLimitsEngine instance.

    Returns:
        Shared RiskLimitsEngine with default limits applied.
    """
    global _default_risk_limits
    if _default_risk_limits is None:
        _default_risk_limits = RiskLimitsEngine.default_limits()
    return _default_risk_limits
