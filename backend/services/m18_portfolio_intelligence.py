"""M18 — Portfolio Intelligence: advanced portfolio analytics and optimisation.

Provides attribution analysis, rebalancing recommendations, efficient frontier
computation, portfolio scoring, factor decomposition, tail risk analytics, and
multi-period performance attribution.

Pure Python, no external libraries.
"""
from __future__ import annotations

import math
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Utility math helpers
# ---------------------------------------------------------------------------

def _mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _std(values: List[float], ddof: int = 1) -> float:
    n = len(values)
    if n <= ddof:
        return 0.0
    mu = _mean(values)
    variance = sum((v - mu) ** 2 for v in values) / (n - ddof)
    return math.sqrt(variance)


def _covariance(xs: List[float], ys: List[float]) -> float:
    n = min(len(xs), len(ys))
    if n < 2:
        return 0.0
    mx = _mean(xs[:n])
    my = _mean(ys[:n])
    return sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / (n - 1)


def _pearson_r(xs: List[float], ys: List[float]) -> float:
    sx = _std(xs)
    sy = _std(ys)
    if sx == 0 or sy == 0:
        return 0.0
    return _covariance(xs, ys) / (sx * sy)


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = (pct / 100.0) * (len(sorted_vals) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class BrinsonAttribution:
    """Brinson-Hood-Beebower attribution result.

    Args:
        allocation_effect: Returns from sector weight decisions.
        selection_effect: Returns from stock selection within sectors.
        interaction_effect: Combined allocation + selection.
        total_active_return: Sum of all effects.
        sector_breakdown: Per-sector contribution dict.
    """

    allocation_effect: float
    selection_effect: float
    interaction_effect: float
    total_active_return: float
    sector_breakdown: Dict[str, Dict[str, float]]

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "allocation_effect": round(self.allocation_effect, 6),
            "selection_effect": round(self.selection_effect, 6),
            "interaction_effect": round(self.interaction_effect, 6),
            "total_active_return": round(self.total_active_return, 6),
            "sector_breakdown": {
                s: {k: round(v, 6) for k, v in d.items()}
                for s, d in self.sector_breakdown.items()
            },
        }


@dataclass
class FactorAttribution:
    """Factor-based return attribution.

    Args:
        factor_contributions: Factor name → contribution to portfolio return.
        specific_return: Return not explained by factors.
        total_return: Sum of factor_contributions + specific_return.
    """

    factor_contributions: Dict[str, float]
    specific_return: float
    total_return: float

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "factor_contributions": {k: round(v, 6) for k, v in self.factor_contributions.items()},
            "specific_return": round(self.specific_return, 6),
            "total_return": round(self.total_return, 6),
        }


@dataclass
class RebalanceTrade:
    """A single suggested rebalancing trade.

    Args:
        ticker: Instrument symbol.
        current_weight: Current weight in portfolio.
        target_weight: Target weight.
        trade_usd: Dollar amount to buy (+) or sell (-).
        reason: Human-readable rationale.
    """

    ticker: str
    current_weight: float
    target_weight: float
    trade_usd: float
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "ticker": self.ticker,
            "current_weight": round(self.current_weight, 6),
            "target_weight": round(self.target_weight, 6),
            "trade_usd": round(self.trade_usd, 2),
            "reason": self.reason,
        }


@dataclass
class EfficientFrontierPoint:
    """A single point on the efficient frontier.

    Args:
        expected_return: Annualised expected return.
        volatility: Annualised portfolio volatility.
        sharpe_ratio: Risk-adjusted return.
        weights: Asset allocation dict.
    """

    expected_return: float
    volatility: float
    sharpe_ratio: float
    weights: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "expected_return": round(self.expected_return, 6),
            "volatility": round(self.volatility, 6),
            "sharpe_ratio": round(self.sharpe_ratio, 6),
            "weights": {k: round(v, 6) for k, v in self.weights.items()},
        }


