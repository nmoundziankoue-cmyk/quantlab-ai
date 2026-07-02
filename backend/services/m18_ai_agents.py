"""M18 — AI Agents framework: 10 specialised autonomous financial analysis agents.

Each agent implements a `run()` method that accepts a task payload and returns
a structured AgentResult. Agents are stateless across runs but maintain an
internal run history. A central AgentOrchestrator manages dispatch, chaining,
and parallel execution simulation.

Pure Python, no external libraries.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AgentType(str, Enum):
    """Identifies a specific AI agent."""
    MARKET_ANALYST = "MARKET_ANALYST"
    RISK_MONITOR = "RISK_MONITOR"
    PORTFOLIO_OPTIMIZER = "PORTFOLIO_OPTIMIZER"
    NEWS_SCOUT = "NEWS_SCOUT"
    EARNINGS_WATCHER = "EARNINGS_WATCHER"
    MACRO_STRATEGIST = "MACRO_STRATEGIST"
    TECHNICAL_ANALYST = "TECHNICAL_ANALYST"
    EXECUTION_ADVISOR = "EXECUTION_ADVISOR"
    COMPLIANCE_GUARD = "COMPLIANCE_GUARD"
    REPORT_GENERATOR = "REPORT_GENERATOR"


class AgentStatus(str, Enum):
    """Execution status of an agent run."""
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class RecommendationAction(str, Enum):
    """High-level action recommended by an agent."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    REDUCE = "REDUCE"
    HEDGE = "HEDGE"
    REBALANCE = "REBALANCE"
    REVIEW = "REVIEW"
    ALERT = "ALERT"
    NO_ACTION = "NO_ACTION"


# ---------------------------------------------------------------------------
# Core dataclasses
# ---------------------------------------------------------------------------

@dataclass
class AgentResult:
    """Structured output from a single agent run.

    Args:
        run_id: Unique run identifier.
        agent_type: Which agent produced this result.
        status: COMPLETED or FAILED.
        action: Recommended action.
        confidence: Model confidence in the recommendation (0-1).
        summary: One-paragraph narrative summary.
        findings: Key-value findings dict.
        recommendations: List of specific recommendations.
        risk_flags: Any risk issues detected.
        data: Arbitrary structured output payload.
        duration_ms: Simulated run duration in milliseconds.
        timestamp: UTC completion time.
    """

    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_type: AgentType = AgentType.MARKET_ANALYST
    status: AgentStatus = AgentStatus.COMPLETED
    action: RecommendationAction = RecommendationAction.HOLD
    confidence: float = 0.5
    summary: str = ""
    findings: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    risk_flags: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "run_id": self.run_id,
            "agent_type": self.agent_type.value,
            "status": self.status.value,
            "action": self.action.value,
            "confidence": round(self.confidence, 4),
            "summary": self.summary,
            "findings": self.findings,
            "recommendations": self.recommendations,
            "risk_flags": self.risk_flags,
            "data": self.data,
            "duration_ms": round(self.duration_ms, 1),
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class OrchestratorResult:
    """Aggregated result from the agent orchestrator.

    Args:
        session_id: Orchestration session identifier.
        agent_results: Dict of AgentType → AgentResult.
        consensus_action: Majority-vote recommended action.
        consensus_confidence: Average confidence across agents.
        summary: High-level orchestration summary.
        total_duration_ms: Wall-clock duration.
        timestamp: Completion time.
    """

    session_id: str
    agent_results: Dict[str, AgentResult]
    consensus_action: RecommendationAction
    consensus_confidence: float
    summary: str
    total_duration_ms: float
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "session_id": self.session_id,
            "agent_results": {k: v.to_dict() for k, v in self.agent_results.items()},
            "consensus_action": self.consensus_action.value,
            "consensus_confidence": round(self.consensus_confidence, 4),
            "summary": self.summary,
            "total_duration_ms": round(self.total_duration_ms, 1),
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AgentRunRecord:
    """Historical record of an agent run (lightweight).

    Args:
        run_id: Run identifier.
        agent_type: Agent that ran.
        action: Output action.
        confidence: Output confidence.
        duration_ms: Run duration.
        timestamp: Run time.
    """

    run_id: str
    agent_type: AgentType
    action: RecommendationAction
    confidence: float
    duration_ms: float
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "run_id": self.run_id,
            "agent_type": self.agent_type.value,
            "action": self.action.value,
            "confidence": round(self.confidence, 4),
            "duration_ms": round(self.duration_ms, 1),
            "timestamp": self.timestamp.isoformat(),
        }


# ---------------------------------------------------------------------------
# Base agent
# ---------------------------------------------------------------------------

