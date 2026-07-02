"""Institutional research report generator.

Produces structured markdown reports with 14 sections.
Deterministic — no external LLM required.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from models.research_workspace import ReportDraft
from schemas.research_workspace import ReportDraftCreate, ReportDraftUpdate
import services.prompt_templates as templates
import services.research_workspace as ws_svc

REPORT_SECTIONS = [
    "executive_summary",
    "business_description",
    "industry_overview",
    "investment_thesis",
    "bull_case",
    "bear_case",
    "catalysts",
    "financial_snapshot",
    "valuation_framework",
    "risk_factors",
    "scenario_analysis",
    "technical_picture",
    "portfolio_fit",
    "conclusion",
]


def _render_section(section: str, ticker: str, context: Dict[str, Any]) -> str:
    company = context.get("company_name", ticker)
    sector = context.get("sector", "N/A")
    rec = context.get("recommendation", "NEUTRAL")
    target = context.get("target_price", "N/A")

    if section == "executive_summary":
        return f"## Executive Summary\n\n**{company} ({ticker})** — Recommendation: **{rec}** | Target: **{target}**\n\nThis report provides comprehensive analysis of {ticker} across fundamental, technical, and alternative data dimensions. Key investment considerations are discussed across a 12-month investment horizon."
    elif section == "business_description":
        return f"## Business Description\n\n{company} operates in the **{sector}** sector. [Complete with company-specific business model, revenue segments, geographic exposure, and competitive positioning. Source: company filings, earnings transcripts.]"
    elif section == "industry_overview":
        return f"## Industry Overview\n\nThe **{sector}** industry is characterized by competitive dynamics, secular growth vectors, and evolving regulatory environments. Key competitors, market share distribution, and industry tailwinds/headwinds require sector-specific research. Market structure and barriers to entry shape the long-term value creation potential."
    elif section == "investment_thesis":
        return templates.render_investment_thesis(ticker, context)
    elif section == "bull_case":
        catalysts = context.get("catalysts", ["Earnings acceleration", "Market share gains", "Product expansion"])
        return templates.render_bull_case(ticker, {**context, "catalysts": catalysts})
    elif section == "bear_case":
        risks = context.get("risks", ["Execution risk", "Competitive pressure", "Macro headwinds"])
        return templates.render_bear_case(ticker, {**context, "risks": risks})
    elif section == "catalysts":
        return f"## Catalysts\n\n### Near-term (0–3 months)\n- Upcoming earnings release\n- Analyst day / management commentary\n- Regulatory decisions or product launches\n\n### Medium-term (3–12 months)\n- Market share trajectory\n- Margin expansion or compression\n- Capital allocation decisions (M&A, buybacks)\n\n### Long-term (12+ months)\n- TAM expansion through new geographies or verticals\n- Structural shift capture in {sector}\n- Management execution on strategic roadmap"
    elif section == "financial_snapshot":
        return (
            f"## Financial Snapshot\n\n"
            f"| Metric | Value |\n|--------|-------|\n"
            f"| Price | {context.get('price', 'N/A')} |\n"
            f"| Market Cap | {context.get('market_cap', 'N/A')} |\n"
            f"| P/E Ratio | {context.get('pe_ratio', 'N/A')} |\n"
            f"| EV/EBITDA | {context.get('ev_ebitda', 'N/A')} |\n"
            f"| Revenue Growth | {context.get('revenue_growth', 'N/A')} |\n"
            f"| EBITDA Margin | {context.get('ebitda_margin', 'N/A')} |\n"
            f"| Net Debt/EBITDA | {context.get('net_debt_ebitda', 'N/A')} |\n"
            f"| FCF Yield | {context.get('fcf_yield', 'N/A')} |"
        )
    elif section == "valuation_framework":
        return (
            f"## Valuation Framework\n\n"
            f"**Primary Method:** Discounted Cash Flow (DCF) / Comparable Company Analysis\n\n"
            f"**Price Target:** {target}\n\n"
            f"### DCF Assumptions\n- WACC: [derive from CAPM]\n- Terminal Growth Rate: [sector-specific]\n- Projection Period: 5 years\n\n"
            f"### Trading Comps\n- P/E vs. sector median\n- EV/Revenue vs. growth-adjusted peers\n- EV/EBITDA vs. leverage-adjusted peers\n\n"
            f"### Upside/Downside to Target\n| Scenario | Price | Return |\n|----------|-------|--------|\n| Bull | [+30%] | [calc] |\n| Base | {target} | [calc] |\n| Bear | [-20%] | [calc] |"
        )
    elif section == "risk_factors":
        return (
            f"## Risk Factors\n\n"
            f"### Macro Risks\n- Interest rate sensitivity and cost of capital impact\n- FX exposure for multinational operations\n- Commodity cost pass-through risk\n\n"
            f"### Industry Risks\n- Competitive disruption in {sector}\n- Technology displacement or substitution\n- Regulatory change (compliance cost, market access)\n\n"
            f"### Company-specific Risks\n- Execution on strategic initiatives\n- Key-person dependency\n- Customer or supplier concentration\n- Balance sheet / leverage constraints\n\n"
            f"### ESG Risks\n- Environmental compliance and carbon transition\n- Governance quality and shareholder alignment"
        )
    elif section == "scenario_analysis":
        return (
            f"## Scenario Analysis\n\n"
            f"| Scenario | Description | Price Impact | Probability |\n"
            f"|----------|-------------|--------------|-------------|\n"
            f"| **Bull** | Earnings beat + multiple expansion | +25–35% | 25% |\n"
            f"| **Base** | Inline results, modest growth | Target: {target} | 50% |\n"
            f"| **Bear** | Margin compression + de-rating | -15–25% | 25% |\n\n"
            f"### Key Swing Factors\n1. Revenue growth rate vs. consensus\n2. Margin trajectory\n3. Capital allocation efficiency\n4. Macro environment (rates, FX, demand)"
        )
    elif section == "technical_picture":
        return f"## Technical Picture\n\n**{ticker}** — Technical summary requires live price data integration.\n\n- **Trend:** [Derive from moving averages]\n- **Momentum:** [RSI, MACD]\n- **Key Support Levels:** [50/200 DMA]\n- **Key Resistance Levels:** [Prior highs, VWAP]\n- **Volume:** [Relative to 30-day average]\n\n*Integrate chart data via the Markets module for a complete technical picture.*"
    elif section == "portfolio_fit":
        return f"## Portfolio Fit\n\n**{ticker}** offers exposure to the **{sector}** sector with the following portfolio characteristics:\n\n- **Factor Exposure:** [Growth / Value / Quality / Momentum]\n- **Beta:** [Market sensitivity]\n- **Correlation:** [To portfolio holdings and benchmarks]\n- **Position Sizing:** [% allocation relative to conviction and portfolio risk budget]\n- **Diversification Effect:** [Does it reduce or add concentration risk?]"
    elif section == "conclusion":
        return f"## Conclusion\n\n**{ticker}** is rated **{rec}** with a 12-month price target of **{target}**.\n\nThe investment case is grounded in [core thesis element]. Near-term catalysts include [key catalysts], while the primary risks to monitor are [key risks]. Portfolio fit is [appropriate/cautious] given [portfolio context].\n\n*This report should be updated upon new earnings, material guidance changes, or significant market events.*"
    return f"## {section.replace('_', ' ').title()}\n\n[Section content for {section}]"


def generate_report(ticker: str, context: Optional[Dict[str, Any]] = None, sections: Optional[List[str]] = None) -> Dict[str, Any]:
    ctx = context or {}
    section_keys = sections or REPORT_SECTIONS
    rendered: Dict[str, str] = {}
    for s in section_keys:
        rendered[s] = _render_section(s, ticker, ctx)
    full_md = "\n\n".join(rendered.values())
    return {
        "ticker": ticker,
        "sections": rendered,
        "full_markdown": full_md,
        "section_count": len(rendered),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "context": ctx,
    }


def generate_section(ticker: str, section: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    ctx = context or {}
    content = _render_section(section, ticker, ctx)
    return {"ticker": ticker, "section": section, "content": content}


def export_html(markdown_content: str) -> str:
    lines = markdown_content.split("\n")
    html_lines = []
    in_table = False
    for line in lines:
        if line.startswith("### "):
            html_lines.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("## "):
            html_lines.append(f'<h2 class="section-title">{line[3:]}</h2>')
        elif line.startswith("# "):
            html_lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("**") and line.endswith("**"):
            html_lines.append(f"<strong>{line[2:-2]}</strong>")
        elif line.startswith("- "):
            html_lines.append(f"<li>{line[2:]}</li>")
        elif line.startswith("|"):
            if not in_table:
                html_lines.append("<table><tbody>")
                in_table = True
            cells = [c.strip() for c in line.split("|") if c.strip()]
            row_html = "".join(f"<td>{c}</td>" for c in cells)
            html_lines.append(f"<tr>{row_html}</tr>")
        elif in_table:
            html_lines.append("</tbody></table>")
            in_table = False
            if line.strip():
                html_lines.append(f"<p>{line}</p>")
        elif line.strip():
            html_lines.append(f"<p>{line}</p>")
    if in_table:
        html_lines.append("</tbody></table>")
    body = "\n".join(html_lines)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Institutional Research Report</title>
<style>
body {{font-family: Georgia, serif; max-width: 900px; margin: 40px auto; color: #1a1a1a; line-height: 1.7;}}
h1 {{font-size: 28px; border-bottom: 2px solid #1a1a1a; padding-bottom: 8px;}}
h2.section-title {{font-size: 20px; color: #1a3a6e; border-bottom: 1px solid #c0c0c0; padding-bottom: 4px; margin-top: 32px;}}
h3 {{font-size: 16px; color: #333;}}
table {{border-collapse: collapse; width: 100%; margin: 16px 0;}}
td {{border: 1px solid #ccc; padding: 8px 12px;}}
li {{margin: 4px 0;}}
p {{margin: 8px 0;}}
</style>
</head>
<body>
{body}
</body>
</html>"""