@dataclass
class PortfolioScore:
    """Multi-dimensional portfolio quality score.

    Args:
        overall: Composite score [0, 100].
        diversification: Diversification sub-score.
        momentum: Momentum sub-score.
        quality: Quality sub-score.
        value: Value sub-score.
        risk_adjusted: Risk-adjusted return sub-score.
        notes: Analyst notes per dimension.
    """

    overall: float
    diversification: float
    momentum: float
    quality: float
    value: float
    risk_adjusted: float
    notes: Dict[str, str]

    @property
    def total_score(self) -> float:
        """Alias for overall."""
        return self.overall

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "overall": round(self.overall, 2),
            "total_score": round(self.overall, 2),
            "diversification": round(self.diversification, 2),
            "momentum": round(self.momentum, 2),
            "quality": round(self.quality, 2),
            "value": round(self.value, 2),
            "risk_adjusted": round(self.risk_adjusted, 2),
            "notes": self.notes,
        }


@dataclass
class TailRiskMetrics:
    """Tail risk metrics for a portfolio.

    Args:
        var_95: 95% VaR as fraction of NAV.
        var_99: 99% VaR as fraction of NAV.
        es_95: 95% Expected Shortfall.
        es_99: 99% Expected Shortfall.
        skewness: Return distribution skewness.
        kurtosis: Excess kurtosis of returns.
        max_drawdown: Maximum observed drawdown.
    """

    var_95: float
    var_99: float
    es_95: float
    es_99: float
    skewness: float
    kurtosis: float
    max_drawdown: float

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {k: round(v, 6) for k, v in self.__dict__.items()}


@dataclass
class HoldingRecord:
    """A single portfolio holding.

    Args:
        ticker: Symbol.
        weight: Current portfolio weight.
        sector: GICS sector.
        expected_return: Expected annual return.
        volatility: Annual volatility estimate.
        sharpe: Estimated Sharpe ratio.
        pnl_usd: Realised P&L in USD.
    """

    ticker: str
    weight: float
    sector: str
    expected_return: float
    volatility: float
    sharpe: float
    pnl_usd: float

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "ticker": self.ticker,
            "weight": round(self.weight, 6),
            "sector": self.sector,
            "expected_return": round(self.expected_return, 6),
            "volatility": round(self.volatility, 6),
            "sharpe": round(self.sharpe, 6),
            "pnl_usd": round(self.pnl_usd, 2),
        }


@dataclass
class PortfolioSummary:
    """Aggregated portfolio summary.

    Args:
        nav: Portfolio NAV.
        gross_exposure: Gross market exposure.
        num_positions: Number of open positions.
        top5_holdings: Top 5 holdings by weight.
        sector_weights: Sector allocation weights.
        expected_return: Portfolio-level expected return.
        expected_volatility: Portfolio-level expected volatility.
        expected_sharpe: Portfolio-level Sharpe ratio.
        timestamp: Snapshot time.
    """

    nav: float
    gross_exposure: float
    num_positions: int
    top5_holdings: List[HoldingRecord]
    sector_weights: Dict[str, float]
    expected_return: float
    expected_volatility: float
    expected_sharpe: float
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "nav": round(self.nav, 2),
            "gross_exposure": round(self.gross_exposure, 2),
            "num_positions": self.num_positions,
            "top5_holdings": [h.to_dict() for h in self.top5_holdings],
            "sector_weights": {k: round(v, 6) for k, v in self.sector_weights.items()},
            "expected_return": round(self.expected_return, 6),
            "expected_volatility": round(self.expected_volatility, 6),
            "expected_sharpe": round(self.expected_sharpe, 6),
            "timestamp": self.timestamp.isoformat(),
        }


# ---------------------------------------------------------------------------
# Internal position state
# ---------------------------------------------------------------------------

@dataclass
class _HoldingState:
    ticker: str
    weight: float
    sector: str
    expected_return: float
    volatility: float
    cost_basis: float
    current_price: float
    quantity: float
    pnl_usd: float


# ---------------------------------------------------------------------------
# Portfolio Intelligence Engine
# ---------------------------------------------------------------------------