class BaseAgent:
    """Abstract base for all AI agents."""

    agent_type: AgentType = AgentType.MARKET_ANALYST

    def __init__(self) -> None:
        self._history: List[AgentRunRecord] = []
        self.status: AgentStatus = AgentStatus.IDLE

    def run(self, payload: Dict[str, Any]) -> AgentResult:
        """Execute the agent.

        Args:
            payload: Task-specific input parameters.

        Returns:
            AgentResult.
        """
        raise NotImplementedError

    def _make_result(
        self,
        action: RecommendationAction,
        confidence: float,
        summary: str,
        findings: Dict[str, Any],
        recommendations: List[str],
        risk_flags: List[str],
        data: Optional[Dict[str, Any]] = None,
        duration_ms: float = 50.0,
    ) -> AgentResult:
        run_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        result = AgentResult(
            run_id=run_id,
            agent_type=self.agent_type,
            status=AgentStatus.COMPLETED,
            action=action,
            confidence=confidence,
            summary=summary,
            findings=findings,
            recommendations=recommendations,
            risk_flags=risk_flags,
            data=data or {},
            duration_ms=duration_ms,
            timestamp=now,
        )
        self._history.append(AgentRunRecord(
            run_id=run_id, agent_type=self.agent_type,
            action=action, confidence=confidence,
            duration_ms=duration_ms, timestamp=now,
        ))
        return result

    def get_history(self, limit: int = 20) -> List[AgentRunRecord]:
        """Return recent run history.

        Args:
            limit: Maximum records.

        Returns:
            List of AgentRunRecord newest first.
        """
        return list(reversed(self._history))[:limit]


# ---------------------------------------------------------------------------
# Agent 1 — Market Analyst
# ---------------------------------------------------------------------------

class MarketAnalystAgent(BaseAgent):
    """Analyses current market conditions and generates a market outlook."""

    agent_type = AgentType.MARKET_ANALYST

    def run(self, payload: Dict[str, Any]) -> AgentResult:
        """Run market analysis.

        Args:
            payload: {
                ticker: str,
                price: float,
                sma_20: float,
                rsi_14: float,
                volume_ratio: float (current/avg volume),
            }

        Returns:
            AgentResult.
        """
        ticker = payload.get("ticker", "UNKNOWN")
        price = float(payload.get("price", 100.0))
        sma_20 = float(payload.get("sma_20", price))
        rsi = float(payload.get("rsi_14", 50.0))
        vol_ratio = float(payload.get("volume_ratio", 1.0))
        price_vs_sma = (price - sma_20) / sma_20 if sma_20 > 0 else 0.0
        bullish_signals = 0
        bearish_signals = 0
        if price > sma_20:
            bullish_signals += 1
        else:
            bearish_signals += 1
        if rsi < 30:
            bullish_signals += 2
        elif rsi > 70:
            bearish_signals += 2
        if vol_ratio > 1.5 and price > sma_20:
            bullish_signals += 1
        elif vol_ratio > 1.5 and price < sma_20:
            bearish_signals += 1
        total = bullish_signals + bearish_signals
        bull_score = bullish_signals / total if total > 0 else 0.5
        if bull_score >= 0.7:
            action = RecommendationAction.BUY
        elif bull_score <= 0.3:
            action = RecommendationAction.SELL
        else:
            action = RecommendationAction.HOLD
        confidence = abs(bull_score - 0.5) * 2
        findings = {
            "price_vs_sma20_pct": round(price_vs_sma * 100, 2),
            "rsi_14": round(rsi, 2),
            "volume_ratio": round(vol_ratio, 2),
            "bullish_signals": bullish_signals,
            "bearish_signals": bearish_signals,
        }
        recs = [f"{'Momentum is positive' if bull_score > 0.5 else 'Momentum is negative'} for {ticker}"]
        if rsi < 30:
            recs.append("RSI oversold — watch for reversal")
        if rsi > 70:
            recs.append("RSI overbought — consider reducing position")
        summary = (f"{ticker} market analysis: price {price:.2f} vs SMA20 {sma_20:.2f} "
                   f"({price_vs_sma:+.1%}), RSI={rsi:.1f}, volume ratio={vol_ratio:.2f}. "
                   f"Bullish signals: {bullish_signals}, Bearish: {bearish_signals}. "
                   f"Recommendation: {action.value}.")
        return self._make_result(action, confidence, summary, findings, recs, [], duration_ms=45.0)


# ---------------------------------------------------------------------------
# Agent 2 — Risk Monitor
# ---------------------------------------------------------------------------

