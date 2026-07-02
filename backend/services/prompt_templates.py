"""Structured prompt templates for the AI Research Copilot.

All templates are deterministic — no randomness, no external LLM calls.
They use structured inputs and available market data to generate
institutional-grade research scaffolding.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional


TEMPLATES: Dict[str, Dict[str, Any]] = {
    "investment_thesis": {
        "name": "Investment Thesis",
        "description": "Generate a structured investment thesis for a ticker",
        "category": "EQUITY",
        "input_fields": ["ticker", "sector", "market_cap", "price", "pe_ratio", "revenue_growth"],
    },
    "bull_case": {
        "name": "Bull Case Analysis",
        "description": "Construct a bull case with catalysts and price targets",
        "category": "EQUITY",
        "input_fields": ["ticker", "current_price", "catalysts", "upside_drivers"],
    },
    "bear_case": {
        "name": "Bear Case Analysis",
        "description": "Construct a bear case with risks and downside scenarios",
        "category": "EQUITY",
        "input_fields": ["ticker", "current_price", "risks", "downside_drivers"],
    },
    "risk_factors": {
        "name": "Risk Factors",
        "description": "Enumerate systematic and idiosyncratic risks",
        "category": "RISK",
        "input_fields": ["ticker", "sector", "leverage", "beta"],
    },
    "swot": {
        "name": "SWOT Analysis",
        "description": "Strengths, Weaknesses, Opportunities, Threats",
        "category": "FRAMEWORK",
        "input_fields": ["ticker", "company_name", "sector"],
    },
    "porter_five_forces": {
        "name": "Porter's Five Forces",
        "description": "Industry competitive dynamics analysis",
        "category": "FRAMEWORK",
        "input_fields": ["ticker", "sector", "industry"],
    },
    "company_summary": {
        "name": "Company Summary",
        "description": "Brief institutional-grade company overview",
        "category": "EQUITY",
        "input_fields": ["ticker", "company_name", "sector", "description"],
    },
    "sector_summary": {
        "name": "Sector Summary",
        "description": "Sector dynamics, key players, and macro trends",
        "category": "MACRO",
        "input_fields": ["sector", "key_tickers"],
    },
    "macro_summary": {
        "name": "Macro Summary",
        "description": "Macroeconomic environment and impact on markets",
        "category": "MACRO",
        "input_fields": ["region", "key_indicators", "central_bank"],
    },
    "earnings_summary": {
        "name": "Earnings Summary",
        "description": "Earnings analysis and guidance interpretation",
        "category": "EQUITY",
        "input_fields": ["ticker", "quarter", "eps_actual", "eps_estimate", "revenue_actual", "revenue_estimate", "guidance"],
    },
    "research_memo": {
        "name": "Research Memo",
        "description": "Concise institutional research memo",
        "category": "EQUITY",
        "input_fields": ["ticker", "recommendation", "target_price", "key_points"],
    },
    "catalyst_analysis": {
        "name": "Catalyst Analysis",
        "description": "Near-term and medium-term catalysts analysis",
        "category": "EQUITY",
        "input_fields": ["ticker", "catalysts", "timeline"],
    },
    "portfolio_summary": {
        "name": "Portfolio Summary",
        "description": "Portfolio composition, risk, and attribution summary",
        "category": "PORTFOLIO",
        "input_fields": ["portfolio_name", "tickers", "weights", "total_value"],
    },
    "full_report": {
        "name": "Full Institutional Report",
        "description": "Complete 14-section institutional research report",
        "category": "EQUITY",
        "input_fields": ["ticker", "company_name", "sector", "recommendation", "target_price"],
    },
}


def list_templates() -> List[Dict[str, Any]]:
    return [
        {"key": k, "name": v["name"], "description": v["description"], "category": v["category"], "input_fields": v["input_fields"]}
        for k, v in TEMPLATES.items()
    ]


def get_template(key: str) -> Optional[Dict[str, Any]]:
    return TEMPLATES.get(key)


# ---------------------------------------------------------------------------
# Template renderers — deterministic structured output
# ---------------------------------------------------------------------------

def render_investment_thesis(ticker: str, context: Dict[str, Any]) -> str:
    sector = context.get("sector", "N/A")
    price = context.get("price", "N/A")
    pe = context.get("pe_ratio", "N/A")
    rev_growth = context.get("revenue_growth", "N/A")
    return f"""## Investment Thesis: {ticker}

**Sector:** {sector}
**Current Price:** {price}
**P/E Ratio:** {pe}
**Revenue Growth:** {rev_growth}

### Core Thesis
{ticker} presents a compelling investment opportunity based on the following pillars:

1. **Business Quality**: The company operates in {sector} with characteristics that support durable competitive advantages.
2. **Valuation**: At {pe}x earnings, the risk/reward profile warrants further analysis relative to sector peers.
3. **Growth Trajectory**: Revenue growth of {rev_growth} indicates operational momentum.

