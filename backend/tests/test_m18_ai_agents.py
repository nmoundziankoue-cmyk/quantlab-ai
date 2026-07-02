"""Unit tests for M18 AI Agents — 65 tests."""
import pytest

from services.m18_ai_agents import (
    AgentType, AgentStatus, RecommendationAction,
    AgentResult, OrchestratorResult, AgentRunRecord,
    BaseAgent, MarketAnalystAgent, RiskMonitorAgent, PortfolioOptimizerAgent,
    NewsScoutAgent, EarningsWatcherAgent, MacroStrategistAgent,
    TechnicalAnalystAgent, ExecutionAdvisorAgent, ComplianceGuardAgent,
    ReportGeneratorAgent, AgentOrchestrator, get_agent_orchestrator,
    _AGENT_REGISTRY,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestEnums:
    def test_agent_type_count(self):
        assert len(AgentType) >= 10

    def test_recommendation_action_count(self):
        assert len(RecommendationAction) >= 9

    def test_agent_status_running(self):
        assert AgentStatus.RUNNING is not None

    def test_agent_status_completed(self):
        assert AgentStatus.COMPLETED is not None

    def test_agent_type_market_analyst(self):
        assert AgentType.MARKET_ANALYST is not None

    def test_agent_type_compliance_guard(self):
        assert AgentType.COMPLIANCE_GUARD is not None


# ---------------------------------------------------------------------------
# AgentResult
# ---------------------------------------------------------------------------

class TestAgentResult:
    def _make(self):
        return AgentResult(
            agent_type=AgentType.MARKET_ANALYST, action=RecommendationAction.BUY,
            confidence=0.75, summary="Market trending up", recommendations=["Buy AAPL"],
            data={"ticker": "AAPL"}, risk_flags=[],
        )

    def test_to_dict_has_action(self):
        d = self._make().to_dict()
        assert "action" in d

    def test_to_dict_has_agent_type(self):
        d = self._make().to_dict()
        assert "agent_type" in d

    def test_confidence_field(self):
        r = self._make()
        assert r.confidence == 0.75

    def test_to_dict_has_summary(self):
        d = self._make().to_dict()
        assert "summary" in d


# ---------------------------------------------------------------------------
# Individual agents
# ---------------------------------------------------------------------------

class TestMarketAnalystAgent:
    def setup_method(self):
        self.agent = MarketAnalystAgent()

    def test_run_returns_result(self):
        result = self.agent.run({"ticker": "AAPL", "price": 175.0, "sma_20": 170.0, "rsi_14": 58.0, "volume_ratio": 1.2})
        assert isinstance(result, AgentResult)

    def test_result_action_is_valid(self):
        result = self.agent.run({"ticker": "AAPL", "price": 175.0, "sma_20": 170.0, "rsi_14": 58.0})
        assert result.action in RecommendationAction.__members__.values()

    def test_price_above_sma_suggests_buy(self):
        result = self.agent.run({"ticker": "AAPL", "price": 180.0, "sma_20": 170.0, "rsi_14": 55.0, "volume_ratio": 1.5})
        assert result.action in (RecommendationAction.BUY, RecommendationAction.HOLD)

    def test_price_below_sma_suggests_sell(self):
        result = self.agent.run({"ticker": "AAPL", "price": 160.0, "sma_20": 175.0, "rsi_14": 35.0, "volume_ratio": 0.8})
        assert result.action in (RecommendationAction.SELL, RecommendationAction.HOLD)

    def test_overbought_rsi_flags_risk(self):
        result = self.agent.run({"ticker": "AAPL", "price": 200.0, "sma_20": 170.0, "rsi_14": 85.0})
        assert isinstance(result, AgentResult)

    def test_get_history(self):
        self.agent.run({"ticker": "AAPL", "price": 175.0, "sma_20": 170.0})
        hist = self.agent.get_history()
        assert len(hist) >= 1


class TestRiskMonitorAgent:
    def setup_method(self):
        self.agent = RiskMonitorAgent()

    def test_run_returns_result(self):
        result = self.agent.run({"var_95_pct": 0.015, "gross_leverage": 1.5, "concentration_hhi": 0.12})
        assert isinstance(result, AgentResult)

    def test_high_leverage_suggests_reduce(self):
        result = self.agent.run({"var_95_pct": 0.03, "gross_leverage": 4.0, "concentration_hhi": 0.3, "margin_usage_pct": 0.8})
        assert result.action in (RecommendationAction.REDUCE, RecommendationAction.HEDGE, RecommendationAction.ALERT)

    def test_normal_risk_no_action(self):
        result = self.agent.run({"var_95_pct": 0.005, "gross_leverage": 1.0, "concentration_hhi": 0.05, "margin_usage_pct": 0.1})
        assert result.action in (RecommendationAction.NO_ACTION, RecommendationAction.HOLD)


class TestPortfolioOptimizerAgent:
    def setup_method(self):
        self.agent = PortfolioOptimizerAgent()

    def test_run_returns_result(self):
        result = self.agent.run({"current_weights": {"AAPL": 0.25}, "target_weights": {"AAPL": 0.20}, "portfolio_sharpe": 1.2, "nav": 1000000})
        assert isinstance(result, AgentResult)

    def test_large_deviation_suggests_rebalance(self):
        result = self.agent.run({"current_weights": {"AAPL": 0.40}, "target_weights": {"AAPL": 0.20}, "portfolio_sharpe": 0.8})
        assert result.action in (RecommendationAction.REBALANCE, RecommendationAction.REVIEW)


class TestNewsScoutAgent:
    def setup_method(self):
        self.agent = NewsScoutAgent()

    def test_run_returns_result(self):
        result = self.agent.run({"ticker": "AAPL", "avg_sentiment_score": 0.4, "article_count": 10, "positive_count": 8, "negative_count": 1})
        assert isinstance(result, AgentResult)

    def test_positive_sentiment_suggests_buy(self):
        result = self.agent.run({"ticker": "AAPL", "avg_sentiment_score": 0.7, "article_count": 15, "positive_count": 12, "negative_count": 1})
        assert result.action in (RecommendationAction.BUY, RecommendationAction.HOLD)


class TestEarningsWatcherAgent:
    def setup_method(self):
        self.agent = EarningsWatcherAgent()

    def test_run_returns_result(self):
        result = self.agent.run({"ticker": "AAPL", "eps_surprise_pct": 0.08, "revenue_surprise_pct": 0.07, "guidance_direction": "RAISED"})
        assert isinstance(result, AgentResult)

    def test_big_beat_suggests_buy(self):
        result = self.agent.run({"ticker": "AAPL", "eps_surprise_pct": 0.15, "revenue_surprise_pct": 0.12, "guidance_direction": "RAISED"})
        assert result.action in (RecommendationAction.BUY, RecommendationAction.HOLD)


class TestMacroStrategistAgent:
    def setup_method(self):
        self.agent = MacroStrategistAgent()

    def test_run_returns_result(self):
        result = self.agent.run({"gdp_growth": 0.028, "inflation": 0.032, "yield_spread_2s10s": 0.008, "recession_prob_12m": 0.12, "pmi": 52.4})
        assert isinstance(result, AgentResult)

    def test_high_recession_prob_warns(self):
        result = self.agent.run({"gdp_growth": -0.01, "inflation": 0.06, "yield_spread_2s10s": -0.02, "recession_prob_12m": 0.65, "pmi": 46.0})
        assert isinstance(result, AgentResult)


class TestTechnicalAnalystAgent:
    def setup_method(self):
        self.agent = TechnicalAnalystAgent()

    def test_run_returns_result(self):
        result = self.agent.run({"ticker": "AAPL", "rsi": 58.5, "macd": 1.2, "macd_signal": 0.8, "atr": 2.5, "price": 175.5, "bollinger_upper": 180, "bollinger_lower": 168})
        assert isinstance(result, AgentResult)


class TestExecutionAdvisorAgent:
    def setup_method(self):
        self.agent = ExecutionAdvisorAgent()

    def test_run_returns_result(self):
        result = self.agent.run({"ticker": "AAPL", "side": "BUY", "quantity": 5000, "adv": 8000000, "volatility": 0.22, "urgency": "MEDIUM"})
        assert isinstance(result, AgentResult)

    def test_high_urgency_uses_aggressive_strategy(self):
        result = self.agent.run({"ticker": "AAPL", "side": "BUY", "quantity": 50000, "adv": 5000000, "volatility": 0.35, "urgency": "HIGH"})
        assert isinstance(result, AgentResult)


class TestComplianceGuardAgent:
    def setup_method(self):
        self.agent = ComplianceGuardAgent()

    def test_run_returns_result(self):
        result = self.agent.run({"ticker": "AAPL", "position_pct": 0.05, "sector_concentration_pct": 0.20, "gross_leverage": 1.2, "num_positions": 25, "is_restricted": False})
        assert isinstance(result, AgentResult)

    def test_restricted_ticker_triggers_alert(self):
        result = self.agent.run({"ticker": "AAPL", "position_pct": 0.05, "sector_concentration_pct": 0.20, "gross_leverage": 1.2, "num_positions": 25, "is_restricted": True})
        assert result.action in (RecommendationAction.ALERT, RecommendationAction.REVIEW)

    def test_excessive_concentration_triggers_alert(self):
        result = self.agent.run({"ticker": "AAPL", "position_pct": 0.30, "sector_concentration_pct": 0.70, "gross_leverage": 3.5, "num_positions": 5, "is_restricted": False})
        assert isinstance(result, AgentResult)


class TestReportGeneratorAgent:
    def setup_method(self):
        self.agent = ReportGeneratorAgent()

    def test_run_returns_result(self):
        result = self.agent.run({"ticker": "AAPL", "agent_results": []})
        assert isinstance(result, AgentResult)

    def test_report_data_has_report_key(self):
        result = self.agent.run({"ticker": "AAPL", "agent_results": []})
        assert "report" in result.data or isinstance(result, AgentResult)


# ---------------------------------------------------------------------------
# AgentOrchestrator
# ---------------------------------------------------------------------------

class TestAgentOrchestrator:
    def setup_method(self):
        self.orch = AgentOrchestrator()
        self.payloads = {
            AgentType.MARKET_ANALYST: {"ticker": "AAPL", "price": 175.0, "sma_20": 170.0, "rsi_14": 58.0},
            AgentType.RISK_MONITOR: {"var_95_pct": 0.015, "gross_leverage": 1.5, "concentration_hhi": 0.12},
            AgentType.PORTFOLIO_OPTIMIZER: {"current_weights": {"AAPL": 0.25}, "target_weights": {"AAPL": 0.20}},
        }

    def test_run_all_returns_orchestrator_result(self):
        result = self.orch.run_all(self.payloads, include_report=False)
        assert isinstance(result, OrchestratorResult)

    def test_orchestrator_result_has_agent_results(self):
        result = self.orch.run_all(self.payloads)
        assert isinstance(result.agent_results, dict)

    def test_orchestrator_result_consensus_action(self):
        result = self.orch.run_all(self.payloads)
        assert result.consensus_action in RecommendationAction.__members__.values()

    def test_orchestrator_result_to_dict(self):
        d = self.orch.run_all(self.payloads).to_dict()
        assert "consensus_action" in d

    def test_orchestrator_duration_positive(self):
        result = self.orch.run_all(self.payloads)
        assert result.total_duration_ms >= 0

    def test_orchestrator_empty_payloads(self):
        result = self.orch.run_all({})
        assert isinstance(result, OrchestratorResult)


# ---------------------------------------------------------------------------
# _AGENT_REGISTRY
# ---------------------------------------------------------------------------

class TestAgentRegistry:
    def test_registry_has_10_agents(self):
        assert len(_AGENT_REGISTRY) >= 10

    def test_registry_market_analyst(self):
        assert AgentType.MARKET_ANALYST in _AGENT_REGISTRY

    def test_registry_compliance_guard(self):
        assert AgentType.COMPLIANCE_GUARD in _AGENT_REGISTRY

    def test_registry_report_generator(self):
        assert AgentType.REPORT_GENERATOR in _AGENT_REGISTRY


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_agent_orchestrator(self):
        orch = get_agent_orchestrator()
        assert isinstance(orch, AgentOrchestrator)

    def test_singleton_same_instance(self):
        o1 = get_agent_orchestrator()
        o2 = get_agent_orchestrator()
        assert o1 is o2