class RiskMonitorAgent(BaseAgent):
    """Continuously monitors portfolio risk metrics and raises flags."""

    agent_type = AgentType.RISK_MONITOR

    def run(self, payload: Dict[str, Any]) -> AgentResult:
        """Run risk monitoring analysis.

        Args:
            payload: {
                var_95_pct: float,
                gross_leverage: float,
                concentration_hhi: float,
                margin_usage_pct: float,
                max_drawdown: float,
            }

        Returns:
            AgentResult.
        """
        var_95 = float(payload.get("var_95_pct", 0.01))
        leverage = float(payload.get("gross_leverage", 1.0))
        hhi = float(payload.get("concentration_hhi", 0.1))
        margin_pct = float(payload.get("margin_usage_pct", 0.3))
        max_dd = float(payload.get("max_drawdown", 0.05))
        risk_flags: List[str] = []
        if var_95 > 0.02:
            risk_flags.append(f"VaR {var_95:.2%} exceeds 2% threshold")
        if leverage > 3.0:
            risk_flags.append(f"Gross leverage {leverage:.2f}x is high")
        if hhi > 0.25:
            risk_flags.append(f"HHI {hhi:.3f} indicates concentration risk")
        if margin_pct > 0.80:
            risk_flags.append(f"Margin usage {margin_pct:.0%} near limit")
        if max_dd > 0.15:
            risk_flags.append(f"Max drawdown {max_dd:.1%} is elevated")
        if len(risk_flags) >= 3:
            action = RecommendationAction.REDUCE
            confidence = 0.85
        elif risk_flags:
            action = RecommendationAction.HEDGE
            confidence = 0.65
        else:
            action = RecommendationAction.NO_ACTION
            confidence = 0.80
        findings = {
            "var_95_pct": round(var_95 * 100, 4),
            "gross_leverage": round(leverage, 4),
            "concentration_hhi": round(hhi, 4),
            "margin_usage_pct": round(margin_pct * 100, 2),
            "max_drawdown_pct": round(max_dd * 100, 2),
            "risk_flag_count": len(risk_flags),
        }
        recs = risk_flags if risk_flags else ["Portfolio risk metrics within acceptable bounds"]
        summary = (f"Risk monitoring complete. {len(risk_flags)} risk flags detected. "
                   f"VaR={var_95:.2%}, Leverage={leverage:.2f}x, HHI={hhi:.3f}. "
                   f"Recommendation: {action.value}.")
        return self._make_result(action, confidence, summary, findings, recs, risk_flags, duration_ms=30.0)


# ---------------------------------------------------------------------------
# Agent 3 — Portfolio Optimizer
# ---------------------------------------------------------------------------

class PortfolioOptimizerAgent(BaseAgent):
    """Analyses portfolio composition and recommends optimisation trades."""

    agent_type = AgentType.PORTFOLIO_OPTIMIZER

    def run(self, payload: Dict[str, Any]) -> AgentResult:
        """Run portfolio optimisation analysis.

        Args:
            payload: {
                current_weights: Dict[str, float],
                target_weights: Dict[str, float],
                portfolio_sharpe: float,
                nav: float,
            }

        Returns:
            AgentResult.
        """
        current = payload.get("current_weights", {})
        target = payload.get("target_weights", {})
        sharpe = float(payload.get("portfolio_sharpe", 0.5))
        nav = float(payload.get("nav", 1_000_000.0))
        deviations: List[Tuple[str, float]] = []
        for t in set(list(current.keys()) + list(target.keys())):
            c = current.get(t, 0.0)
            tgt = target.get(t, 0.0)
            deviations.append((t, abs(c - tgt)))
        deviations.sort(key=lambda x: -x[1])
        large_deviations = [(t, d) for t, d in deviations if d > 0.02]
        if large_deviations:
            action = RecommendationAction.REBALANCE
            confidence = min(0.95, 0.5 + len(large_deviations) * 0.08)
        else:
            action = RecommendationAction.NO_ACTION
            confidence = 0.75
        findings = {
            "portfolio_sharpe": round(sharpe, 4),
            "nav_usd": round(nav, 2),
            "tickers_off_target": len(large_deviations),
            "largest_deviation_pct": round(deviations[0][1] * 100, 2) if deviations else 0,
        }
        recs = [f"Rebalance {t}: deviation={d:.1%}" for t, d in large_deviations[:5]] or ["Portfolio weights aligned with target"]
        summary = (f"Portfolio optimisation: {len(large_deviations)} positions require rebalancing. "
                   f"Portfolio Sharpe={sharpe:.2f}. Recommendation: {action.value}.")
        return self._make_result(action, confidence, summary, findings, recs, [], duration_ms=60.0)


# ---------------------------------------------------------------------------
# Agent 4 — News Scout
# ---------------------------------------------------------------------------

