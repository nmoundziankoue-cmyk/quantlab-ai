"""M15 Phase 4 — Event Impact Engine.

Computes pre/post event return metrics, volume spikes, volatility spikes,
abnormal returns, drawdowns, and momentum persistence.
Pure Python, in-memory, fully deterministic.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Statistical helpers
# ---------------------------------------------------------------------------

def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    var = sum((v - m) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(var)


def _cumulative_return(returns: List[float]) -> float:
    result = 1.0
    for r in returns:
        result *= (1.0 + r)
    return result - 1.0


def _max_drawdown(returns: List[float]) -> float:
    """Maximum drawdown from a returns series."""
    if not returns:
        return 0.0
    peak = 1.0
    trough = 1.0
    max_dd = 0.0
    level = 1.0
    for r in returns:
        level *= (1.0 + r)
        if level > peak:
            peak = level
            trough = level
        else:
            if level < trough:
                trough = level
        dd = (trough - peak) / peak if peak > 0 else 0.0
        if dd < max_dd:
            max_dd = dd
    return round(max_dd, 8)


def _recovery_time(returns: List[float], event_idx: int) -> Optional[int]:
    """Days after event to recover to pre-event level."""
    if not returns or event_idx >= len(returns):
        return None
    pre_level = 1.0
    for r in returns[:event_idx]:
        pre_level *= (1.0 + r)
    level = pre_level
    for i, r in enumerate(returns[event_idx:]):
        level *= (1.0 + r)
        if level >= pre_level:
            return i
    return None


def _momentum_persistence(post_returns: List[float], window: int = 5) -> float:
    """Fraction of post-event days where the return sign matches event direction."""
    if not post_returns:
        return 0.0
    event_sign = 1 if _mean(post_returns[:3]) >= 0 else -1
    check = post_returns[:window]
    matching = sum(1 for r in check if (r >= 0) == (event_sign > 0))
    return round(matching / len(check), 4) if check else 0.0


# ---------------------------------------------------------------------------
# EventImpact dataclass
# ---------------------------------------------------------------------------

@dataclass
class EventImpact:
    """Full impact profile of an event on a security."""

    event_id: str
    ticker: str
    pre_return: float
    post_return: float
    gap_pct: float
    volume_spike: float
    volatility_spike: float
    relative_return: float
    abnormal_return: float
    liquidity_change: float
    max_drawdown: float
    recovery_days: Optional[int]
    momentum_persistence: float
    risk_contribution: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "ticker": self.ticker,
            "pre_return": self.pre_return,
            "post_return": self.post_return,
            "gap_pct": self.gap_pct,
            "volume_spike": self.volume_spike,
            "volatility_spike": self.volatility_spike,
            "relative_return": self.relative_return,
            "abnormal_return": self.abnormal_return,
            "liquidity_change": self.liquidity_change,
            "max_drawdown": self.max_drawdown,
            "recovery_days": self.recovery_days,
            "momentum_persistence": self.momentum_persistence,
            "risk_contribution": self.risk_contribution,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# EventImpactEngine
# ---------------------------------------------------------------------------

class EventImpactEngine:
    """Compute impact metrics for corporate or macro events."""

    def compute(
        self,
        event_id: str,
        ticker: str,
        pre_returns: List[float],
        post_returns: List[float],
        market_returns: Optional[List[float]] = None,
        pre_volumes: Optional[List[float]] = None,
        post_volumes: Optional[List[float]] = None,
        gap_return: float = 0.0,
        expected_daily_return: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EventImpact:
        """Compute full event impact profile.

        Args:
            event_id: Identifier of the event.
            ticker: Security identifier.
            pre_returns: Daily returns in the pre-event window.
            post_returns: Daily returns in the post-event window.
            market_returns: Benchmark returns (same combined length) for
                relative/abnormal return computation.
            pre_volumes: Pre-event daily volumes for volume spike.
            post_volumes: Post-event daily volumes.
            gap_return: Return at the open on the event day (gap).
            expected_daily_return: Expected return per day (market model).
            metadata: Optional extra data.

        Returns:
            EventImpact with all computed metrics.
        """
        pre_ret = round(_cumulative_return(pre_returns), 8)
        post_ret = round(_cumulative_return(post_returns), 8)
        gap = round(gap_return, 8)

        # Volume spike: post vs pre average
        avg_pre_vol = _mean(pre_volumes) if pre_volumes else 1.0
        avg_post_vol = _mean(post_volumes) if post_volumes else avg_pre_vol
        vol_spike = round(avg_post_vol / avg_pre_vol, 4) if avg_pre_vol > 0 else 1.0

        # Volatility spike: std(post) vs std(pre)
        pre_vol_val = _std(pre_returns) if pre_returns else 0.0
        post_vol_val = _std(post_returns) if post_returns else 0.0
        vol_spike_ratio = round(post_vol_val / pre_vol_val, 4) if pre_vol_val > 0 else 1.0

        # Relative return: post vs market
        if market_returns:
            market_post = market_returns[len(pre_returns):]
            mkt_ret = _cumulative_return(market_post)
        else:
            mkt_ret = 0.0
        rel_ret = round(post_ret - mkt_ret, 8)

        # Abnormal return: post vs expected
        n_post = len(post_returns)
        expected_total = expected_daily_return * n_post
        abnormal = round(post_ret - expected_total, 8)

        # Liquidity change: change in bid-ask spread proxy (volume-based)
        liquidity_change = round(1.0 / vol_spike - 1.0, 4) if vol_spike > 0 else 0.0

        # Drawdown on post window
        all_returns = pre_returns + post_returns
        max_dd = _max_drawdown(all_returns)
        recovery = _recovery_time(all_returns, len(pre_returns))
        momentum = _momentum_persistence(post_returns)

        # Risk contribution: beta * vol proxy
        combined_std = _std(pre_returns + post_returns)
        market_std = _std(market_returns) if market_returns else 1.0
        beta = combined_std / market_std if market_std > 0 else 1.0
        risk_contribution = round(beta * combined_std, 8)

        return EventImpact(
            event_id=event_id,
            ticker=ticker,
            pre_return=pre_ret,
            post_return=post_ret,
            gap_pct=gap,
            volume_spike=vol_spike,
            volatility_spike=vol_spike_ratio,
            relative_return=rel_ret,
            abnormal_return=abnormal,
            liquidity_change=liquidity_change,
            max_drawdown=max_dd,
            recovery_days=recovery,
            momentum_persistence=momentum,
            risk_contribution=risk_contribution,
            metadata=metadata or {},
        )

    def batch_compute(
        self,
        event_id: str,
        inputs: List[Dict[str, Any]],
    ) -> List[EventImpact]:
        """Compute impact for multiple securities.

        Each dict in inputs should have keys: ticker, pre_returns, post_returns,
        optionally: market_returns, pre_volumes, post_volumes, gap_return,
        expected_daily_return.
        """
        results = []
        for inp in inputs:
            impact = self.compute(
                event_id=event_id,
                ticker=inp["ticker"],
                pre_returns=inp.get("pre_returns", []),
                post_returns=inp.get("post_returns", []),
                market_returns=inp.get("market_returns"),
                pre_volumes=inp.get("pre_volumes"),
                post_volumes=inp.get("post_volumes"),
                gap_return=inp.get("gap_return", 0.0),
                expected_daily_return=inp.get("expected_daily_return", 0.0),
                metadata=inp.get("metadata"),
            )
            results.append(impact)
        return results

    def summary_stats(self, impacts: List[EventImpact]) -> Dict[str, Any]:
        """Cross-sectional summary statistics across a list of EventImpacts."""
        if not impacts:
            return {}
        fields = [
            "pre_return", "post_return", "gap_pct", "volume_spike",
            "volatility_spike", "abnormal_return", "max_drawdown",
        ]
        stats: Dict[str, Any] = {"count": len(impacts)}
        for f in fields:
            vals = [getattr(imp, f) for imp in impacts]
            stats[f"{f}_mean"] = round(_mean(vals), 6)
            stats[f"{f}_min"] = round(min(vals), 6)
            stats[f"{f}_max"] = round(max(vals), 6)
        return stats
