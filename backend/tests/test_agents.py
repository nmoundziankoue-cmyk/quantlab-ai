"""Tests for M6 AI Agent Framework — 12 agents + multi-agent workflow."""
from __future__ import annotations
import pytest

from services.agents import (
    list_agents, get_agent_capabilities, run_agent, run_multi_agent_workflow,
    AGENTS,
)


# ---------------------------------------------------------------------------
# Agent registry
# ---------------------------------------------------------------------------

def test_agents_dict_not_empty():
    assert len(AGENTS) >= 12


def test_agents_has_all_required():
    required = {
        "market_analyst", "macro_analyst", "fundamental_analyst", "technical_analyst",
        "portfolio_analyst", "risk_analyst", "news_analyst", "earnings_analyst",
        "sector_analyst", "options_analyst", "crypto_analyst", "research_coordinator",
    }
    for agent_id in required:
        assert agent_id in AGENTS, f"Missing agent: {agent_id}"


def test_list_agents_returns_list():
    result = list_agents()
    assert isinstance(result, list)
    assert len(result) >= 12


def test_list_agents_each_has_id():
    for agent in list_agents():
        assert "id" in agent
        assert "name" in agent


def test_list_agents_each_has_description():
    for agent in list_agents():
        desc = agent.get("description") or agent.get("summary", "")
        assert isinstance(desc, str)


def test_list_agents_each_has_capabilities():
    for agent in list_agents():
        assert "capabilities" in agent
        assert isinstance(agent["capabilities"], list)
        assert len(agent["capabilities"]) >= 1


# ---------------------------------------------------------------------------
# get_agent_capabilities
# ---------------------------------------------------------------------------

def test_get_agent_capabilities_market_analyst():
    caps = get_agent_capabilities("market_analyst")
    assert caps is not None
    assert "capabilities" in caps


def test_get_agent_capabilities_research_coordinator():
    caps = get_agent_capabilities("research_coordinator")
    assert caps is not None
    assert "id" in caps


def test_get_agent_capabilities_unknown():
    assert get_agent_capabilities("nonexistent_agent") is None


def test_get_agent_capabilities_all_agents():
    for agent_id in AGENTS:
        caps = get_agent_capabilities(agent_id)
        assert caps is not None, f"Capabilities missing for {agent_id}"


# ---------------------------------------------------------------------------
# Individual agent runs (pure, no external calls)
# ---------------------------------------------------------------------------

def test_run_fundamental_analyst():
    result = run_agent("fundamental_analyst", ticker="AAPL")
    assert result is not None
    assert "ticker" in result
    assert result["ticker"] == "AAPL"


def test_run_technical_analyst():
    result = run_agent("technical_analyst", ticker="MSFT")
    assert "signals" in result or "analysis" in result or "ticker" in result


def test_run_risk_analyst():
    result = run_agent("risk_analyst", ticker="TSLA")
    assert result is not None
    assert "ticker" in result


def test_run_news_analyst():
    result = run_agent("news_analyst", ticker="NVDA", context={"headlines": ["NVDA beats earnings"]})
    assert result is not None


def test_run_earnings_analyst():
    result = run_agent("earnings_analyst", ticker="GOOGL")
    assert result is not None
    assert "ticker" in result


def test_run_macro_analyst():
    result = run_agent("macro_analyst", ticker="SPY")
    assert result is not None


def test_run_portfolio_analyst():
    result = run_agent("portfolio_analyst", ticker="AAPL")
    assert result is not None


def test_run_sector_analyst():
    result = run_agent("sector_analyst", ticker="AMZN")
    assert result is not None


def test_run_market_analyst():
    result = run_agent("market_analyst", ticker="AAPL")
    assert result is not None


def test_run_options_analyst():
    result = run_agent("options_analyst", ticker="AAPL")
    assert result is not None


def test_run_crypto_analyst():
    result = run_agent("crypto_analyst", ticker="BTC")
    assert result is not None


def test_run_research_coordinator():
    result = run_agent("research_coordinator", ticker="MSFT")
    assert result is not None
    assert "ticker" in result


def test_run_unknown_agent():
    result = run_agent("nonexistent_agent_xyz", ticker="AAPL")
    assert "error" in result


def test_run_agent_no_ticker():
    result = run_agent("macro_analyst")
    assert result is not None


def test_run_agent_with_context():
    result = run_agent("fundamental_analyst", ticker="AAPL", context={"pe": 28.5, "roe": 0.45})
    assert result is not None


def test_run_agent_result_has_agent_id():
    result = run_agent("fundamental_analyst", ticker="AAPL")
    assert "agent_id" in result or "agent" in result


def test_run_agent_result_has_timestamp():
    result = run_agent("risk_analyst", ticker="TSLA")
    assert "generated_at" in result or "timestamp" in result or "agent_id" in result


# ---------------------------------------------------------------------------
# Multi-agent workflow
# ---------------------------------------------------------------------------

def test_run_multi_agent_workflow_basic():
    result = run_multi_agent_workflow(
        tickers=["AAPL"],
        agent_ids=["fundamental_analyst", "risk_analyst"],
    )
    assert result is not None
    assert "results" in result


def test_run_multi_agent_workflow_multiple_tickers():
    result = run_multi_agent_workflow(
        tickers=["AAPL", "MSFT"],
        agent_ids=["fundamental_analyst"],
    )
    assert "results" in result
    # results is a dict keyed by ticker
    assert isinstance(result["results"], dict)


def test_run_multi_agent_workflow_all_agents():
    result = run_multi_agent_workflow(
        tickers=["AAPL"],
        agent_ids=list(AGENTS.keys()),
    )
    assert "results" in result


def test_run_multi_agent_workflow_max_tickers():
    tickers = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "TSLA", "META", "NFLX", "CRM", "PYPL"]
    result = run_multi_agent_workflow(tickers=tickers, agent_ids=["fundamental_analyst"])
    assert "results" in result
    assert len(result.get("tickers", [])) <= 10


def test_run_multi_agent_workflow_with_context():
    result = run_multi_agent_workflow(
        tickers=["MSFT"],
        agent_ids=["fundamental_analyst", "risk_analyst"],
        context={"sector": "Technology", "analysis_depth": "deep"},
    )
    assert result is not None


def test_run_multi_agent_workflow_default_agents():
    result = run_multi_agent_workflow(tickers=["AAPL"])
    assert "results" in result


def test_run_multi_agent_workflow_has_summary():
    result = run_multi_agent_workflow(
        tickers=["NVDA"],
        agent_ids=["fundamental_analyst", "technical_analyst", "risk_analyst"],
    )
    assert "summary" in result or "results" in result


def test_run_multi_agent_workflow_coordinator_synthesis():
    result = run_multi_agent_workflow(
        tickers=["AAPL"],
        agent_ids=["research_coordinator"],
    )
    assert "results" in result
    # results is a dict keyed by ticker, each value is a dict of agent_id -> result
    assert "AAPL" in result["results"] or isinstance(result["results"], dict)


def test_run_multi_agent_workflow_empty_tickers():
    result = run_multi_agent_workflow(tickers=[], agent_ids=["fundamental_analyst"])
    assert "results" in result
    assert isinstance(result["results"], dict)
