"""Tests for M9 Phase 7 — AI Research Copilot agents and orchestrator."""
import pytest
from services.ai_agents import (
    get_agent, list_agents, get_orchestrator, ResearchOrchestrator,
    AGENT_TYPES, MacroEconomistAgent, EquityResearcherAgent,
    OptionsStrategistAgent, PortfolioManagerAgent, RiskOfficerAgent,
    QuantResearcherAgent, NewsAnalystAgent,
)


# ---------------------------------------------------------------------------
# Agent registry
# ---------------------------------------------------------------------------

class TestAgentRegistry:
    def test_all_agent_types_registered(self):
        for agent_type in AGENT_TYPES:
            assert get_agent(agent_type) is not None

    def test_get_nonexistent(self):
        assert get_agent("nonexistent_agent") is None

    def test_list_agents_count(self):
        agents = list_agents()
        assert len(agents) == len(AGENT_TYPES)

    def test_list_agents_structure(self):
        for a in list_agents():
            assert "type" in a
            assert "description" in a
            assert "tools" in a


# ---------------------------------------------------------------------------
# Individual agents
# ---------------------------------------------------------------------------

class TestIndividualAgents:
    def _ctx(self, tickers=None):
        return {"tickers": tickers or ["AAPL"]}

    def test_macro_economist(self):
        r = MacroEconomistAgent().analyze("rate policy", self._ctx())
        assert r.agent_type == "macro_economist"
        assert 0 < r.confidence <= 1
        assert len(r.content) > 20

    def test_equity_researcher(self):
        r = EquityResearcherAgent().analyze("MSFT valuation", self._ctx(["MSFT"]))
        assert r.agent_type == "equity_researcher"
        assert len(r.citations) > 0

    def test_options_strategist(self):
        r = OptionsStrategistAgent().analyze("AAPL options", self._ctx())
        assert r.agent_type == "options_strategist"
        assert len(r.tools_used) > 0

    def test_portfolio_manager(self):
        r = PortfolioManagerAgent().analyze("rebalance", self._ctx())
        assert r.agent_type == "portfolio_manager"
        assert r.confidence > 0

    def test_risk_officer(self):
        r = RiskOfficerAgent().analyze("portfolio risk", self._ctx())
        assert "VaR" in r.content or "risk" in r.content.lower()

    def test_quant_researcher(self):
        r = QuantResearcherAgent().analyze("momentum factor", self._ctx())
        assert r.agent_type == "quant_researcher"

    def test_news_analyst(self):
        r = NewsAnalystAgent().analyze("earnings news", self._ctx(["NVDA"]))
        assert r.agent_type == "news_analyst"
        assert len(r.content) > 0

    def test_citation_structure(self):
        r = MacroEconomistAgent().analyze("inflation", self._ctx())
        for c in r.citations:
            assert hasattr(c, "source")
            assert hasattr(c, "relevance")
            assert 0 <= c.relevance <= 1

    def test_timestamp_present(self):
        r = EquityResearcherAgent().analyze("growth", self._ctx())
        assert "T" in r.timestamp  # ISO 8601


# ---------------------------------------------------------------------------
# Orchestrator: session management
# ---------------------------------------------------------------------------

class TestOrchestrator:
    def setup_method(self):
        self.orch = ResearchOrchestrator()

    def test_create_session(self):
        s = self.orch.create_session("AAPL deep dive", {"tickers": ["AAPL"]})
        assert s.id
        assert s.topic == "AAPL deep dive"

    def test_get_session(self):
        s = self.orch.create_session("test")
        found = self.orch.get_session(s.id)
        assert found is s

    def test_get_nonexistent_session(self):
        assert self.orch.get_session("fake-id") is None

    def test_list_sessions(self):
        self.orch.create_session("A")
        self.orch.create_session("B")
        sessions = self.orch.list_sessions()
        assert len(sessions) >= 2

    def test_delete_session(self):
        s = self.orch.create_session("delete me")
        assert self.orch.delete_session(s.id)
        assert self.orch.get_session(s.id) is None

    def test_delete_nonexistent(self):
        assert not self.orch.delete_session("fake")


# ---------------------------------------------------------------------------
# Orchestrator: single agent query
# ---------------------------------------------------------------------------

class TestOrchestratorQuery:
    def setup_method(self):
        self.orch = ResearchOrchestrator()
        self.session = self.orch.create_session("research", {"tickers": ["AAPL"]})

    def test_run_single_agent(self):
        resp = self.orch.run_agent(self.session.id, "macro_economist", "rate analysis")
        assert resp is not None
        assert resp.agent_type == "macro_economist"

    def test_run_invalid_agent(self):
        resp = self.orch.run_agent(self.session.id, "invalid_agent", "query")
        assert resp is None

    def test_run_invalid_session(self):
        resp = self.orch.run_agent("fake-session", "macro_economist", "query")
        assert resp is None

    def test_message_appended_to_session(self):
        self.orch.run_agent(self.session.id, "equity_researcher", "valuation")
        s = self.orch.get_session(self.session.id)
        assert len(s.messages) == 1

    def test_run_all_agents(self):
        responses = self.orch.run_all_agents(self.session.id, "comprehensive analysis")
        assert len(responses) == len(AGENT_TYPES)


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------

class TestSynthesis:
    def setup_method(self):
        self.orch = ResearchOrchestrator()
        self.session = self.orch.create_session("synthesis test", {"tickers": ["MSFT"]})

    def test_empty_synthesis(self):
        result = self.orch.synthesize(self.session.id)
        assert "No responses" in result["synthesis"] or result["consensus_confidence"] == 0.0

    def test_synthesis_after_queries(self):
        self.orch.run_all_agents(self.session.id, "MSFT outlook")
        result = self.orch.synthesize(self.session.id)
        assert result["agent_count"] == len(AGENT_TYPES)
        assert 0 < result["consensus_confidence"] <= 1
        assert "recommendation" in result

    def test_synthesis_key_points(self):
        self.orch.run_agent(self.session.id, "risk_officer", "risk")
        result = self.orch.synthesize(self.session.id)
        assert len(result["key_points"]) >= 1

    def test_invalid_session_synthesis(self):
        result = self.orch.synthesize("fake-id")
        assert "No responses" in result["synthesis"]

    def test_singleton_orchestrator(self):
        o1 = get_orchestrator()
        o2 = get_orchestrator()
        assert o1 is o2