class NewsScoutAgent(BaseAgent):
    """Scans news sentiment and generates trading signals."""

    agent_type = AgentType.NEWS_SCOUT

    def run(self, payload: Dict[str, Any]) -> AgentResult:
        """Run news sentiment analysis.

        Args:
            payload: {
                ticker: str,
                avg_sentiment_score: float,
                article_count: int,
                positive_count: int,
                negative_count: int,
                trend: str,
            }

        Returns:
            AgentResult.
        """
        ticker = payload.get("ticker", "UNKNOWN")
        score = float(payload.get("avg_sentiment_score", 0.0))
        count = int(payload.get("article_count", 0))
        pos = int(payload.get("positive_count", 0))
        neg = int(payload.get("negative_count", 0))
        trend = str(payload.get("trend", "STABLE"))
        risk_flags: List[str] = []
        if score <= -0.3:
            risk_flags.append(f"Strongly negative news sentiment ({score:.3f}) for {ticker}")
        if trend == "WORSENING":
            risk_flags.append(f"Deteriorating sentiment trend for {ticker}")
        if score >= 0.3:
            action = RecommendationAction.BUY
            confidence = min(0.90, 0.5 + abs(score))
        elif score <= -0.3:
            action = RecommendationAction.SELL
            confidence = min(0.90, 0.5 + abs(score))
        else:
            action = RecommendationAction.HOLD
            confidence = 0.4
        findings = {
            "avg_sentiment_score": round(score, 4),
            "article_count": count,
            "positive_articles": pos,
            "negative_articles": neg,
            "trend": trend,
        }
        recs = [f"News signal for {ticker}: {action.value} (score={score:.3f})"]
        summary = (f"News scout analysed {count} articles for {ticker}. "
                   f"Avg sentiment={score:.3f}, {pos} positive, {neg} negative. "
                   f"Trend={trend}. Recommendation: {action.value}.")
        return self._make_result(action, confidence, summary, findings, recs, risk_flags, duration_ms=25.0)


# ---------------------------------------------------------------------------
# Agent 5 — Earnings Watcher
# ---------------------------------------------------------------------------

class EarningsWatcherAgent(BaseAgent):
    """Monitors upcoming earnings and analyses historical surprise patterns."""

    agent_type = AgentType.EARNINGS_WATCHER

    def run(self, payload: Dict[str, Any]) -> AgentResult:
        """Run earnings analysis.

        Args:
            payload: {
                ticker: str,
                eps_surprise_pct: float,
                revenue_surprise_pct: float,
                guidance_direction: str,
                beat_rate: float,
                post_drift_avg: float,
            }

        Returns:
            AgentResult.
        """
        ticker = payload.get("ticker", "UNKNOWN")
        eps_surp = float(payload.get("eps_surprise_pct", 0.0))
        rev_surp = float(payload.get("revenue_surprise_pct", 0.0))
        guidance = str(payload.get("guidance_direction", "NOT_PROVIDED"))
        beat_rate = float(payload.get("beat_rate", 0.5))
        drift_avg = float(payload.get("post_drift_avg", 0.0))
        composite = eps_surp * 0.5 + rev_surp * 0.25 + (0.25 if guidance == "RAISED" else (-0.25 if guidance == "LOWERED" else 0.0))
        if composite >= 0.05:
            action = RecommendationAction.BUY
        elif composite <= -0.05:
            action = RecommendationAction.SELL
        else:
            action = RecommendationAction.HOLD
        confidence = min(0.90, 0.45 + abs(composite) * 2)
        risk_flags = [f"Guidance lowered for {ticker}"] if guidance == "LOWERED" else []
        findings = {
            "eps_surprise_pct": round(eps_surp * 100, 2),
            "revenue_surprise_pct": round(rev_surp * 100, 2),
            "guidance": guidance,
            "historical_beat_rate": round(beat_rate, 4),
            "avg_post_earnings_drift_pct": round(drift_avg * 100, 2),
            "composite_score": round(composite, 4),
        }
        recs = [f"Earnings composite signal {composite:+.3f}: {action.value} for {ticker}"]
        summary = (f"Earnings analysis for {ticker}: EPS surprise={eps_surp:+.2%}, "
                   f"Rev surprise={rev_surp:+.2%}, Guidance={guidance}. "
                   f"Historical beat rate={beat_rate:.0%}. Recommendation: {action.value}.")
        return self._make_result(action, confidence, summary, findings, recs, risk_flags, duration_ms=35.0)


# ---------------------------------------------------------------------------
# Agent 6 — Macro Strategist
# ---------------------------------------------------------------------------