### Key Metrics Summary
| Metric | Value |
|--------|-------|
| Price | {price} |
| P/E | {pe} |
| Revenue Growth | {rev_growth} |
| Sector | {sector} |

### Recommendation Framework
Further analysis required on: balance sheet quality, competitive moat, management track record, and macro sensitivity."""


def render_bull_case(ticker: str, context: Dict[str, Any]) -> str:
    price = context.get("current_price", "N/A")
    catalysts = context.get("catalysts", [])
    cat_list = "\n".join(f"- {c}" for c in catalysts) if catalysts else "- Identify near-term catalysts through primary research"
    return f"""## Bull Case: {ticker}

**Current Price:** {price}

### Bull Case Thesis
The bull case for {ticker} rests on execution of core business drivers and favorable macro conditions.

### Catalysts
{cat_list}

### Upside Scenario Analysis
- **Base Case Upside**: Driven by earnings beat and multiple expansion
- **Optimistic Scenario**: Acceleration in core metrics + sector re-rating
- **Bull Case Price Target**: Requires fundamental analysis of DCF and comps

### Key Assumptions
1. Revenue growth meets or exceeds current consensus estimates
2. Margin expansion from operating leverage
3. Capital allocation remains shareholder-friendly
4. Macro environment stays supportive"""


def render_bear_case(ticker: str, context: Dict[str, Any]) -> str:
    price = context.get("current_price", "N/A")
    risks = context.get("risks", [])
    risk_list = "\n".join(f"- {r}" for r in risks) if risks else "- Execution risk\n- Competitive pressure\n- Macro headwinds"
    return f"""## Bear Case: {ticker}

**Current Price:** {price}

### Bear Case Thesis
The bear case for {ticker} centers on structural headwinds and execution risk that the market may be underpricing.

### Key Risks
{risk_list}

### Downside Scenario Analysis
- **Mild Downside**: Earnings miss + guidance cut → multiple compression
- **Severe Downside**: Business model disruption or macro shock
- **Tail Risk**: Regulatory action, accounting irregularity, or liquidity event

### Key Assumptions
1. Competition intensifies and erodes pricing power
2. Cost structure remains elevated, compressing margins
3. Macro deterioration reduces end-market demand"""


def render_swot(ticker: str, context: Dict[str, Any]) -> str:
    company = context.get("company_name", ticker)
    sector = context.get("sector", "N/A")
    return f"""## SWOT Analysis: {company} ({ticker})

**Sector:** {sector}

### Strengths
- Scale advantages and established market position
- Brand recognition and customer loyalty within {sector}
- Financial strength to fund organic and inorganic growth
- Experienced management team with execution track record

### Weaknesses
- Concentration risk (geographic, product, or customer)
- Cost structure may lag peers on unit economics
- Potential legacy technology or process constraints
- Dependency on key suppliers or distribution channels

### Opportunities
- TAM expansion through new products or geographies
- M&A-driven consolidation of fragmented {sector} market
- Operational efficiency and margin improvement runway
- Secular tailwinds (technology adoption, demographics, regulation)

### Threats
- New entrants with disruptive business models
- Pricing pressure from well-capitalized competitors
- Regulatory risk specific to {sector}
- Macro sensitivity (interest rates, FX, commodity costs)"""


def render_porter_five_forces(ticker: str, context: Dict[str, Any]) -> str:
    sector = context.get("sector", "N/A")
    industry = context.get("industry", sector)
    return f"""## Porter's Five Forces: {industry} ({ticker})

### 1. Threat of New Entrants — Moderate
Capital requirements and regulatory barriers in {industry} create meaningful moats.
However, technology-enabled disruption lowers entry barriers over time.

### 2. Bargaining Power of Suppliers — Low to Moderate
Multiple supplier options exist in {industry} for most input categories.
Specialized inputs may carry higher supplier concentration risk.

### 3. Bargaining Power of Buyers — Moderate
Customer switching costs vary by segment. B2B customers with high volume have
leverage; B2C tends to be more fragmented with lower individual buyer power.

### 4. Threat of Substitutes — Low to Moderate
Direct substitutes are limited in core segments. Indirect substitution from
adjacent technology solutions represents a medium-term risk.

### 5. Competitive Rivalry — High
The {industry} space exhibits intense rivalry with multiple credible players.
Differentiation, scale, and innovation pace are key competitive dimensions.

### Overall Competitive Intensity: Moderate
*{ticker}* operates in a competitive but structured landscape with identifiable moat sources."""


def render_earnings_summary(ticker: str, context: Dict[str, Any]) -> str:
    quarter = context.get("quarter", "N/A")
    eps_a = context.get("eps_actual", "N/A")
    eps_e = context.get("eps_estimate", "N/A")
    rev_a = context.get("revenue_actual", "N/A")
    rev_e = context.get("revenue_estimate", "N/A")
    guidance = context.get("guidance", "Not provided")
    return f"""## Earnings Summary: {ticker} — {quarter}

