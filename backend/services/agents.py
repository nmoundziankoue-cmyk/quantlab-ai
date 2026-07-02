"""AI Agent Framework — specialized research agents with deterministic fallbacks."""
from __future__ import annotations
from typing import Any, Dict, List, Optional

import services.prompt_templates as templates
from services.screener import MOCK_FUNDAMENTALS

AGENTS: Dict[str, Dict[str, Any]] = {
    "market_analyst": {
        "name": "Market Analyst Agent",
        "role": "Market structure, breadth, and technical analysis",
        "capabilities": ["market_summary", "breadth_analysis", "sector_rotation", "technical_overview"],
        "category": "MARKET",
    },
    "macro_analyst": {
        "name": "Macro Analyst Agent",
        "role": "Macroeconomic environment, central bank policy, and global risk factors",
        "capabilities": ["macro_summary", "rate_analysis", "fx_analysis", "commodity_overview"],
        "category": "MACRO",
    },
    "fundamental_analyst": {
        "name": "Fundamental Analyst Agent",
        "role": "Company fundamentals, valuation, and earnings analysis",
        "capabilities": ["company_summary", "financial_snapshot", "valuation_framework", "earnings_analysis"],
        "category": "EQUITY",
    },
    "technical_analyst": {
        "name": "Technical Analyst Agent",
        "role": "Price action, chart patterns, momentum, and trend analysis",
        "capabilities": ["trend_analysis", "support_resistance", "momentum_indicators", "pattern_recognition"],
        "category": "TECHNICAL",
    },
    "portfolio_analyst": {
        "name": "Portfolio Analyst Agent",
        "role": "Portfolio construction, allocation, and performance attribution",
        "capabilities": ["portfolio_summary", "allocation_analysis", "performance_attribution", "rebalancing_suggestions"],
        "category": "PORTFOLIO",
    },
    "risk_analyst": {
        "name": "Risk Analyst Agent",
        "role": "Risk factor analysis, stress testing, and drawdown management",
        "capabilities": ["risk_factors", "stress_test", "var_analysis", "tail_risk"],
        "category": "RISK",
    },
    "news_analyst": {
        "name": "News Analyst Agent",
        "role": "News monitoring, sentiment analysis, and event-driven impact",
        "capabilities": ["news_summary", "sentiment_analysis", "event_impact", "catalyst_tracking"],
        "category": "NEWS",
    },
    "earnings_analyst": {
        "name": "Earnings Analyst Agent",
        "role": "Earnings preview, analysis, and revision tracking",
        "capabilities": ["earnings_preview", "earnings_summary", "revision_analysis", "guidance_interpretation"],
        "category": "EARNINGS",
    },
    "sector_analyst": {
        "name": "Sector Analyst Agent",
        "role": "Sector dynamics, relative performance, and rotation signals",
        "capabilities": ["sector_summary", "relative_performance", "sector_rotation", "peer_comparison"],
        "category": "SECTOR",
    },
    "options_analyst": {
        "name": "Options Analyst Agent",
        "role": "Options flow, volatility surface, and positioning analysis",
        "capabilities": ["options_flow", "vol_surface", "gamma_analysis", "put_call_ratio"],
        "category": "DERIVATIVES",
    },
    "crypto_analyst": {
        "name": "Crypto Analyst Agent",
        "role": "Digital asset analysis, on-chain metrics, and DeFi dynamics",
        "capabilities": ["crypto_summary", "onchain_analysis", "defi_metrics", "narrative_tracking"],
        "category": "CRYPTO",
    },
    "research_coordinator": {
        "name": "Research Coordinator Agent",
        "role": "Orchestrates multi-agent research workflows and synthesizes outputs",
        "capabilities": ["workflow_orchestration", "synthesis", "report_compilation", "task_routing"],
        "category": "COORDINATOR",
    },
}


def list_agents() -> List[Dict[str, Any]]:
    return [
        {
            "id": agent_id,
            "name": info["name"],
            "role": info["role"],
            "capabilities": info["capabilities"],
            "category": info["category"],
        }
        for agent_id, info in AGENTS.items()
    ]