class MacroStrategistAgent(BaseAgent):
    """Translates macroeconomic data into portfolio positioning recommendations."""

    agent_type = AgentType.MACRO_STRATEGIST

    def run(self, payload: Dict[str, Any]) -> AgentResult:
        """Run macro strategy analysis.

        Args:
            payload: {
                gdp_growth: float,
                inflation: float,
                yield_spread_2s10s: float,
                recession_prob_12m: float,
                pmi: float,
            }

        Returns:
            AgentResult.
        """
        gdp = float(payload.get("gdp_growth", 0.02))
        inflation = float(payload.get("inflation", 0.03))
        spread = float(payload.get("yield_spread_2s10s", 0.01))
        rec_prob = float(payload.get("recession_prob_12m", 0.15))
        pmi = float(payload.get("pmi", 52.0))
        risk_flags: List[str] = []
        if rec_prob > 0.4:
            risk_flags.append(f"Recession probability {rec_prob:.0%} is elevated")
        if spread < 0:
            risk_flags.append(f"Inverted yield curve (2s10s={spread:.3f})")
        if inflation > 0.05:
            risk_flags.append(f"High inflation {inflation:.1%}")
        macro_score = (gdp / 0.03) * 0.3 + (pmi - 50) / 10 * 0.3 - rec_prob * 0.4
        if macro_score > 0.2:
            action = RecommendationAction.BUY
        elif macro_score < -0.2:
            action = RecommendationAction.REDUCE
        else:
            action = RecommendationAction.HOLD
        confidence = min(0.80, 0.40 + abs(macro_score) * 0.6)
        findings = {
            "gdp_growth_pct": round(gdp * 100, 2),
            "inflation_pct": round(inflation * 100, 2),
            "yield_spread_2s10s": round(spread, 4),
            "recession_prob_12m": round(rec_prob, 4),
            "pmi": round(pmi, 1),
            "macro_score": round(macro_score, 4),
        }
        recs = risk_flags if risk_flags else [f"Macro environment is supportive. Maintain allocation."]
        summary = (f"Macro analysis: GDP={gdp:.2%}, Inflation={inflation:.2%}, "
                   f"Recession prob={rec_prob:.0%}, PMI={pmi:.1f}. "
                   f"Macro score={macro_score:.3f}. Recommendation: {action.value}.")
        return self._make_result(action, confidence, summary, findings, recs, risk_flags, duration_ms=55.0)


# ---------------------------------------------------------------------------
# Agent 7 — Technical Analyst
# ---------------------------------------------------------------------------

class TechnicalAnalystAgent(BaseAgent):
    """Performs comprehensive technical analysis using multiple indicators."""

    agent_type = AgentType.TECHNICAL_ANALYST

    def run(self, payload: Dict[str, Any]) -> AgentResult:
        """Run technical analysis.

        Args:
            payload: {
                ticker: str,
                rsi: float,
                macd: float,
                macd_signal: float,
                atr: float,
                price: float,
                bollinger_upper: float,
                bollinger_lower: float,
                volume_ratio: float,
            }

        Returns:
            AgentResult.
        """
        ticker = payload.get("ticker", "UNKNOWN")
        rsi = float(payload.get("rsi", 50.0))
        macd = float(payload.get("macd", 0.0))
        macd_sig = float(payload.get("macd_signal", 0.0))
        atr = float(payload.get("atr", 1.0))
        price = float(payload.get("price", 100.0))
        bb_upper = float(payload.get("bollinger_upper", price * 1.02))
        bb_lower = float(payload.get("bollinger_lower", price * 0.98))
        vol_ratio = float(payload.get("volume_ratio", 1.0))
        bulls = 0
        bears = 0
        if rsi < 30:
            bulls += 2
        elif rsi > 70:
            bears += 2
        if macd > macd_sig:
            bulls += 1
        else:
            bears += 1
        if price < bb_lower:
            bulls += 1
        elif price > bb_upper:
            bears += 1
        if vol_ratio > 1.5:
            if macd > macd_sig:
                bulls += 1
            else:
                bears += 1
        total = bulls + bears
        bull_pct = bulls / total if total > 0 else 0.5
        if bull_pct >= 0.65:
            action = RecommendationAction.BUY
        elif bull_pct <= 0.35:
            action = RecommendationAction.SELL
        else:
            action = RecommendationAction.HOLD
        confidence = abs(bull_pct - 0.5) * 1.8
        findings = {
            "rsi_14": round(rsi, 2),
            "macd_histogram": round(macd - macd_sig, 4),
            "atr_14": round(atr, 4),
            "price_vs_bb_upper_pct": round((price - bb_upper) / bb_upper * 100, 2),
            "price_vs_bb_lower_pct": round((price - bb_lower) / bb_lower * 100, 2),
            "bullish_signals": bulls,
            "bearish_signals": bears,
        }
        recs = [f"Technical composite for {ticker}: {bull_pct:.0%} bullish → {action.value}"]
        summary = (f"Technical analysis for {ticker}: RSI={rsi:.1f}, "
                   f"MACD {'bullish' if macd > macd_sig else 'bearish'} cross, "
                   f"{'At/below BB lower' if price <= bb_lower else 'At/above BB upper' if price >= bb_upper else 'Mid-band'}. "
                   f"Recommendation: {action.value}.")
        return self._make_result(action, confidence, summary, findings, recs, [], duration_ms=40.0)