### Headline Results
| Metric | Actual | Estimate | vs. Estimate |
|--------|--------|----------|--------------|
| EPS | {eps_a} | {eps_e} | {"Beat" if str(eps_a) > str(eps_e) else "Miss"} |
| Revenue | {rev_a} | {rev_e} | {"Beat" if str(rev_a) > str(rev_e) else "Miss"} |

### Guidance
{guidance}

### Key Themes
1. Management tone and forward visibility
2. Segment performance and margin trajectory
3. Capital allocation priorities (buybacks, dividends, capex)
4. Balance sheet health and liquidity position

### Analyst Reaction Framework
- Multiple expansion/contraction relative to guidance beat/miss
- Revision risk to consensus estimates for next 2 quarters
- Sector read-through implications"""


def render_research_memo(ticker: str, context: Dict[str, Any]) -> str:
    rec = context.get("recommendation", "NEUTRAL")
    target = context.get("target_price", "N/A")
    key_points = context.get("key_points", [])
    points_text = "\n".join(f"{i+1}. {p}" for i, p in enumerate(key_points)) if key_points else "1. Complete fundamental analysis\n2. Validate thesis against alternative data\n3. Assess risk/reward vs. position sizing"
    return f"""## Research Memo: {ticker}

**Recommendation:** {rec}
**Price Target:** {target}
**Date:** Current

### Investment Summary
{ticker} — {rec} rated with target price of {target}.

### Key Investment Points
{points_text}

### Risk/Reward
- **Upside:** Path to target price supported by identified catalysts
- **Downside:** Key risks could impair thesis execution
- **Conviction:** Based on available data and analytical framework

### Next Steps
- Monitor upcoming catalysts and data releases
- Update model upon new earnings or guidance
- Reassess position sizing relative to portfolio risk budget

*This memo is generated from structured analytical inputs.*"""


def render_full_report_structure(ticker: str, context: Dict[str, Any]) -> Dict[str, str]:
    company = context.get("company_name", ticker)
    sector = context.get("sector", "N/A")
    rec = context.get("recommendation", "NEUTRAL")
    target = context.get("target_price", "N/A")
    return {
        "executive_summary": f"## Executive Summary\n{company} ({ticker}) — {rec} | Target: {target}\n\nThis report provides a comprehensive analysis of {ticker} across fundamental, technical, and alternative data dimensions.",
        "business_description": f"## Business Description\n{company} operates in the {sector} sector. [Complete with company-specific business model, revenue segments, and geographic exposure.]",
        "industry_overview": f"## Industry Overview\nThe {sector} industry is characterized by [dynamics]. Key competitors include [peers]. Industry tailwinds/headwinds: [analysis].",
        "investment_thesis": render_investment_thesis(ticker, context),
        "bull_case": render_bull_case(ticker, context),
        "bear_case": render_bear_case(ticker, context),
        "catalysts": f"## Catalysts\n### Near-term (0-3 months)\n- Earnings release\n- Analyst day / management commentary\n\n### Medium-term (3-12 months)\n- Product launches\n- Market share gains\n\n### Long-term (12+ months)\n- TAM expansion\n- Structural shift capture",
        "financial_snapshot": f"## Financial Snapshot\n| Metric | Value |\n|--------|-------|\n| Price | {context.get('price', 'N/A')} |\n| Market Cap | {context.get('market_cap', 'N/A')} |\n| P/E | {context.get('pe_ratio', 'N/A')} |\n| Rev Growth | {context.get('revenue_growth', 'N/A')} |",
        "valuation_framework": f"## Valuation Framework\n**Primary Method:** DCF / Comparable Companies\n**Target:** {target}\n**Key Assumptions:** [Cost of capital, growth rate, terminal multiple]",
        "risk_factors": f"## Risk Factors\n1. Macro sensitivity and interest rate exposure\n2. Competitive disruption risk in {sector}\n3. Execution risk on strategic initiatives\n4. Regulatory and ESG considerations",
        "scenario_analysis": f"## Scenario Analysis\n| Scenario | Target | Probability |\n|----------|--------|-------------|\n| Bull | +30% | 25% |\n| Base | {target} | 50% |\n| Bear | -20% | 25% |",
        "technical_picture": f"## Technical Picture\nTechnical analysis of {ticker}: key levels, trend, momentum indicators. [Integrate chart data for complete technical picture.]",
        "portfolio_fit": f"## Portfolio Fit\n{ticker} offers [sector/factor] exposure. Suggested position sizing: [% of portfolio]. Correlation characteristics: [analysis].",
        "conclusion": f"## Conclusion\n{ticker} is rated **{rec}** with a target price of **{target}**. The investment case [rests on / is challenged by] [key thesis element]. Monitor [key catalysts].",
    }