def get_agent_capabilities(agent_id: str) -> Optional[Dict[str, Any]]:
    agent = AGENTS.get(agent_id)
    if not agent:
        return None
    return {
        "id": agent_id,
        "name": agent["name"],
        "role": agent["role"],
        "capabilities": agent["capabilities"],
        "category": agent["category"],
        "input_schema": {"ticker": "str (optional)", "context": "dict (optional)"},
        "output_schema": {"result": "str", "confidence": "float", "sources": "list"},
    }


def _run_fundamental(ticker: str, context: Dict[str, Any]) -> Dict[str, Any]:
    fundamentals = MOCK_FUNDAMENTALS.get(ticker.upper(), {})
    content = templates.render_investment_thesis(ticker, {**context, **fundamentals})
    sources = ["Mock fundamental data", "Template-based analysis"]
    confidence = 0.75 if fundamentals else 0.30
    return {"result": content, "confidence": confidence, "sources": sources, "data": fundamentals}


def _run_technical(ticker: str, context: Dict[str, Any]) -> Dict[str, Any]:
    result = (
        f"## Technical Analysis: {ticker}\n\n"
        f"Technical analysis requires live price data. Key dimensions to evaluate:\n\n"
        f"1. **Trend**: Price vs. 50-day and 200-day moving averages\n"
        f"2. **Momentum**: RSI (overbought >70, oversold <30), MACD crossovers\n"
        f"3. **Volume**: Relative volume vs. 30-day average (confirms or refutes moves)\n"
        f"4. **Support/Resistance**: Prior swing highs/lows, VWAP, Fibonacci retracements\n"
        f"5. **Patterns**: Head and shoulders, double tops/bottoms, consolidation zones\n\n"
        f"*Integrate with the Markets module for live data.*"
    )
    return {"result": result, "confidence": 0.40, "sources": ["Technical framework template"]}


def _run_risk(ticker: str, context: Dict[str, Any]) -> Dict[str, Any]:
    fundamentals = MOCK_FUNDAMENTALS.get(ticker.upper(), {})
    beta = fundamentals.get("beta", 1.0)
    content = templates.render_bear_case(ticker, {
        "current_price": context.get("price", "N/A"),
        "risks": [
            f"Market beta of {beta:.2f}x amplifies drawdowns",
            "Earnings miss risk given consensus expectations",
            "Sector-specific regulatory headwinds",
            "Balance sheet stress under higher rates",
        ],
    })
    return {"result": content, "confidence": 0.70, "sources": ["Risk framework", "Mock beta data"]}


def _run_news(ticker: str, context: Dict[str, Any]) -> Dict[str, Any]:
    result = (
        f"## News & Sentiment Analysis: {ticker}\n\n"
        f"Sentiment analysis requires live news ingestion via the Alternative Data module.\n\n"
        f"**Framework Applied:**\n"
        f"- Headline sentiment scoring: positive/negative keyword analysis\n"
        f"- Source reliability weighting: SEC > institutional > media > social\n"
        f"- Event importance classification: earnings > M&A > guidance > analyst notes\n"
        f"- Market impact scoring: urgency × reliability × importance\n\n"
        f"*Ingest news events via /api/v1/alternative-data/ingest to populate this feed.*"
    )
    return {"result": result, "confidence": 0.50, "sources": ["News intelligence framework"]}


def _run_earnings(ticker: str, context: Dict[str, Any]) -> Dict[str, Any]:
    result = templates.render_earnings_summary(ticker, context)
    return {"result": result, "confidence": 0.65, "sources": ["Earnings template", "Provided context"]}


def _run_macro(_ticker: str, context: Dict[str, Any]) -> Dict[str, Any]:
    region = context.get("region", "United States")
    result = templates.render_research_memo("MACRO", {
        "recommendation": "MONITOR",
        "target_price": "N/A",
        "key_points": [
            f"Central bank policy trajectory in {region}",
            "Inflation regime and rate sensitivity",
            "Global growth differentials and FX implications",
            "Geopolitical risk premia and commodity impact",
        ],
    })
    return {"result": result, "confidence": 0.60, "sources": ["Macro analysis template"]}