# ---------------------------------------------------------------------------
# Agent 8 — Execution Advisor
# ---------------------------------------------------------------------------

class ExecutionAdvisorAgent(BaseAgent):
    """Recommends optimal execution strategy for a given order."""

    agent_type = AgentType.EXECUTION_ADVISOR

    def run(self, payload: Dict[str, Any]) -> AgentResult:
        """Run execution advisory analysis.

        Args:
            payload: {
                ticker: str,
                side: str (BUY/SELL),
                quantity: float,
                adv: float,
                volatility: float,
                urgency: str (LOW/MEDIUM/HIGH),
            }

        Returns:
            AgentResult.
        """
        ticker = payload.get("ticker", "UNKNOWN")
        side = str(payload.get("side", "BUY"))
        qty = float(payload.get("quantity", 100.0))
        adv = float(payload.get("adv", 1_000_000.0))
        vol = float(payload.get("volatility", 0.20))
        urgency = str(payload.get("urgency", "MEDIUM"))
        participation_rate = qty / adv if adv > 0 else 0.0
        risk_flags: List[str] = []
        if participation_rate > 0.10:
            risk_flags.append(f"Order is {participation_rate:.0%} of ADV — significant market impact expected")
        if urgency == "HIGH" and vol > 0.30:
            risk_flags.append("High-urgency order in volatile market — consider TWAP")
        if participation_rate > 0.20:
            strategy = "VWAP"
        elif urgency == "HIGH":
            strategy = "MARKET"
        elif vol > 0.30:
            strategy = "TWAP"
        else:
            strategy = "LIMIT"
        est_slippage_bps = participation_rate * vol * 10000 * 0.1
        findings = {
            "participation_rate_pct": round(participation_rate * 100, 3),
            "estimated_slippage_bps": round(est_slippage_bps, 2),
            "recommended_strategy": strategy,
            "volatility_pct": round(vol * 100, 2),
            "urgency": urgency,
        }
        action = RecommendationAction.REVIEW if risk_flags else RecommendationAction.NO_ACTION
        confidence = 0.72
        recs = [f"Use {strategy} strategy for {side} {qty:.0f} shares of {ticker}"]
        if risk_flags:
            recs.extend(risk_flags)
        summary = (f"Execution advisory for {side} {qty:.0f} {ticker}: "
                   f"participation={participation_rate:.2%}, volatility={vol:.1%}. "
                   f"Recommended strategy: {strategy}, estimated slippage={est_slippage_bps:.1f}bps.")
        return self._make_result(action, confidence, summary, findings, recs, risk_flags, duration_ms=20.0)


# ---------------------------------------------------------------------------
# Agent 9 — Compliance Guard
# ---------------------------------------------------------------------------

class ComplianceGuardAgent(BaseAgent):
    """Checks orders and positions against compliance rules."""

    agent_type = AgentType.COMPLIANCE_GUARD

    def run(self, payload: Dict[str, Any]) -> AgentResult:
        """Run compliance checks.

        Args:
            payload: {
                ticker: str,
                position_pct: float,
                sector_concentration_pct: float,
                gross_leverage: float,
                num_positions: int,
                is_restricted: bool,
            }

        Returns:
            AgentResult.
        """
        ticker = payload.get("ticker", "UNKNOWN")
        pos_pct = float(payload.get("position_pct", 0.05))
        sector_conc = float(payload.get("sector_concentration_pct", 0.20))
        leverage = float(payload.get("gross_leverage", 1.0))
        n_pos = int(payload.get("num_positions", 20))
        restricted = bool(payload.get("is_restricted", False))
        risk_flags: List[str] = []
        if restricted:
            risk_flags.append(f"{ticker} is on the restricted list — trade blocked")
        if pos_pct > 0.10:
            risk_flags.append(f"Single-position limit breach: {ticker}={pos_pct:.1%} > 10%")
        if sector_conc > 0.30:
            risk_flags.append(f"Sector concentration {sector_conc:.1%} exceeds 30% limit")
        if leverage > 4.0:
            risk_flags.append(f"Leverage {leverage:.2f}x exceeds 4x compliance limit")
        if n_pos < 5:
            risk_flags.append(f"Portfolio has only {n_pos} positions — diversification concern")
        if restricted or (pos_pct > 0.10 and sector_conc > 0.30):
            action = RecommendationAction.ALERT
        elif risk_flags:
            action = RecommendationAction.REVIEW
        else:
            action = RecommendationAction.NO_ACTION
        confidence = 0.95
        findings = {
            "position_pct": round(pos_pct * 100, 2),
            "sector_concentration_pct": round(sector_conc * 100, 2),
            "gross_leverage": round(leverage, 4),
            "num_positions": n_pos,
            "is_restricted": restricted,
            "violations": len(risk_flags),
        }
        recs = risk_flags if risk_flags else ["No compliance violations detected"]
        summary = (f"Compliance review for {ticker}: {len(risk_flags)} violation(s) detected. "
                   f"Pos={pos_pct:.1%}, Sector={sector_conc:.1%}, Leverage={leverage:.2f}x. "
                   f"Status: {action.value}.")
        return self._make_result(action, confidence, summary, findings, recs, risk_flags, duration_ms=15.0)