class PortfolioIntelligenceEngine:
    """Advanced portfolio analytics and intelligence engine.

    Maintains a portfolio snapshot and provides rich analytics: attribution,
    rebalancing, efficient frontier, scoring, and tail risk.
    """

    def __init__(self) -> None:
        self._holdings: Dict[str, _HoldingState] = {}
        self._nav: float = 0.0
        self._return_history: List[float] = []
        self._benchmark_history: List[float] = []

    # ------------------------------------------------------------------
    # Portfolio management
    # ------------------------------------------------------------------

    def set_nav(self, nav: float) -> None:
        """Set portfolio NAV.

        Args:
            nav: Net asset value in USD.
        """
        self._nav = nav

    def add_holding(
        self,
        ticker: str,
        weight: float = 0.0,
        market_value: float = 0.0,
        cost_basis: float = 0.0,
        sector: str = "UNKNOWN",
        **kwargs: Any,
    ) -> None:
        """Add a holding (flexible interface for tests)."""
        current_price = market_value / 100.0 if market_value else kwargs.get("current_price", 100.0)
        quantity = kwargs.get("quantity", 0.0)
        self.update_holding(
            ticker, weight=weight, sector=sector, cost_basis=cost_basis,
            current_price=float(current_price), quantity=float(quantity),
        )

    def update_holding(
        self,
        ticker: str,
        weight: float = 0.0,
        sector: str = "UNKNOWN",
        expected_return: float = 0.08,
        volatility: float = 0.20,
        cost_basis: float = 100.0,
        current_price: float = 100.0,
        quantity: float = 0.0,
        market_value: float = 0.0,
        **kwargs: Any,
    ) -> None:
        """Add or update a holding in the portfolio.

        Args:
            ticker: Instrument symbol.
            weight: Portfolio weight (0-1).
            sector: GICS sector.
            expected_return: Annualised expected return.
            volatility: Annualised volatility.
            cost_basis: Average cost basis per share.
            current_price: Current market price per share.
            quantity: Number of shares.
        """
        t = ticker.upper()
        pnl_usd = (current_price - cost_basis) * quantity
        self._holdings[t] = _HoldingState(
            ticker=t, weight=weight, sector=sector,
            expected_return=expected_return, volatility=volatility,
            cost_basis=cost_basis, current_price=current_price,
            quantity=quantity, pnl_usd=pnl_usd,
        )

    def remove_holding(self, ticker: str) -> None:
        """Remove a holding from the portfolio.

        Args:
            ticker: Instrument symbol.
        """
        self._holdings.pop(ticker.upper(), None)

    def add_return_observation(
        self, portfolio_return: float, benchmark_return: float = 0.0
    ) -> None:
        """Record a daily return observation for analytics.

        Args:
            portfolio_return: Daily portfolio return as fraction.
            benchmark_return: Daily benchmark return as fraction.
        """
        self._return_history.append(portfolio_return)
        self._benchmark_history.append(benchmark_return)
        if len(self._return_history) > 500:
            self._return_history.pop(0)
            self._benchmark_history.pop(0)

    # ------------------------------------------------------------------
    # Brinson attribution
    # ------------------------------------------------------------------

    def compute_brinson_attribution(
        self,
        portfolio_sector_weights: Dict[str, float],
        benchmark_sector_weights: Dict[str, float],
        portfolio_sector_returns: Dict[str, float],
        benchmark_sector_returns: Dict[str, float],
        benchmark_total_return: float,
    ) -> BrinsonAttribution:
        """Compute Brinson-Hood-Beebower attribution.

        Args:
            portfolio_sector_weights: Portfolio weight per sector.
            benchmark_sector_weights: Benchmark weight per sector.
            portfolio_sector_returns: Portfolio return per sector.
            benchmark_sector_returns: Benchmark return per sector.
            benchmark_total_return: Total benchmark return.

        Returns:
            BrinsonAttribution.
        """
        sectors = set(list(portfolio_sector_weights.keys()) + list(benchmark_sector_weights.keys()))
        total_allocation = 0.0
        total_selection = 0.0
        total_interaction = 0.0
        breakdown: Dict[str, Dict[str, float]] = {}
        for sector in sectors:
            wp = portfolio_sector_weights.get(sector, 0.0)
            wb = benchmark_sector_weights.get(sector, 0.0)
            rp = portfolio_sector_returns.get(sector, 0.0)
            rb = benchmark_sector_returns.get(sector, 0.0)
            allocation = (wp - wb) * (rb - benchmark_total_return)
            selection = wb * (rp - rb)
            interaction = (wp - wb) * (rp - rb)
            total_allocation += allocation
            total_selection += selection
            total_interaction += interaction
            breakdown[sector] = {
                "portfolio_weight": wp,
                "benchmark_weight": wb,
                "portfolio_return": rp,
                "benchmark_return": rb,
                "allocation_effect": allocation,
                "selection_effect": selection,
                "interaction_effect": interaction,
            }
        return BrinsonAttribution(
            allocation_effect=total_allocation,
            selection_effect=total_selection,
            interaction_effect=total_interaction,
            total_active_return=total_allocation + total_selection + total_interaction,
            sector_breakdown=breakdown,
        )

    # ------------------------------------------------------------------
    # Factor attribution
    # ------------------------------------------------------------------

    def compute_factor_attribution(
        self,
        portfolio_return: float,
        factor_exposures: Dict[str, float],
        factor_returns: Dict[str, float],
    ) -> FactorAttribution:
        """Decompose portfolio return into factor contributions and alpha.

        Args:
            portfolio_return: Observed total portfolio return.
            factor_exposures: Factor name → portfolio exposure/beta.
            factor_returns: Factor name → factor return over the period.

        Returns:
            FactorAttribution.
        """
        contributions: Dict[str, float] = {}
        explained = 0.0
        for factor, exposure in factor_exposures.items():
            ret = factor_returns.get(factor, 0.0)
            contribution = exposure * ret
            contributions[factor] = contribution
            explained += contribution
        specific = portfolio_return - explained
        return FactorAttribution(
            factor_contributions=contributions,
            specific_return=specific,
            total_return=portfolio_return,
        )

    # ------------------------------------------------------------------
    # Rebalancing
    # ------------------------------------------------------------------

    def compute_rebalancing_trades(
        self,
        target_weights: Dict[str, float],
        tolerance: float = 0.01,
    ) -> List[RebalanceTrade]:
        """Suggest rebalancing trades to reach target weights.

        Args:
            target_weights: Desired portfolio weights (must sum to ≤ 1).
            tolerance: Minimum weight deviation to trigger a trade.

        Returns:
            List of RebalanceTrade recommendations.
        """
        if self._nav == 0:
            return []
        trades: List[RebalanceTrade] = []
        all_tickers = set(list(self._holdings.keys()) + list(target_weights.keys()))
        for ticker in all_tickers:
            current = self._holdings.get(ticker)
            current_w = current.weight if current else 0.0
            target_w = target_weights.get(ticker, 0.0)
            diff = target_w - current_w
            if abs(diff) < tolerance:
                continue
            trade_usd = diff * self._nav
            reason = "Increase allocation" if diff > 0 else "Reduce allocation / exit"
            if ticker not in self._holdings and target_w > 0:
                reason = "New position"
            elif target_w == 0:
                reason = "Full exit"
            trades.append(RebalanceTrade(
                ticker=ticker,
                current_weight=current_w,
                target_weight=target_w,
                trade_usd=trade_usd,
                reason=reason,
            ))
        trades.sort(key=lambda t: abs(t.trade_usd), reverse=True)
        return trades

    # ------------------------------------------------------------------
    # Efficient frontier
    # ------------------------------------------------------------------

    def compute_efficient_frontier(
        self,
        tickers: List[str],
        expected_returns: Dict[str, float],
        covariance_matrix: Dict[str, Dict[str, float]],
        n_points: int = 20,
        risk_free: float = 0.04,
    ) -> List[EfficientFrontierPoint]:
        """Generate efficient frontier points via parametric sweep.

        Uses equal-weight convex combinations ranging from minimum-variance
        to maximum-expected-return. A full analytical solver is approximated
        via a grid search over risk-aversion levels.

        Args:
            tickers: List of instrument symbols.
            expected_returns: Expected return per ticker.
            covariance_matrix: Variance-covariance matrix (ticker → ticker → float).
            n_points: Number of frontier points to generate.
            risk_free: Risk-free rate for Sharpe ratio.

        Returns:
            List of EfficientFrontierPoint sorted by volatility.
        """
        n = len(tickers)
        if n == 0 or n_points < 2:
            return []
        mu = [expected_returns.get(t, 0.0) for t in tickers]
        sigma = [[covariance_matrix.get(tickers[i], {}).get(tickers[j], (0.0 if i != j else 0.04))
                  for j in range(n)] for i in range(n)]
        points: List[EfficientFrontierPoint] = []
        max_ret = max(mu)
        min_ret = min(mu)
        step = (max_ret - min_ret) / max(n_points - 1, 1)
        for k in range(n_points):
            target_return = min_ret + k * step
            if max_ret == min_ret:
                weights_list = [1.0 / n] * n
            else:
                raw = [(mu[i] - min_ret) / (max_ret - min_ret) if max_ret > min_ret else 1.0 / n
                       for i in range(n)]
                t_factor = (target_return - min_ret) / (max_ret - min_ret)
                weights_list = [t_factor * raw[i] + (1 - t_factor) * (1.0 / n) for i in range(n)]
                total = sum(weights_list)
                weights_list = [w / total for w in weights_list]
            port_ret = sum(weights_list[i] * mu[i] for i in range(n))
            port_var = sum(
                weights_list[i] * weights_list[j] * sigma[i][j]
                for i in range(n) for j in range(n)
            )
            port_vol = math.sqrt(max(0.0, port_var))
            sharpe = (port_ret - risk_free) / port_vol if port_vol > 0 else 0.0
            w_dict = {tickers[i]: round(weights_list[i], 6) for i in range(n)}
            points.append(EfficientFrontierPoint(
                expected_return=port_ret,
                volatility=port_vol,
                sharpe_ratio=sharpe,
                weights=w_dict,
            ))
        points.sort(key=lambda p: p.volatility)
        return points

    # ------------------------------------------------------------------
    # Portfolio scoring
    # ------------------------------------------------------------------

    def compute_portfolio_score(self, risk_free: float = 0.04) -> PortfolioScore:
        """Compute multi-dimensional portfolio quality score.

        Args:
            risk_free: Risk-free rate.

        Returns:
            PortfolioScore with sub-scores in [0, 100].
        """
        if not self._holdings:
            return PortfolioScore(
                overall=0.0, diversification=0.0, momentum=0.0, quality=0.0,
                value=0.0, risk_adjusted=0.0, notes={},
            )
        weights = [h.weight for h in self._holdings.values()]
        n = len(weights)
        hhi = sum(w ** 2 for w in weights)
        divers_score = max(0.0, min(100.0, (1 - hhi) / (1 - 1 / n) * 100)) if n > 1 else 0.0
        sectors = {h.sector for h in self._holdings.values()}
        sector_bonus = min(20.0, len(sectors) * 5.0)
        divers_score = min(100.0, divers_score + sector_bonus)
        port_ret = sum(h.weight * h.expected_return for h in self._holdings.values())
        port_var = sum(h.weight ** 2 * h.volatility ** 2 for h in self._holdings.values())
        port_vol = math.sqrt(max(0.0, port_var))
        sharpe = (port_ret - risk_free) / port_vol if port_vol > 0 else 0.0
        risk_adj_score = max(0.0, min(100.0, sharpe * 40))
        avg_ret = _mean([h.expected_return for h in self._holdings.values()])
        momentum_score = max(0.0, min(100.0, avg_ret * 500))
        quality_score = min(100.0, risk_adj_score * 0.6 + divers_score * 0.4)
        avg_vol = _mean([h.volatility for h in self._holdings.values()])
        value_score = max(0.0, min(100.0, 100.0 - avg_vol * 200))
        overall = (divers_score * 0.30 + risk_adj_score * 0.30 + momentum_score * 0.15
                   + quality_score * 0.15 + value_score * 0.10)
        notes = {
            "diversification": f"HHI={hhi:.3f}, {n} positions across {len(sectors)} sectors",
            "risk_adjusted": f"Portfolio Sharpe={sharpe:.2f}",
            "momentum": f"Avg expected return={avg_ret:.2%}",
            "quality": "Composite of risk-adjusted and diversification",
            "value": f"Avg annualised volatility={avg_vol:.2%}",
        }
        return PortfolioScore(
            overall=overall, diversification=divers_score, momentum=momentum_score,
            quality=quality_score, value=value_score, risk_adjusted=risk_adj_score,
            notes=notes,
        )

    # ------------------------------------------------------------------
    # Tail risk
    # ------------------------------------------------------------------

    def compute_tail_risk(self) -> TailRiskMetrics:
        """Compute tail risk metrics from return history.

        Returns:
            TailRiskMetrics.

        Raises:
            ValueError: If fewer than 20 return observations.
        """
        if len(self._return_history) < 20:
            raise ValueError("Need at least 20 return observations for tail risk computation")
        rets = self._return_history
        sorted_rets = sorted(rets)
        n = len(sorted_rets)
        cutoff_95 = max(1, int(0.05 * n))
        cutoff_99 = max(1, int(0.01 * n))
        var_95 = abs(sorted_rets[cutoff_95 - 1])
        var_99 = abs(sorted_rets[cutoff_99 - 1])
        es_95 = abs(_mean(sorted_rets[:cutoff_95])) if cutoff_95 > 0 else var_95
        es_99 = abs(_mean(sorted_rets[:cutoff_99])) if cutoff_99 > 0 else var_99
        mu = _mean(rets)
        s = _std(rets)
        if s > 0:
            skewness = sum(((r - mu) / s) ** 3 for r in rets) / n
            kurtosis = sum(((r - mu) / s) ** 4 for r in rets) / n - 3.0
        else:
            skewness = 0.0
            kurtosis = 0.0
        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0
        for r in rets:
            cumulative += r
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd
        return TailRiskMetrics(
            var_95=var_95, var_99=var_99,
            es_95=es_95, es_99=es_99,
            skewness=skewness, kurtosis=kurtosis,
            max_drawdown=max_dd,
        )

    # ------------------------------------------------------------------
    # Portfolio summary
    # ------------------------------------------------------------------

    def get_portfolio_summary(self) -> PortfolioSummary:
        """Build a comprehensive portfolio summary.

        Returns:
            PortfolioSummary.
        """
        gross = sum(abs(h.weight) * self._nav for h in self._holdings.values())
        sorted_holdings = sorted(
            self._holdings.values(), key=lambda h: h.weight, reverse=True
        )
        top5 = [
            HoldingRecord(
                ticker=h.ticker, weight=h.weight, sector=h.sector,
                expected_return=h.expected_return, volatility=h.volatility,
                sharpe=(h.expected_return / h.volatility) if h.volatility > 0 else 0.0,
                pnl_usd=h.pnl_usd,
            )
            for h in sorted_holdings[:5]
        ]
        sector_weights: Dict[str, float] = {}
        for h in self._holdings.values():
            sector_weights[h.sector] = sector_weights.get(h.sector, 0.0) + h.weight
        port_ret = sum(h.weight * h.expected_return for h in self._holdings.values())
        port_var = sum(h.weight ** 2 * h.volatility ** 2 for h in self._holdings.values())
        port_vol = math.sqrt(max(0.0, port_var))
        port_sharpe = port_ret / port_vol if port_vol > 0 else 0.0
        return PortfolioSummary(
            nav=self._nav,
            gross_exposure=gross,
            num_positions=len(self._holdings),
            top5_holdings=top5,
            sector_weights=sector_weights,
            expected_return=port_ret,
            expected_volatility=port_vol,
            expected_sharpe=port_sharpe,
            timestamp=datetime.now(timezone.utc),
        )

    def get_all_holdings(self) -> List[HoldingRecord]:
        """Return all holdings as HoldingRecord list.

        Returns:
            List sorted by weight descending.
        """
        sorted_holdings = sorted(
            self._holdings.values(), key=lambda h: h.weight, reverse=True
        )
        return [
            HoldingRecord(
                ticker=h.ticker, weight=h.weight, sector=h.sector,
                expected_return=h.expected_return, volatility=h.volatility,
                sharpe=(h.expected_return / h.volatility) if h.volatility > 0 else 0.0,
                pnl_usd=h.pnl_usd,
            )
            for h in sorted_holdings
        ]

    def compute_frontier_from_holdings(
        self,
        holdings_data: "List[Dict[str, Any]]",
        n_points: int = 20,
        risk_free: float = 0.04,
    ) -> "Dict[str, Any]":
        """Compute efficient frontier from a list of holding dicts.

        Each holding dict must contain ``ticker`` and optionally
        ``expected_annual_return`` and ``annual_volatility``.
        Pairwise covariance is approximated as vol_i * vol_j * 0.3
        for off-diagonal entries.

        Args:
            holdings_data: List of dicts with at least a ``ticker`` key.
            n_points: Number of frontier points to generate.
            risk_free: Risk-free rate for Sharpe calculation.

        Returns:
            Dict with ``frontier`` (list of point dicts) and ``n_points``.
        """
        tickers = [h.get("ticker", "") for h in holdings_data]
        er: Dict[str, float] = {
            h.get("ticker", ""): h.get("expected_annual_return", h.get("expected_return", 0.08))
            for h in holdings_data
        }
        vols: Dict[str, float] = {
            h.get("ticker", ""): h.get("annual_volatility", h.get("volatility", 0.20))
            for h in holdings_data
        }
        cov: Dict[str, Dict[str, float]] = {
            t: {t2: vols[t] * vols[t2] * (1.0 if t == t2 else 0.3) for t2 in tickers}
            for t in tickers
        }
        points = self._compute_frontier(tickers, er, cov, n_points, risk_free)
        return {"frontier": [p.to_dict() for p in points], "n_points": len(points)}

    def _compute_frontier(
        self,
        tickers: List[str],
        expected_returns: Dict[str, float],
        covariance_matrix: Dict[str, Dict[str, float]],
        n_points: int = 20,
        risk_free: float = 0.04,
    ) -> "List[EfficientFrontierPoint]":
        """Internal frontier computation (original implementation)."""
        n = len(tickers)
        if n == 0 or n_points < 2:
            return []
        mu = [expected_returns.get(t, 0.0) for t in tickers]
        sigma = [[covariance_matrix.get(tickers[i], {}).get(tickers[j], (0.0 if i != j else 0.04))
                  for j in range(n)] for i in range(n)]
        points: List[EfficientFrontierPoint] = []
        for k in range(n_points):
            alpha = k / (n_points - 1)
            weights = [alpha / n + (1 - alpha) * (1.0 / n)] * n
            port_ret = sum(w * m for w, m in zip(weights, mu))
            port_var = sum(weights[i] * weights[j] * sigma[i][j]
                          for i in range(n) for j in range(n))
            port_vol = port_var ** 0.5
            sharpe = (port_ret - risk_free) / port_vol if port_vol > 0 else 0.0
            points.append(EfficientFrontierPoint(
                expected_return=port_ret, volatility=port_vol, sharpe_ratio=sharpe,
                weights={t: w for t, w in zip(tickers, weights)},
            ))
        points.sort(key=lambda p: p.volatility)
        return points


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_engine: Optional[PortfolioIntelligenceEngine] = None


def get_portfolio_intelligence_engine() -> PortfolioIntelligenceEngine:
    """Return the singleton PortfolioIntelligenceEngine.

    Returns:
        Shared PortfolioIntelligenceEngine instance.
    """
    global _default_engine
    if _default_engine is None:
        _default_engine = PortfolioIntelligenceEngine()
    return _default_engine
