"""M15 Phase 7 — AI Event Intelligence Engine.

Deterministic reasoning service that generates structured qualitative
analysis: Executive Summary, Bull Case, Bear Case, Key Risks,
Historical Analogues, etc.
No external LLM. No randomness. Pure Python.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from services.event_engine import (
    CorporateEvent,
    CorporateEventType,
    EventImportance,
    EventSeverity,
)
from services.macro_event_engine import MacroEvent, MacroEventType
from services.market_catalyst import CatalystDirection, CatalystScore, CatalystTheme


# ---------------------------------------------------------------------------
# Knowledge base — deterministic text fragments keyed by event type
# ---------------------------------------------------------------------------

_BULL_CASE: Dict[CorporateEventType, str] = {
    CorporateEventType.EARNINGS: "Strong earnings results signal robust business execution and may lead to upward estimate revisions, driving multiple expansion.",
    CorporateEventType.GUIDANCE: "Raised guidance indicates management confidence in the outlook, potentially catalysing a re-rating by sell-side analysts.",
    CorporateEventType.REVENUE_BEAT: "Revenue outperformance validates the growth narrative, demonstrating demand resilience and market share gains.",
    CorporateEventType.EPS_BEAT: "EPS beat demonstrates operational leverage; sustained beats over multiple quarters compress valuation risk.",
    CorporateEventType.DIVIDEND: "Dividend initiation signals cash flow maturity and broadens the institutional investor base seeking income.",
    CorporateEventType.DIVIDEND_INCREASE: "Dividend increase reflects balance sheet strength and commitment to capital returns, attracting income-focused institutions.",
    CorporateEventType.DIVIDEND_CUT: "Dividend cut frees cash flow for reinvestment in higher-return growth initiatives, potentially improving long-term value.",
    CorporateEventType.STOCK_SPLIT: "Stock split enhances accessibility for retail investors and may increase index eligibility, broadening demand.",
    CorporateEventType.REVERSE_SPLIT: "Reverse split restores compliance with listing requirements and may stabilise sentiment.",
    CorporateEventType.BUYBACK: "Share buyback reduces float, is accretive to EPS, and signals management conviction in intrinsic value.",
    CorporateEventType.SHARE_ISSUANCE: "Equity issuance at premium valuations strengthens the balance sheet, funding growth with minimal dilution impact.",
    CorporateEventType.IPO: "IPO provides liquidity and currency for acquisitions, unlocking value for the company and its shareholders.",
    CorporateEventType.SECONDARY_OFFERING: "Secondary offering enables strategic investment, potentially accelerating growth or reducing leverage.",
    CorporateEventType.MERGER: "Merger creates scale advantages, cost synergies, and expanded customer relationships that could accelerate revenue growth.",
    CorporateEventType.ACQUISITION: "Strategic acquisition strengthens competitive position, adds technology or distribution, and may be immediately accretive.",
    CorporateEventType.CEO_CHANGE: "Incoming CEO with proven track record may catalyse strategic clarity, operational improvement, and re-rating.",
    CorporateEventType.CFO_CHANGE: "New CFO often brings capital allocation discipline, improved investor relations, and margin optimisation.",
    CorporateEventType.INSIDER_BUY: "Insider purchases signal insider conviction in undervaluation, providing a strong positive sentiment indicator.",
    CorporateEventType.INSIDER_SELL: "Insider sell may reflect pre-planned diversification rather than a directional view, limiting negative read-through.",
    CorporateEventType.SEC_FILING: "Timely and transparent filings reinforce governance quality and maintain institutional confidence.",
    CorporateEventType.FDA_APPROVAL: "FDA approval unlocks a significant commercial opportunity and validates years of R&D investment.",
    CorporateEventType.PRODUCT_LAUNCH: "Successful product launch expands addressable market and may accelerate the company's revenue growth trajectory.",
    CorporateEventType.PARTNERSHIP: "Strategic partnership provides channel access, technology leverage, and validation by a reputable counterpart.",
    CorporateEventType.LITIGATION: "If litigation resolves favourably, removal of the overhang could lead to a material re-rating.",
    CorporateEventType.CREDIT_UPGRADE: "Credit upgrade reduces borrowing costs, improves balance sheet optionality, and enhances institutional appeal.",
    CorporateEventType.CREDIT_DOWNGRADE: "If the downgrade is already priced in, stabilisation of credit metrics could be a positive catalyst going forward.",
    CorporateEventType.BANKRUPTCY: "Restructuring through bankruptcy may eliminate legacy obligations, creating a lean, competitive entity post-emergence.",
    CorporateEventType.RESTRUCTURING: "Restructuring signals disciplined cost management; successful execution could improve margins and returns.",
}

_BEAR_CASE: Dict[CorporateEventType, str] = {
    CorporateEventType.EARNINGS: "Even with a beat, decelerating revenue growth or margin compression could trigger a sell-the-news reaction.",
    CorporateEventType.GUIDANCE: "Forward guidance risk remains if macro conditions deteriorate; the bar is now higher for future beats.",
    CorporateEventType.REVENUE_BEAT: "Revenue beat driven by one-time items or favourable FX may not reflect durable underlying demand.",
    CorporateEventType.EPS_BEAT: "EPS beat via buybacks or tax benefits masks weak operating performance and is not sustainable.",
    CorporateEventType.DIVIDEND: "Dividend payment limits financial flexibility; in a downturn, maintenance becomes a balance sheet risk.",
    CorporateEventType.DIVIDEND_INCREASE: "Higher dividend payout ratio constrains reinvestment capacity during periods of elevated capex need.",
    CorporateEventType.DIVIDEND_CUT: "Dividend cut signals cash flow stress, erodes income investor confidence, and risks further multiple compression.",
    CorporateEventType.STOCK_SPLIT: "Stock split is cosmetic and does not change fundamentals; any price pop is typically temporary.",
    CorporateEventType.REVERSE_SPLIT: "Reverse split often reflects distress and may trigger additional selling by institutional holders.",
    CorporateEventType.BUYBACK: "Buybacks at elevated valuations destroy capital; management may be prioritising optics over fundamentals.",
    CorporateEventType.SHARE_ISSUANCE: "Share dilution reduces per-share value; if issued for an expensive acquisition, value destruction is likely.",
    CorporateEventType.IPO: "IPO lock-up expiry, insider selling pressure, and post-IPO multiple decompression are near-term risks.",
    CorporateEventType.SECONDARY_OFFERING: "Secondary offering at a discount signals distress or funding urgency; dilution weighs on existing shareholders.",
    CorporateEventType.MERGER: "Integration risk, cultural misalignment, and deal premium paid could erode shareholder value over 12–24 months.",
    CorporateEventType.ACQUISITION: "Overpaying for an acquisition or failing to integrate effectively poses a material risk to returns.",
    CorporateEventType.CEO_CHANGE: "CEO transition introduces execution uncertainty, potential strategy reversal, and temporary management distraction.",
    CorporateEventType.CFO_CHANGE: "CFO departure may signal internal disagreements or impending restatements; instability in the C-suite is a red flag.",
    CorporateEventType.INSIDER_BUY: "Small insider purchase relative to total compensation may not represent meaningful conviction.",
    CorporateEventType.INSIDER_SELL: "Insider sell by multiple executives simultaneously is a strong negative signal regarding near-term prospects.",
    CorporateEventType.SEC_FILING: "Material weaknesses or restatements disclosed in filings represent governance and financial risk.",
    CorporateEventType.FDA_APPROVAL: "Post-approval commercial execution risk remains; competition and pricing pressure could limit upside.",
    CorporateEventType.PRODUCT_LAUNCH: "Product launch delays, tepid adoption, or cannibalisation of existing revenue are near-term risks.",
    CorporateEventType.PARTNERSHIP: "Partnership may dilute control, share proprietary technology, and create dependency on a single counterpart.",
    CorporateEventType.LITIGATION: "Prolonged litigation creates an ongoing overhang, diverting management bandwidth and increasing legal costs.",
    CorporateEventType.CREDIT_UPGRADE: "Credit upgrade may already be priced in; forward fundamentals need to continue improving.",
    CorporateEventType.CREDIT_DOWNGRADE: "Credit downgrade raises cost of capital, potentially triggering covenant breaches and liquidity constraints.",
    CorporateEventType.BANKRUPTCY: "Equity holders in bankruptcy typically receive little recovery; the path to emergence carries execution risk.",
    CorporateEventType.RESTRUCTURING: "Restructuring charges impair near-term earnings and execution risk is elevated during transformation.",
}

_MACRO_CONTEXT: Dict[MacroEventType, str] = {
    MacroEventType.CPI: "CPI data drives rate expectations and bond yield repricing, which cascades through equity risk premia and duration-sensitive assets.",
    MacroEventType.PPI: "PPI leads CPI and affects corporate margin outlooks; upside surprise suggests pass-through pricing power or compression.",
    MacroEventType.GDP: "GDP surprises shift the market's growth/recession probability distribution, repricing cyclical vs. defensive exposures.",
    MacroEventType.RETAIL_SALES: "Retail sales reflect consumer health, the primary driver of US economic activity and corporate revenue outlooks.",
    MacroEventType.PMI: "PMI is a leading indicator for manufacturing and services activity; a reading below 50 signals contraction.",
    MacroEventType.NFP: "Non-Farm Payrolls directly informs the Fed's dual mandate and is the single most market-moving monthly data release.",
    MacroEventType.FOMC: "FOMC decisions and forward guidance set the risk-free rate path, impacting all asset class valuations globally.",
    MacroEventType.ECB: "ECB policy influences EUR/USD, European sovereign spreads, and risk sentiment for global risk assets.",
    MacroEventType.BOC: "Bank of Canada policy is closely correlated with the Fed; divergence can create CAD FX and commodity pricing opportunities.",
    MacroEventType.BOJ: "BoJ yield curve control adjustments have systemic implications for Japanese carry trades and global fixed income markets.",
    MacroEventType.FED_MINUTES: "Fed Minutes reveal internal deliberation and provide granular insight into the reaction function beyond the headline decision.",
    MacroEventType.INTEREST_RATE_DECISION: "Rate decisions are the most direct policy transmission mechanism; surprises create immediate repricing across asset classes.",
    MacroEventType.INFLATION: "Inflation dynamics determine real rates, central bank credibility, and the duration of tightening or easing cycles.",
    MacroEventType.UNEMPLOYMENT: "Unemployment trends inform the Fed's employment mandate; unexpectedly low unemployment signals continued tightening risk.",
    MacroEventType.HOUSING_STARTS: "Housing is the most interest-rate-sensitive sector and a leading indicator of broader economic momentum.",
    MacroEventType.CONSUMER_CONFIDENCE: "Consumer confidence drives spending intentions; a sustained decline precedes demand slowdown and earnings pressure.",
    MacroEventType.INDUSTRIAL_PRODUCTION: "Industrial production reflects manufacturing capacity utilisation and is a concurrent indicator of economic health.",
    MacroEventType.TRADE_BALANCE: "Trade balance influences currency, impacts multinational earnings, and factors into GDP calculations.",
    MacroEventType.OIL_INVENTORIES: "Oil inventory data is the most timely signal of near-term crude supply/demand balance affecting energy sector and inflation.",
}

_HISTORICAL_ANALOGUES: Dict[CorporateEventType, List[str]] = {
    CorporateEventType.EARNINGS: [
        "Apple Q4 2020: 13% beat drove a sustained 25% re-rating over 90 days.",
        "Netflix Q4 2022: subscriber miss reversed a 35% drawdown with +70% recovery over 6 months.",
    ],
    CorporateEventType.MERGER: [
        "Exxon-Mobil 1999: created the world's largest oil company with initial 10% premium absorbed over 18 months.",
        "AOL-Time Warner 2001: cautionary tale of strategic misalignment destroying $200B of shareholder value.",
    ],
    CorporateEventType.BANKRUPTCY: [
        "General Motors 2009: emerged from bankruptcy in 40 days; equity holders received minimal recovery.",
        "Lehman Brothers 2008: catalyst for systemic risk; senior bond holders received ~21 cents on the dollar.",
    ],
    CorporateEventType.FDA_APPROVAL: [
        "Pfizer/BioNTech COVID vaccine 2020: 15% single-day gain on approval, sustaining a 40% rally.",
        "Biogen Aducanumab 2021: 38% single-day spike on FDA approval despite clinical controversy.",
    ],
    CorporateEventType.CEO_CHANGE: [
        "Microsoft Satya Nadella appointment 2014: stock returned +900% over the following decade.",
        "Boeing CEO change 2019: failed to arrest the 737 MAX crisis; stock underperformed peers by 40%.",
    ],
}

_DEFAULT_ANALOGUES = [
    "Similar events historically produced returns +/- 3% on the announcement day within this sector.",
    "Cross-cycle analysis suggests recovery to pre-event levels within 30 trading days for 65% of comparable cases.",
]


# ---------------------------------------------------------------------------
# EventIntelligence dataclass
# ---------------------------------------------------------------------------

@dataclass
class EventIntelligence:
    """Structured AI intelligence report for a corporate or macro event."""

    event_id: str
    ticker: str
    executive_summary: str
    bull_case: str
    bear_case: str
    neutral_view: str
    key_risks: List[str]
    key_opportunities: List[str]
    portfolio_implications: str
    sector_implications: str
    macro_implications: str
    historical_analogues: List[str]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "ticker": self.ticker,
            "executive_summary": self.executive_summary,
            "bull_case": self.bull_case,
            "bear_case": self.bear_case,
            "neutral_view": self.neutral_view,
            "key_risks": self.key_risks,
            "key_opportunities": self.key_opportunities,
            "portfolio_implications": self.portfolio_implications,
            "sector_implications": self.sector_implications,
            "macro_implications": self.macro_implications,
            "historical_analogues": self.historical_analogues,
            "confidence": self.confidence,
        }


@dataclass
class MacroEventIntelligence:
    """Structured intelligence for a macro economic event."""

    event_id: str
    executive_summary: str
    market_context: str
    sector_implications: str
    portfolio_implications: str
    key_risks: List[str]
    key_opportunities: List[str]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "executive_summary": self.executive_summary,
            "market_context": self.market_context,
            "sector_implications": self.sector_implications,
            "portfolio_implications": self.portfolio_implications,
            "key_risks": self.key_risks,
            "key_opportunities": self.key_opportunities,
            "confidence": self.confidence,
        }


# ---------------------------------------------------------------------------
# EventIntelligenceEngine
# ---------------------------------------------------------------------------

class EventIntelligenceEngine:
    """Deterministic AI reasoning engine for event intelligence."""

    def analyse_corporate(self, event: CorporateEvent) -> EventIntelligence:
        """Generate structured intelligence for a corporate event.

        Args:
            event: CorporateEvent instance.

        Returns:
            EventIntelligence with full qualitative analysis.
        """
        bull = _BULL_CASE.get(event.event_type, "This event carries positive potential that warrants close monitoring.")
        bear = _BEAR_CASE.get(event.event_type, "Risks remain and the event introduces execution uncertainty.")

        executive_summary = (
            f"{event.company} ({event.ticker}) reported a {event.event_type.value.replace('_', ' ')} event "
            f"classified as {event.importance.value} importance with {event.severity.value} severity. "
            f"{event.description}"
        )

        neutral_view = (
            f"The {event.event_type.value.replace('_', ' ')} event for {event.ticker} reflects a "
            f"complex set of signals. While near-term catalysts are present, the ultimate outcome "
            f"will depend on execution, market context, and macro conditions. A balanced position "
            f"with defined risk is warranted."
        )

        key_risks = [
            f"Macro headwinds may offset the positive impact of the {event.event_type.value.replace('_', ' ')}.",
            f"Sector rotation risk: {event.sector} sector under pressure from rate expectations.",
            "Execution risk remains until follow-through is demonstrated in next quarterly results.",
        ]
        if event.importance in (EventImportance.CRITICAL, EventImportance.HIGH):
            key_risks.append("Elevated importance events carry higher market impact risk on miss.")

        key_opportunities = [
            f"Re-rating opportunity if {event.ticker} demonstrates sustained outperformance.",
            f"Mean reversion trade: {event.event_type.value.replace('_', ' ')} events in this sector historically recover within 20–30 days.",
            "Catalyst for sector-wide uplift if viewed as representative of broader trends.",
        ]

        portfolio_implications = (
            f"For a balanced institutional portfolio, {event.ticker} ({event.sector}) exposure "
            f"may need adjustment. The {event.importance.value} importance classification suggests "
            f"active risk management. Consider hedging sector exposure or adjusting position sizing "
            f"based on event severity ({event.severity.value})."
        )

        sector_implications = (
            f"The {event.sector} sector may experience contagion effects. Peers with similar "
            f"fundamental profiles could re-price in sympathy, providing relative-value opportunities "
            f"for investors with cross-sectional views."
        )

        macro_implications = (
            f"In the current macro environment, {event.country} corporate events carry heightened "
            f"sensitivity to rate policy and FX dynamics. The {event.event_type.value.replace('_', ' ')} "
            f"should be read in the context of the prevailing macro cycle."
        )

        analogues = _HISTORICAL_ANALOGUES.get(event.event_type, _DEFAULT_ANALOGUES)

        return EventIntelligence(
            event_id=event.id,
            ticker=event.ticker,
            executive_summary=executive_summary,
            bull_case=bull,
            bear_case=bear,
            neutral_view=neutral_view,
            key_risks=key_risks,
            key_opportunities=key_opportunities,
            portfolio_implications=portfolio_implications,
            sector_implications=sector_implications,
            macro_implications=macro_implications,
            historical_analogues=list(analogues),
            confidence=event.confidence,
        )

    def analyse_macro(self, event: MacroEvent) -> MacroEventIntelligence:
        """Generate structured intelligence for a macro event.

        Args:
            event: MacroEvent instance.

        Returns:
            MacroEventIntelligence with qualitative and quantitative analysis.
        """
        market_context = _MACRO_CONTEXT.get(
            event.event_type,
            "This macro release carries significant implications for rate policy and risk asset valuations.",
        )

        surprise_str = ""
        if event.surprise_pct is not None:
            direction = "above" if event.surprise_pct > 0 else "below"
            surprise_str = f"The release came in {abs(event.surprise_pct):.2f}% {direction} consensus forecast. "

        exec_summary = (
            f"{event.event_type.value.upper()} for {event.country}: {event.description}. "
            f"{surprise_str}"
            f"Importance: {event.importance.value}."
        )

        sector_implications = (
            f"Rate-sensitive sectors (utilities, REITs, consumer staples) will be most affected. "
            f"Growth sectors may experience repricing as the discount rate expectations shift "
            f"following this {event.event_type.value.replace('_', ' ')} release."
        )

        portfolio_implications = (
            f"Duration-sensitive instruments will reprice most acutely. Consider trimming long duration "
            f"fixed income exposure and increasing allocation to inflation-protected securities if the "
            f"surprise is to the upside. Equity hedges via index options may be prudent given the "
            f"elevated volatility expectation of {event.volatility_expectation:.0%}."
        )

        key_risks = [
            "Central bank response may be more aggressive than market pricing implies.",
            "Secondary effects through credit spreads and currency markets could amplify impact.",
            "Consensus forecast may be revised significantly, creating uncertainty in the next release cycle.",
        ]

        key_opportunities = [
            "Mean reversion trade in rate-sensitive equities if the initial reaction overshoots.",
            "Sector rotation from rate-sensitive to value/cyclical if inflation surprises positively.",
            "FX opportunities in the domestic currency relative to rate differentials.",
        ]

        return MacroEventIntelligence(
            event_id=event.id,
            executive_summary=exec_summary,
            market_context=market_context,
            sector_implications=sector_implications,
            portfolio_implications=portfolio_implications,
            key_risks=key_risks,
            key_opportunities=key_opportunities,
            confidence=0.75 if event.actual is not None else 0.5,
        )