# ---------------------------------------------------------------------------
# Agent 10 — Report Generator
# ---------------------------------------------------------------------------

class ReportGeneratorAgent(BaseAgent):
    """Synthesises findings from all other agents into a narrative report."""

    agent_type = AgentType.REPORT_GENERATOR

    def run(self, payload: Dict[str, Any]) -> AgentResult:
        """Generate a consolidated investment report.

        Args:
            payload: {
                ticker: str,
                agent_results: List[Dict] of serialised AgentResult dicts,
            }

        Returns:
            AgentResult with 'report' key in data.
        """
        ticker = payload.get("ticker", "UNKNOWN")
        results: List[Dict[str, Any]] = payload.get("agent_results", [])
        actions: List[str] = [r.get("action", "HOLD") for r in results]
        buy_count = actions.count("BUY") + actions.count("STRONG_BUY")
        sell_count = actions.count("SELL") + actions.count("STRONG_SELL") + actions.count("REDUCE")
        hold_count = len(actions) - buy_count - sell_count
        confidences = [float(r.get("confidence", 0.5)) for r in results]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.5
        risk_flags: List[str] = []
        for r in results:
            risk_flags.extend(r.get("risk_flags", []))
        risk_flags = list(set(risk_flags))[:10]
        if buy_count > sell_count and buy_count > hold_count:
            consensus = RecommendationAction.BUY
        elif sell_count > buy_count and sell_count > hold_count:
            consensus = RecommendationAction.SELL
        elif risk_flags:
            consensus = RecommendationAction.REVIEW
        else:
            consensus = RecommendationAction.HOLD
        report_lines = [
            f"# Institutional Research Report — {ticker}",
            f"",
            f"## Executive Summary",
            f"Multi-agent consensus: **{consensus.value}** with average confidence {avg_conf:.0%}.",
            f"Analysis based on {len(results)} agent modules.",
            f"",
            f"## Signal Breakdown",
            f"- Bullish signals: {buy_count}",
            f"- Bearish signals: {sell_count}",
            f"- Neutral signals: {hold_count}",
            f"",
            f"## Risk Flags ({len(risk_flags)})",
        ]
        for flag in risk_flags:
            report_lines.append(f"- {flag}")
        report_lines += [
            f"",
            f"## Agent Summaries",
        ]
        for r in results:
            report_lines.append(f"- {r.get('agent_type', 'AGENT')}: {r.get('action', 'HOLD')} "
                                 f"(confidence={float(r.get('confidence', 0.5)):.0%}) — "
                                 f"{r.get('summary', '')[:100]}")
        findings = {
            "buy_signals": buy_count,
            "sell_signals": sell_count,
            "hold_signals": hold_count,
            "avg_confidence": round(avg_conf, 4),
            "total_risk_flags": len(risk_flags),
        }
        recs = [f"Consensus recommendation: {consensus.value} for {ticker}"]
        full_report = "\n".join(report_lines)
        summary = (f"Report for {ticker}: {buy_count}B/{sell_count}S/{hold_count}H across "
                   f"{len(results)} agents. Consensus={consensus.value} at {avg_conf:.0%} confidence.")
        return self._make_result(
            consensus, avg_conf, summary, findings, recs, risk_flags,
            data={"report": full_report, "ticker": ticker}, duration_ms=10.0,
        )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