def _run_portfolio(ticker: str, context: Dict[str, Any]) -> Dict[str, Any]:
    result = templates.render_research_memo(ticker, {
        "recommendation": "REVIEW",
        "target_price": "N/A",
        "key_points": [
            "Review position sizing relative to conviction score",
            "Assess correlation with existing portfolio holdings",
            "Evaluate risk-adjusted return contribution",
            "Consider rebalancing thresholds and transaction costs",
        ],
    })
    return {"result": result, "confidence": 0.55, "sources": ["Portfolio framework"]}


def _run_sector(ticker: str, context: Dict[str, Any]) -> Dict[str, Any]:
    sector = context.get("sector", "N/A")
    result = templates.render_investment_thesis(ticker, {"sector": sector, "price": "N/A"})
    result += f"\n\n## Sector Context: {sector}\n" + templates.render_porter_five_forces(ticker, {"sector": sector, "industry": sector})
    return {"result": result, "confidence": 0.65, "sources": ["Sector analysis template", "Porter Five Forces"]}


def _run_coordinator(ticker: str, context: Dict[str, Any]) -> Dict[str, Any]:
    results = {}
    for agent_id in ["fundamental_analyst", "technical_analyst", "risk_analyst"]:
        results[agent_id] = run_agent(agent_id, ticker, context)
    synthesis = (
        f"## Multi-Agent Research Synthesis: {ticker}\n\n"
        f"The Research Coordinator has synthesized outputs from 3 specialized agents:\n\n"
        f"### Fundamental View\n{results['fundamental_analyst']['result'][:500]}...\n\n"
        f"### Technical View\n{results['technical_analyst']['result'][:300]}...\n\n"
        f"### Risk View\n{results['risk_analyst']['result'][:300]}...\n\n"
        f"### Coordinator Assessment\nBased on multi-agent analysis, the weight of evidence suggests "
        f"continued monitoring of {ticker} with attention to the identified catalysts and risks."
    )
    avg_conf = sum(r["confidence"] for r in results.values()) / len(results)
    return {"result": synthesis, "confidence": round(avg_conf, 3), "sources": list(results.keys()), "sub_results": results}


_AGENT_RUNNERS = {
    "fundamental_analyst": _run_fundamental,
    "technical_analyst": _run_technical,
    "risk_analyst": _run_risk,
    "news_analyst": _run_news,
    "earnings_analyst": _run_earnings,
    "macro_analyst": _run_macro,
    "market_analyst": _run_macro,
    "portfolio_analyst": _run_portfolio,
    "sector_analyst": _run_sector,
    "options_analyst": _run_technical,
    "crypto_analyst": _run_technical,
    "research_coordinator": _run_coordinator,
}


def run_agent(agent_id: str, ticker: str = "", context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if agent_id not in AGENTS:
        return {"error": f"Unknown agent: {agent_id}", "confidence": 0.0, "sources": []}
    runner = _AGENT_RUNNERS.get(agent_id, _run_fundamental)
    result = runner(ticker or "UNKNOWN", context or {})
    result["agent_id"] = agent_id
    result["agent_name"] = AGENTS[agent_id]["name"]
    result["ticker"] = ticker
    return result


def run_multi_agent_workflow(tickers: List[str], agent_ids: Optional[List[str]] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    selected = agent_ids or ["fundamental_analyst", "risk_analyst", "news_analyst"]
    ctx = context or {}
    workflow_results: Dict[str, Any] = {}
    for ticker in tickers[:10]:
        ticker_results: Dict[str, Any] = {}
        for agent_id in selected:
            ticker_results[agent_id] = run_agent(agent_id, ticker, ctx)
        workflow_results[ticker] = ticker_results
    return {
        "tickers": tickers,
        "agents_used": selected,
        "results": workflow_results,
        "summary": f"Multi-agent workflow completed for {len(tickers)} ticker(s) using {len(selected)} agent(s).",
    }
