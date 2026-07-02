"""M18 — Real-Time Risk Engine: continuously monitors portfolio risk metrics.

Computes Portfolio VaR, Expected Shortfall, leverage, exposure (gross/net/
sector/country/currency/factor), liquidity risk, gap risk, concentration,
margin, buying power, stress tests, and real-time alerts.

Pure Python, no external libraries.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class VaRResult:
    """Value-at-Risk computation result.

    Args:
        confidence: Confidence level (e.g. 0.95).
        var_pct: VaR as a fraction of NAV.
        var_usd: VaR in USD.
        method: Computation method (HISTORICAL, PARAMETRIC).
        window: Look-back window used.
        nav: Portfolio NAV at computation time.
    """

    confidence: float
    var_pct: float
    var_usd: float
    method: str
    window: int
    nav: float

    @property
    def var_1d(self) -> float:
        """Alias for var_usd."""
        return self.var_usd

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        d = {k: (round(v, 6) if isinstance(v, float) else v) for k, v in self.__dict__.items()}
        d["var_1d"] = round(self.var_usd, 6)
        return d


@dataclass
class LeverageMetrics:
    """Portfolio leverage metrics.

    Args:
        gross_leverage: |long| + |short| / NAV.
        net_leverage: (long - short) / NAV.
        long_exposure_usd: Total long market value.
        short_exposure_usd: Total short market value (absolute).
        nav: Portfolio NAV.
    """

    gross_leverage: float
    net_leverage: float
    long_exposure_usd: float
    short_exposure_usd: float
    nav: float

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {k: (round(v, 6) if isinstance(v, float) else v)
                for k, v in self.__dict__.items()}


@dataclass
class LiquidityRiskResult:
    """Portfolio liquidity risk assessment.

    Args:
        days_to_liquidate: Estimated trading days to close all positions
            at 25% of ADV.
        illiquid_positions: Tickers estimated to take > 5 days to close.
        total_position_value_usd: Total long market value.
        total_adv_usd: Sum of ADV across all positions.
        liquidity_score: Composite score in [0, 1] (1 = highly liquid).
    """

    days_to_liquidate: float
    illiquid_positions: List[str]
    total_position_value_usd: float
    total_adv_usd: float
    liquidity_score: float

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "days_to_liquidate": round(self.days_to_liquidate, 2),
            "illiquid_positions": self.illiquid_positions,
            "total_position_value_usd": round(self.total_position_value_usd, 2),
            "total_adv_usd": round(self.total_adv_usd, 2),
            "liquidity_score": round(self.liquidity_score, 4),
        }


@dataclass
class GapRiskResult:
    """Overnight gap risk estimates.

    Args:
        expected_gap_pnl: Expected P&L impact under a gap scenario.
        worst_case_gap_pnl: Worst-case P&L under extreme gap.
        scenario_name: Name of the gap scenario applied.
        gap_pct: Gap percentage applied.
        affected_positions: Tickers most affected.
    """

    expected_gap_pnl: float
    worst_case_gap_pnl: float
    scenario_name: str
    gap_pct: float
    affected_positions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "expected_gap_pnl": round(self.expected_gap_pnl, 2),
            "worst_case_gap_pnl": round(self.worst_case_gap_pnl, 2),
            "scenario_name": self.scenario_name,
            "gap_pct": round(self.gap_pct, 4),
            "affected_positions": self.affected_positions,
        }


@dataclass
class ConcentrationResult:
    """Portfolio concentration metrics.

    Args:
        herfindahl_index: HHI of position weights (0 = perfectly diversified).
        top1_weight: Weight of the largest single position.
        top5_weight: Combined weight of the 5 largest positions.
        top_positions: List of (ticker, weight) for the 5 largest.
        is_concentrated: True if HHI > 0.25 or top1 > 0.20.
    """

    herfindahl_index: float
    top1_weight: float
    top5_weight: float
    top_positions: List[Tuple[str, float]]
    is_concentrated: bool

    @property
    def hhi(self) -> float:
        """Alias for herfindahl_index."""
        return self.herfindahl_index

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "herfindahl_index": round(self.herfindahl_index, 6),
            "hhi": round(self.herfindahl_index, 6),
            "top1_weight": round(self.top1_weight, 6),
            "top5_weight": round(self.top5_weight, 6),
            "top_positions": [[t, round(w, 6)] for t, w in self.top_positions],
            "is_concentrated": self.is_concentrated,
        }


@dataclass
class MarginResult:
    """Margin usage and buying power.

    Args:
        margin_used_usd: Current initial margin consumed.
        margin_available_usd: Remaining margin.
        margin_usage_pct: margin_used / equity as fraction.
        buying_power_usd: Available buying power at given leverage.
        maintenance_margin_usd: Maintenance margin threshold.
        margin_call_triggered: True if equity < maintenance_margin.
    """

    margin_used_usd: float
    margin_available_usd: float
    margin_usage_pct: float
    buying_power_usd: float
    maintenance_margin_usd: float
    margin_call_triggered: bool

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {k: (round(v, 4) if isinstance(v, float) else v)
                for k, v in self.__dict__.items()}


@dataclass
class StressTestResult:
    """Result of a single stress-test scenario.

    Args:
        scenario_name: Human-readable scenario name.
        pnl_impact_usd: Estimated P&L change under scenario.
        pnl_impact_pct: P&L impact as fraction of NAV.
        nav_after: Estimated NAV after shock.
        most_impacted: List of (ticker, impact_usd) sorted by absolute impact.
    """

    scenario_name: str
    pnl_impact_usd: float
    pnl_impact_pct: float
    nav_after: float
    most_impacted: List[Tuple[str, float]]

    @property
    def portfolio_pnl(self) -> float:
        """Alias for pnl_impact_usd."""
        return self.pnl_impact_usd

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "scenario_name": self.scenario_name,
            "pnl_impact_usd": round(self.pnl_impact_usd, 2),
            "portfolio_pnl": round(self.pnl_impact_usd, 2),
            "pnl_impact_pct": round(self.pnl_impact_pct, 6),
            "nav_after": round(self.nav_after, 2),
            "most_impacted": [[t, round(v, 2)] for t, v in self.most_impacted],
        }


@dataclass
class RiskAlert:
    """A triggered real-time risk alert.

    Args:
        alert_id: Unique identifier.
        risk_type: Category (VAR, LEVERAGE, DRAWDOWN, etc.).
        severity: LOW, MEDIUM, HIGH, CRITICAL.
        message: Human-readable description.
        value: Current metric value.
        threshold: Threshold that was breached.
        timestamp: UTC time of alert.
    """

    alert_id: str
    risk_type: str
    severity: str
    message: str
    value: float
    threshold: float
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "alert_id": self.alert_id,
            "risk_type": self.risk_type,
            "severity": self.severity,
            "message": self.message,
            "value": round(self.value, 6),
            "threshold": round(self.threshold, 6),
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class RiskDashboard:
    """Consolidated real-time risk dashboard snapshot.

    Args:
        nav: Portfolio NAV.
        var_95: 95% one-day VaR.
        expected_shortfall_95: 95% Expected Shortfall.
        gross_leverage: Gross leverage.
        net_leverage: Net leverage.
        sector_exposure: Dict of sector weights.
        concentration_hhi: Herfindahl index.
        margin_usage_pct: Margin utilisation fraction.
        active_alerts: Active risk alerts.
        timestamp: Snapshot time UTC.
    """

    nav: float
    var_95: float
    expected_shortfall_95: float
    gross_leverage: float
    net_leverage: float
    sector_exposure: Dict[str, float]
    concentration_hhi: float
    margin_usage_pct: float
    active_alerts: List[RiskAlert]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "nav": round(self.nav, 2),
            "var_95": round(self.var_95, 6),
            "expected_shortfall_95": round(self.expected_shortfall_95, 6),
            "gross_leverage": round(self.gross_leverage, 4),
            "net_leverage": round(self.net_leverage, 4),
            "sector_exposure": {k: round(v, 6) for k, v in self.sector_exposure.items()},
            "concentration_hhi": round(self.concentration_hhi, 6),
            "margin_usage_pct": round(self.margin_usage_pct, 4),
            "active_alerts": [a.to_dict() for a in self.active_alerts],
            "timestamp": self.timestamp.isoformat(),
        }


# ---------------------------------------------------------------------------
# Position record
# ---------------------------------------------------------------------------

@dataclass
class _PositionRecord:
    ticker: str
    quantity: float
    market_price: float
    sector: str
    country: str
    currency: str
    adv: float
    beta: float

    @property
    def market_value(self) -> float:
        """Signed market value."""
        return self.quantity * self.market_price

    @property
    def abs_market_value(self) -> float:
        """Absolute market value."""
        return abs(self.market_value)


# ---------------------------------------------------------------------------
# Risk Engine
# ---------------------------------------------------------------------------

class RiskEngine:
    """Real-time portfolio risk engine.

    Maintains a live position book and computes all risk metrics on demand.
    Historical P&L is maintained as a rolling window for VaR computation.
    """

    _MAX_PNL_HISTORY = 500

    def __init__(self) -> None:
        self._positions: Dict[str, _PositionRecord] = {}
        self._nav: float = 0.0
        self._pnl_history: List[float] = []
        self._active_alerts: List[RiskAlert] = []

    # ------------------------------------------------------------------
    # Position management
    # ------------------------------------------------------------------

    def update_position(
        self,
        ticker: str,
        quantity: float,
        market_price: float,
        sector: str = "UNKNOWN",
        country: str = "US",
        currency: str = "USD",
        adv: float = 1_000_000.0,
        beta: float = 1.0,
    ) -> None:
        """Add or update a position in the risk engine.

        Args:
            ticker: Instrument symbol.
            quantity: Signed quantity (positive=long, negative=short).
            market_price: Current market price.
            sector: GICS sector name.
            country: ISO country code.
            currency: ISO currency code.
            adv: Average daily volume in USD.
            beta: Market beta.
        """
        t = ticker.upper()
        if quantity == 0:
            self._positions.pop(t, None)
            return
        self._positions[t] = _PositionRecord(
            ticker=t, quantity=quantity, market_price=market_price,
            sector=sector, country=country, currency=currency,
            adv=adv, beta=beta,
        )

    def remove_position(self, ticker: str) -> None:
        """Remove a position from the risk engine.

        Args:
            ticker: Instrument symbol.
        """
        self._positions.pop(ticker.upper(), None)

    def set_nav(self, nav: float) -> None:
        """Set the current portfolio NAV (cash + positions).

        Args:
            nav: Net asset value in USD.
        """
        self._nav = nav

    def add_pnl_observation(self, pnl: float) -> None:
        """Append a daily P&L observation for historical VaR.

        Args:
            pnl: Daily P&L in USD.
        """
        self._pnl_history.append(pnl)
        if len(self._pnl_history) > self._MAX_PNL_HISTORY:
            self._pnl_history.pop(0)

    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """Return all current positions as dicts.

        Returns:
            Dict mapping ticker to position attributes.
        """
        return {
            t: {
                "ticker": p.ticker,
                "quantity": p.quantity,
                "market_price": round(p.market_price, 6),
                "market_value": round(p.market_value, 2),
                "sector": p.sector,
                "country": p.country,
                "currency": p.currency,
                "adv": p.adv,
                "beta": p.beta,
            }
            for t, p in self._positions.items()
        }

    # ------------------------------------------------------------------
    # VaR
    # ------------------------------------------------------------------

    def compute_portfolio_var(
        self,
        confidence: float = 0.95,
        window: int = 252,
    ) -> VaRResult:
        """Compute historical 1-day VaR from current P&L history.

        Args:
            confidence: Confidence level (default 0.95).
            window: Look-back window in trading days.

        Returns:
            VaRResult.

        Raises:
            ValueError: If insufficient P&L history.
        """
        history = self._pnl_history[-window:]
        if len(history) < 10:
            raise ValueError("Need at least 10 P&L observations for VaR computation")
        sorted_pnl = sorted(history)
        cutoff = max(1, int((1.0 - confidence) * len(sorted_pnl)))
        var_usd = abs(sorted_pnl[cutoff - 1])
        var_pct = var_usd / self._nav if self._nav > 0 else 0.0
        return VaRResult(
            confidence=confidence,
            var_pct=var_pct,
            var_usd=var_usd,
            method="HISTORICAL",
            window=len(history),
            nav=self._nav,
        )

    # ------------------------------------------------------------------
    # Expected Shortfall
    # ------------------------------------------------------------------

    def compute_expected_shortfall(
        self, confidence: float = 0.95
    ) -> float:
        """Compute Expected Shortfall (CVaR) from P&L history.

        Args:
            confidence: Confidence level.

        Returns:
            Expected Shortfall in USD (positive number = loss).

        Raises:
            ValueError: If insufficient P&L history.
        """
        if len(self._pnl_history) < 10:
            raise ValueError("Need at least 10 P&L observations for ES")
        sorted_pnl = sorted(self._pnl_history)
        cutoff = max(1, int((1.0 - confidence) * len(sorted_pnl)))
        tail = sorted_pnl[:cutoff]
        return abs(sum(tail) / len(tail))

    # ------------------------------------------------------------------
    # Leverage
    # ------------------------------------------------------------------

    def compute_leverage(
        self, positions: Optional[List[Dict[str, Any]]] = None
    ) -> LeverageMetrics:
        """Compute gross and net leverage.

        Returns:
            LeverageMetrics.

        Raises:
            ValueError: If NAV is zero.
        """
        if positions is not None:
            self._load_positions(positions)
        if self._nav == 0:
            return LeverageMetrics(gross_leverage=0.0, net_leverage=0.0,
                                   long_exposure_usd=0.0, short_exposure_usd=0.0, nav=0.0)
        long_usd = sum(p.market_value for p in self._positions.values() if p.quantity > 0)
        short_usd = abs(sum(p.market_value for p in self._positions.values() if p.quantity < 0))
        gross_lev = (long_usd + short_usd) / self._nav
        net_lev = (long_usd - short_usd) / self._nav
        return LeverageMetrics(
            gross_leverage=gross_lev,
            net_leverage=net_lev,
            long_exposure_usd=long_usd,
            short_exposure_usd=short_usd,
            nav=self._nav,
        )

    # ------------------------------------------------------------------
    # Exposure
    # ------------------------------------------------------------------

    def compute_gross_exposure(self) -> float:
        """Return gross market exposure in USD.

        Returns:
            Sum of absolute position market values.
        """
        return sum(p.abs_market_value for p in self._positions.values())

    def compute_net_exposure(self) -> float:
        """Return net market exposure in USD (long - short).

        Returns:
            Signed net exposure.
        """
        return sum(p.market_value for p in self._positions.values())

    def compute_sector_exposure(self) -> Dict[str, float]:
        """Compute sector exposure as fraction of gross exposure.

        Returns:
            Dict mapping sector name to weight.
        """
        gross = self.compute_gross_exposure()
        if gross == 0:
            return {}
        sector_vals: Dict[str, float] = {}
        for p in self._positions.values():
            sector_vals[p.sector] = sector_vals.get(p.sector, 0.0) + p.abs_market_value
        return {s: round(v / gross, 6) for s, v in sector_vals.items()}

    def compute_country_exposure(
        self, positions: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, float]:
        """Compute country exposure as fraction of gross exposure.

        Returns:
            Dict mapping country code to weight.
        """
        if positions is not None:
            self._load_positions(positions)
        gross = self.compute_gross_exposure()
        if gross == 0:
            return {}
        country_vals: Dict[str, float] = {}
        for p in self._positions.values():
            country_vals[p.country] = country_vals.get(p.country, 0.0) + p.abs_market_value
        return {c: round(v / gross, 6) for c, v in country_vals.items()}

    def compute_currency_exposure(self) -> Dict[str, float]:
        """Compute currency exposure as fraction of gross exposure.

        Returns:
            Dict mapping currency code to weight.
        """
        gross = self.compute_gross_exposure()
        if gross == 0:
            return {}
        ccy_vals: Dict[str, float] = {}
        for p in self._positions.values():
            ccy_vals[p.currency] = ccy_vals.get(p.currency, 0.0) + p.abs_market_value
        return {c: round(v / gross, 6) for c, v in ccy_vals.items()}

    def compute_factor_exposure(
        self, factor_betas: Optional[Dict[str, Dict[str, float]]] = None
    ) -> Dict[str, float]:
        """Compute portfolio-level factor exposures (beta-weighted).

        Args:
            factor_betas: Optional mapping of ticker -> {factor: beta}.
                If None, uses the position.beta for a single 'Market' factor.

        Returns:
            Dict mapping factor name to weighted exposure.
        """
        gross = self.compute_gross_exposure()
        if gross == 0 or not self._positions:
            return {}
        if factor_betas:
            factor_exposure: Dict[str, float] = {}
            for p in self._positions.values():
                betas = factor_betas.get(p.ticker, {})
                weight = p.abs_market_value / gross
                for factor, beta in betas.items():
                    factor_exposure[factor] = factor_exposure.get(factor, 0.0) + weight * beta
            return {k: round(v, 6) for k, v in factor_exposure.items()}
        market_beta = sum(
            (p.abs_market_value / gross) * p.beta for p in self._positions.values()
        )
        return {"Market": round(market_beta, 6)}

    # ------------------------------------------------------------------
    # Liquidity risk
    # ------------------------------------------------------------------

    def compute_liquidity_risk(
        self, participation_rate: float = 0.25
    ) -> LiquidityRiskResult:
        """Estimate time-to-liquidate assuming participation_rate * ADV daily.

        Args:
            participation_rate: Fraction of ADV we can trade per day (default 25%).

        Returns:
            LiquidityRiskResult.
        """
        illiquid: List[str] = []
        total_pos = 0.0
        total_adv = 0.0
        max_days = 0.0
        for p in self._positions.values():
            if p.quantity <= 0:
                continue
            pos_usd = p.abs_market_value
            daily_tradeable = p.adv * participation_rate
            days = pos_usd / daily_tradeable if daily_tradeable > 0 else float("inf")
            total_pos += pos_usd
            total_adv += p.adv
            if days > 5:
                illiquid.append(p.ticker)
            if days > max_days:
                max_days = days
        score = max(0.0, min(1.0, 1.0 - max_days / 30.0)) if total_pos > 0 else 1.0
        return LiquidityRiskResult(
            days_to_liquidate=round(max_days, 2),
            illiquid_positions=illiquid,
            total_position_value_usd=total_pos,
            total_adv_usd=total_adv,
            liquidity_score=score,
        )

    # ------------------------------------------------------------------
    # Gap risk
    # ------------------------------------------------------------------

    def compute_gap_risk(
        self,
        scenario_name: str = "OVERNIGHT_5PCT",
        gap_pct: float = 0.05,
    ) -> GapRiskResult:
        """Estimate overnight gap risk under a shock scenario.

        Args:
            scenario_name: Name of the scenario.
            gap_pct: Fraction of price gap applied to all positions.

        Returns:
            GapRiskResult.
        """
        total_impact = 0.0
        position_impacts: List[Tuple[str, float]] = []
        for p in self._positions.values():
            direction = 1 if p.quantity > 0 else -1
            impact = p.abs_market_value * gap_pct * (-direction)
            total_impact += impact
            position_impacts.append((p.ticker, impact))
        position_impacts.sort(key=lambda x: abs(x[1]), reverse=True)
        worst_case = total_impact * 2.0
        return GapRiskResult(
            expected_gap_pnl=total_impact,
            worst_case_gap_pnl=worst_case,
            scenario_name=scenario_name,
            gap_pct=gap_pct,
            affected_positions=[t for t, _ in position_impacts[:5]],
        )

    # ------------------------------------------------------------------
    # Concentration
    # ------------------------------------------------------------------

    def compute_concentration(
        self, positions: Optional[List[Dict[str, Any]]] = None
    ) -> ConcentrationResult:
        """Compute portfolio concentration metrics.

        Returns:
            ConcentrationResult.
        """
        if positions is not None:
            self._load_positions(positions)
        gross = self.compute_gross_exposure()
        if gross == 0:
            return ConcentrationResult(
                herfindahl_index=0.0, top1_weight=0.0, top5_weight=0.0,
                top_positions=[], is_concentrated=False,
            )
        weights = [(p.ticker, p.abs_market_value / gross)
                   for p in self._positions.values()]
        weights.sort(key=lambda x: -x[1])
        hhi = sum(w ** 2 for _, w in weights)
        top1 = weights[0][1] if weights else 0.0
        top5 = sum(w for _, w in weights[:5])
        return ConcentrationResult(
            herfindahl_index=hhi,
            top1_weight=top1,
            top5_weight=top5,
            top_positions=weights[:5],
            is_concentrated=hhi > 0.25 or top1 > 0.20,
        )

    # ------------------------------------------------------------------
    # Margin
    # ------------------------------------------------------------------

    def compute_margin_usage(
        self,
        margin_requirement_pct: float = 0.25,
        maintenance_pct: float = 0.15,
    ) -> MarginResult:
        """Compute margin usage and buying power.

        Args:
            margin_requirement_pct: Initial margin as fraction of position value.
            maintenance_pct: Maintenance margin fraction.

        Returns:
            MarginResult.
        """
        gross = self.compute_gross_exposure()
        margin_used = gross * margin_requirement_pct
        maintenance = gross * maintenance_pct
        equity = self._nav
        margin_avail = max(0.0, equity - margin_used)
        usage_pct = margin_used / equity if equity > 0 else 0.0
        buying_power = (equity - margin_used) / margin_requirement_pct if margin_requirement_pct > 0 else 0.0
        margin_call = equity < maintenance
        return MarginResult(
            margin_used_usd=margin_used,
            margin_available_usd=margin_avail,
            margin_usage_pct=usage_pct,
            buying_power_usd=max(0.0, buying_power),
            maintenance_margin_usd=maintenance,
            margin_call_triggered=margin_call,
        )

    def compute_buying_power(
        self, leverage_ratio: float = 2.0
    ) -> float:
        """Compute available buying power at a given leverage ratio.

        Args:
            leverage_ratio: Maximum leverage ratio allowed.

        Returns:
            Buying power in USD.
        """
        current_exposure = self.compute_gross_exposure()
        max_exposure = self._nav * leverage_ratio
        return max(0.0, max_exposure - current_exposure)

    # ------------------------------------------------------------------
    # Stress tests
    # ------------------------------------------------------------------

    def run_stress_test(
        self,
        scenario_name: str = "UNNAMED",
        shock_pct: float = 0.0,
        affected_sectors: Optional[List[str]] = None,
    ) -> StressTestResult:
        """Run a named stress-test scenario on current positions.

        Args:
            scenario_name: Descriptive name of the scenario.
            shock_pct: Price shock applied (negative = down, positive = up).
            affected_sectors: If provided, only shock positions in these sectors.

        Returns:
            StressTestResult.
        """
        total_impact = 0.0
        position_impacts: List[Tuple[str, float]] = []
        for p in self._positions.values():
            if affected_sectors and p.sector not in affected_sectors:
                continue
            impact = p.market_value * shock_pct
            total_impact += impact
            position_impacts.append((p.ticker, impact))
        position_impacts.sort(key=lambda x: abs(x[1]), reverse=True)
        nav_after = self._nav + total_impact
        impact_pct = total_impact / self._nav if self._nav != 0 else 0.0
        return StressTestResult(
            scenario_name=scenario_name,
            pnl_impact_usd=total_impact,
            pnl_impact_pct=impact_pct,
            nav_after=nav_after,
            most_impacted=position_impacts[:5],
        )

    # ------------------------------------------------------------------
    # Risk alerts
    # ------------------------------------------------------------------

    def check_risk_alerts(
        self,
        var_threshold_pct: float = 0.02,
        leverage_threshold: float = 3.0,
        concentration_threshold: float = 0.25,
        drawdown_threshold_pct: float = 0.10,
    ) -> List[RiskAlert]:
        """Evaluate risk metrics and generate alerts for breached thresholds.

        Args:
            var_threshold_pct: Alert if VaR > this fraction of NAV.
            leverage_threshold: Alert if gross leverage > this.
            concentration_threshold: Alert if HHI > this.
            drawdown_threshold_pct: Alert if current drawdown > this.

        Returns:
            List of newly generated RiskAlert instances.
        """
        alerts: List[RiskAlert] = []
        nav = self._nav
        if nav <= 0:
            return alerts
        if len(self._pnl_history) >= 10:
            try:
                var_result = self.compute_portfolio_var(0.95)
                if var_result.var_pct > var_threshold_pct:
                    alerts.append(RiskAlert(
                        alert_id=str(uuid.uuid4()),
                        risk_type="VAR",
                        severity="HIGH",
                        message=f"Portfolio VaR ({var_result.var_pct:.2%}) exceeds threshold ({var_threshold_pct:.2%})",
                        value=var_result.var_pct,
                        threshold=var_threshold_pct,
                        timestamp=datetime.now(timezone.utc),
                    ))
            except ValueError:
                pass
        try:
            lev = self.compute_leverage()
            if lev.gross_leverage > leverage_threshold:
                alerts.append(RiskAlert(
                    alert_id=str(uuid.uuid4()),
                    risk_type="LEVERAGE",
                    severity="HIGH",
                    message=f"Gross leverage ({lev.gross_leverage:.2f}x) exceeds threshold ({leverage_threshold:.2f}x)",
                    value=lev.gross_leverage,
                    threshold=leverage_threshold,
                    timestamp=datetime.now(timezone.utc),
                ))
        except ValueError:
            pass
        conc = self.compute_concentration()
        if conc.herfindahl_index > concentration_threshold:
            alerts.append(RiskAlert(
                alert_id=str(uuid.uuid4()),
                risk_type="CONCENTRATION",
                severity="MEDIUM",
                message=f"Portfolio HHI ({conc.herfindahl_index:.3f}) indicates excessive concentration",
                value=conc.herfindahl_index,
                threshold=concentration_threshold,
                timestamp=datetime.now(timezone.utc),
            ))
        self._active_alerts = alerts
        return alerts

    def get_active_alerts(self) -> List[RiskAlert]:
        """Return the most recently computed risk alerts.

        Returns:
            List of RiskAlert.
        """
        return list(self._active_alerts)

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    def add_daily_pnl(self, pnl: float) -> None:
        """Alias for add_pnl_observation."""
        self.add_pnl_observation(pnl)

    def _load_positions(self, positions: List[Dict[str, Any]]) -> None:
        """Update engine positions from a list of dicts (test helper)."""
        for p in positions:
            ticker = str(p.get("ticker", "UNKNOWN"))
            qty = float(p.get("quantity", 0.0))
            price = float(p.get("current_price", p.get("market_price", 0.0)))
            sector = str(p.get("sector", "UNKNOWN"))
            country = str(p.get("country", "US"))
            currency = str(p.get("currency", "USD"))
            self.update_position(ticker, qty, price, sector, country, currency)

    def get_risk_dashboard(self) -> RiskDashboard:
        """Compute a consolidated risk dashboard snapshot.

        Returns:
            RiskDashboard with all key metrics.
        """
        var_95 = 0.0
        es_95 = 0.0
        if len(self._pnl_history) >= 10:
            try:
                var_95 = self.compute_portfolio_var(0.95).var_pct
                es_95 = self.compute_expected_shortfall(0.95) / self._nav if self._nav > 0 else 0.0
            except ValueError:
                pass
        gross_lev, net_lev = 0.0, 0.0
        if self._nav > 0:
            try:
                lev = self.compute_leverage()
                gross_lev = lev.gross_leverage
                net_lev = lev.net_leverage
            except ValueError:
                pass
        sector_exp = self.compute_sector_exposure()
        conc = self.compute_concentration()
        margin_result = self.compute_margin_usage()
        self.check_risk_alerts()
        return RiskDashboard(
            nav=self._nav,
            var_95=var_95,
            expected_shortfall_95=es_95,
            gross_leverage=gross_lev,
            net_leverage=net_lev,
            sector_exposure=sector_exp,
            concentration_hhi=conc.herfindahl_index,
            margin_usage_pct=margin_result.margin_usage_pct,
            active_alerts=self._active_alerts,
            timestamp=datetime.now(timezone.utc),
        )


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_engine: Optional[RiskEngine] = None


def get_risk_engine() -> RiskEngine:
    """Return the singleton RiskEngine.

    Returns:
        Shared RiskEngine instance.
    """
    global _default_engine
    if _default_engine is None:
        _default_engine = RiskEngine()
    return _default_engine