_AGENT_REGISTRY: Dict[AgentType, type] = {
    AgentType.MARKET_ANALYST: MarketAnalystAgent,
    AgentType.RISK_MONITOR: RiskMonitorAgent,
    AgentType.PORTFOLIO_OPTIMIZER: PortfolioOptimizerAgent,
    AgentType.NEWS_SCOUT: NewsScoutAgent,
    AgentType.EARNINGS_WATCHER: EarningsWatcherAgent,
    AgentType.MACRO_STRATEGIST: MacroStrategistAgent,
    AgentType.TECHNICAL_ANALYST: TechnicalAnalystAgent,
    AgentType.EXECUTION_ADVISOR: ExecutionAdvisorAgent,
    AgentType.COMPLIANCE_GUARD: ComplianceGuardAgent,
    AgentType.REPORT_GENERATOR: ReportGeneratorAgent,
}


class AgentOrchestrator:
    """Central orchestrator for dispatching and coordinating AI agents."""

    def __init__(self) -> None:
        self._agents: Dict[AgentType, BaseAgent] = {
            atype: cls() for atype, cls in _AGENT_REGISTRY.items()
        }
        self._run_history: List[OrchestratorResult] = []

    def run_agent(
        self, agent_type: AgentType, payload: Dict[str, Any]
    ) -> AgentResult:
        """Run a single agent.

        Args:
            agent_type: Which agent to run.
            payload: Task input.

        Returns:
            AgentResult.
        """
        agent = self._agents.get(agent_type)
        if agent is None:
            raise ValueError(f"Unknown agent type: {agent_type}")
        return agent.run(payload)

    def run_all(
        self,
        payloads: Dict[AgentType, Dict[str, Any]],
        include_report: bool = True,
    ) -> OrchestratorResult:
        """Run all specified agents and aggregate results.

        Args:
            payloads: Dict of AgentType → payload for each agent to run.
            include_report: Whether to run the ReportGeneratorAgent as final step.

        Returns:
            OrchestratorResult.
        """
        session_id = str(uuid.uuid4())
        start = datetime.now(timezone.utc)
        results: Dict[str, AgentResult] = {}
        for atype, payload in payloads.items():
            agent = self._agents.get(atype)
            if agent:
                result = agent.run(payload)
                results[atype.value] = result
        if include_report and AgentType.REPORT_GENERATOR not in payloads:
            reporter = self._agents[AgentType.REPORT_GENERATOR]
            report_payload = {
                "ticker": next(iter(payloads.values()), {}).get("ticker", "PORTFOLIO"),
                "agent_results": [r.to_dict() for r in results.values()],
            }
            report_result = reporter.run(report_payload)
            results[AgentType.REPORT_GENERATOR.value] = report_result
        actions = [r.action for r in results.values()]
        buy_count = sum(1 for a in actions if a in {RecommendationAction.BUY})
        sell_count = sum(1 for a in actions if a in {RecommendationAction.SELL, RecommendationAction.REDUCE})
        if buy_count > sell_count:
            consensus = RecommendationAction.BUY
        elif sell_count > buy_count:
            consensus = RecommendationAction.SELL
        else:
            consensus = RecommendationAction.HOLD
        avg_conf = (sum(r.confidence for r in results.values()) / len(results)
                    if results else 0.5)
        end = datetime.now(timezone.utc)
        duration_ms = (end - start).total_seconds() * 1000
        orch_result = OrchestratorResult(
            session_id=session_id,
            agent_results=results,
            consensus_action=consensus,
            consensus_confidence=avg_conf,
            summary=(f"Orchestration complete: {len(results)} agents, consensus={consensus.value}, "
                     f"confidence={avg_conf:.0%}."),
            total_duration_ms=duration_ms,
            timestamp=end,
        )
        self._run_history.append(orch_result)
        return orch_result

    def get_agent_history(
        self, agent_type: AgentType, limit: int = 20
    ) -> List[AgentRunRecord]:
        """Return history for a specific agent.

        Args:
            agent_type: Agent to query.
            limit: Maximum records.

        Returns:
            List of AgentRunRecord.
        """
        agent = self._agents.get(agent_type)
        return agent.get_history(limit) if agent else []

    def list_agents(self) -> List[Dict[str, str]]:
        """Return metadata for all registered agents.

        Returns:
            List of dicts with agent_type and status.
        """
        return [
            {"agent_type": atype.value, "status": agent.status.value}
            for atype, agent in self._agents.items()
        ]

    def get_orchestration_history(self, limit: int = 10) -> List[OrchestratorResult]:
        """Return recent orchestration session results.

        Args:
            limit: Maximum sessions.

        Returns:
            List of OrchestratorResult.
        """
        return list(reversed(self._run_history))[:limit]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_orchestrator: Optional[AgentOrchestrator] = None


def get_agent_orchestrator() -> AgentOrchestrator:
    """Return the singleton AgentOrchestrator.

    Returns:
        Shared AgentOrchestrator instance.
    """
    global _default_orchestrator
    if _default_orchestrator is None:
        _default_orchestrator = AgentOrchestrator()
    return _default_orchestrator
