"""M18 Pydantic v2 request / response schemas for the Real-Time Institutional
Operating System.

Covers all 12 M18 service modules: Streaming Engine, Market Data Gateway,
Market Microstructure, Feature Engine, Risk Engine, Portfolio Intelligence,
Alert Engine, Economic Intelligence, News Intelligence, Earnings Intelligence,
AI Agents, and Watchlist System.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ===========================================================================
# 1. STREAMING ENGINE
# ===========================================================================

class PublishTickRequest(BaseModel):
    """Publish a tick event to the streaming bus."""
    ticker: str = Field(min_length=1, max_length=20)
    price: float = Field(gt=0)
    volume: float = Field(ge=0)
    venue: str = "UNKNOWN"
    bid: Optional[float] = Field(default=None, gt=0)
    ask: Optional[float] = Field(default=None, gt=0)


class PublishQuoteRequest(BaseModel):
    """Publish a quote event."""
    ticker: str = Field(min_length=1, max_length=20)
    bid: float = Field(gt=0)
    ask: float = Field(gt=0)
    bid_size: float = Field(ge=0)
    ask_size: float = Field(ge=0)
    venue: str = "UNKNOWN"


class PublishNewsRequest(BaseModel):
    """Publish a news event to the streaming bus."""
    ticker: Optional[str] = None
    headline: str = Field(min_length=1)
    source: str = "UNKNOWN"
    sentiment_score: float = Field(ge=-1.0, le=1.0, default=0.0)


class PublishRiskRequest(BaseModel):
    """Publish a risk event."""
    risk_type: str
    severity: str
    message: str
    value: float = 0.0
    threshold: float = 0.0


class SubscribeRequest(BaseModel):
    """Subscribe to one or more event types."""
    event_types: List[str] = Field(min_length=1)
    ticker_filter: Optional[str] = None


class StreamingMetricsResponse(BaseModel):
    """Streaming engine performance metrics."""
    total_published: int
    by_type: Dict[str, int]
    subscribers: int
    sequence: int


class ReplayRequest(BaseModel):
    """Request historical event replay from a sequence number."""
    since_sequence: int = Field(ge=0)
    event_type: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=10000)


# ===========================================================================
# 2. MARKET DATA GATEWAY
# ===========================================================================

class VenueConnectRequest(BaseModel):
    """Request to connect to a specific market venue."""
    venue: str
    asset_class: str = "EQUITY"


class SetQuoteRequest(BaseModel):
    """Manually inject a quote into a venue connector."""
    ticker: str = Field(min_length=1, max_length=20)
    bid: float = Field(gt=0)
    ask: float = Field(gt=0)
    bid_size: float = Field(ge=0, default=100.0)
    ask_size: float = Field(ge=0, default=100.0)
    venue: str


class IngestTickRequest(BaseModel):
    """Inject a tick into a venue's history buffer."""
    ticker: str = Field(min_length=1, max_length=20)
    price: float = Field(gt=0)
    volume: float = Field(ge=0)
    venue: str


class FetchQuoteRequest(BaseModel):
    """Fetch the best quote across venues."""
    ticker: str = Field(min_length=1, max_length=20)
    venues: Optional[List[str]] = None


class QuoteResponse(BaseModel):
    """Quote response for a single ticker."""
    ticker: str
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    venue: str
    spread_bps: float
    mid: float
    timestamp: str


class GatewaySummaryResponse(BaseModel):
    """Gateway-level summary of all connected venues."""
    total_venues: int
    connected_venues: int
    total_quotes: int
    venues: List[Dict[str, Any]]


# ===========================================================================
# 3. MARKET MICROSTRUCTURE
# ===========================================================================

class IngestLevel1Request(BaseModel):
    """Ingest a Level 1 (top-of-book) quote."""
    ticker: str = Field(min_length=1, max_length=20)
    bid: float = Field(gt=0)
    ask: float = Field(gt=0)
    bid_size: float = Field(ge=0)
    ask_size: float = Field(ge=0)


class IngestTradeRequest(BaseModel):
    """Ingest a trade print for microstructure analysis."""
    ticker: str = Field(min_length=1, max_length=20)
    price: float = Field(gt=0)
    volume: float = Field(ge=0)
    aggressor_side: str = "UNKNOWN"


class IngestOrderBookRequest(BaseModel):
    """Ingest a Level 2 order book snapshot."""
    ticker: str = Field(min_length=1, max_length=20)
    bids: List[List[float]] = Field(description="List of [price, size] pairs")
    asks: List[List[float]] = Field(description="List of [price, size] pairs")


class Level1Response(BaseModel):
    """Level 1 market data response."""
    ticker: str
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    spread: float
    spread_bps: float
    mid: float


class SpreadAnalyticsResponse(BaseModel):
    """Spread analytics for a single ticker."""
    ticker: str
    current_spread_bps: float
    avg_spread_bps: float
    min_spread_bps: float
    max_spread_bps: float
    quoted_spread_bps: float
    effective_spread_bps: float


class ManipulationSignalResponse(BaseModel):
    """Detected market manipulation signal."""
    ticker: str
    signal_type: str
    detected: bool
    confidence: float
    details: Dict[str, Any]


class LiquidityHeatmapResponse(BaseModel):
    """Liquidity heatmap for a ticker."""
    ticker: str
    price_levels: List[float]
    bid_sizes: List[float]
    ask_sizes: List[float]
    total_bid_liquidity: float
    total_ask_liquidity: float


# ===========================================================================
# 4. FEATURE ENGINE
# ===========================================================================

class FeatureUpdateRequest(BaseModel):
    """Update the feature engine with a new price/volume observation."""
    ticker: str = Field(min_length=1, max_length=20)
    price: float = Field(gt=0)
    volume: float = Field(ge=0, default=0.0)
    high: Optional[float] = Field(default=None, gt=0)
    low: Optional[float] = Field(default=None, gt=0)


class ComputeFeatureRequest(BaseModel):
    """Compute a specific feature for a ticker."""
    ticker: str = Field(min_length=1, max_length=20)
    window: Optional[int] = Field(default=None, ge=2)
    period: Optional[int] = Field(default=None, ge=2)


class ComputeRSIRequest(BaseModel):
    """Compute RSI for a ticker."""
    ticker: str = Field(min_length=1, max_length=20)
    window: int = Field(default=14, ge=2)


class ComputeMACDRequest(BaseModel):
    """Compute MACD for a ticker."""
    ticker: str = Field(min_length=1, max_length=20)
    fast: int = Field(default=12, ge=2)
    slow: int = Field(default=26, ge=2)
    signal: int = Field(default=9, ge=2)

    @model_validator(mode="after")
    def fast_less_than_slow(self) -> "ComputeMACDRequest":
        if self.fast >= self.slow:
            raise ValueError("fast must be less than slow")
        return self


class ComputeBetaRequest(BaseModel):
    """Compute beta relative to a benchmark."""
    ticker: str = Field(min_length=1, max_length=20)
    benchmark_ticker: str = Field(min_length=1, max_length=20)
    window: int = Field(default=60, ge=10)


class ComputeCorrelationRequest(BaseModel):
    """Compute correlation between two tickers."""
    ticker1: str = Field(min_length=1, max_length=20)
    ticker2: str = Field(min_length=1, max_length=20)
    window: int = Field(default=60, ge=10)


class ComputePCARequest(BaseModel):
    """Compute PCA across multiple tickers."""
    tickers: List[str] = Field(min_length=2)
    n_components: int = Field(default=3, ge=1)
    window: int = Field(default=60, ge=10)


class FeatureScalarResponse(BaseModel):
    """Single scalar feature result."""
    ticker: str
    feature: str
    value: float
    window: Optional[int] = None


class MACDResponse(BaseModel):
    """MACD computation result."""
    ticker: str
    macd_line: float
    signal_line: float
    histogram: float


class FeatureSnapshotResponse(BaseModel):
    """Full feature snapshot for a ticker."""
    ticker: str
    data_points: int
    features: Dict[str, Any]


# ===========================================================================
# 5. RISK ENGINE
# ===========================================================================

class UpdatePositionRequest(BaseModel):
    """Add or update a position in the risk engine."""
    ticker: str = Field(min_length=1, max_length=20)
    quantity: float
    market_price: float = Field(gt=0)
    sector: str = "UNKNOWN"
    country: str = "US"
    currency: str = "USD"
    adv: float = Field(default=1_000_000.0, gt=0)
    beta: float = Field(default=1.0)


class SetNavRequest(BaseModel):
    """Set the portfolio NAV for the risk engine."""
    nav: float = Field(gt=0)


class AddPnlObservationRequest(BaseModel):
    """Add a daily P&L observation for VaR computation."""
    pnl: float


class ComputeVaRRequest(BaseModel):
    """Compute portfolio VaR."""
    confidence: float = Field(default=0.95, ge=0.5, le=0.999)
    window: int = Field(default=252, ge=10)


class ComputeESRequest(BaseModel):
    """Compute Expected Shortfall."""
    confidence: float = Field(default=0.95, ge=0.5, le=0.999)


class StressTestRequest(BaseModel):
    """Run a stress-test scenario on the portfolio."""
    scenario_name: str = Field(min_length=1)
    shock_pct: float = Field(default=0.0, ge=-1.0, le=1.0)
    equity_shock: Optional[float] = None
    affected_sectors: Optional[List[str]] = None
    positions: Optional[List[Any]] = None


class RiskAlertThresholdsRequest(BaseModel):
    """Thresholds for triggering risk alerts."""
    var_threshold_pct: float = Field(default=0.02, ge=0)
    leverage_threshold: float = Field(default=3.0, ge=0)
    concentration_threshold: float = Field(default=0.25, ge=0)
    drawdown_threshold_pct: float = Field(default=0.10, ge=0)


class MarginRequest(BaseModel):
    """Compute margin usage for a given requirement."""
    margin_requirement_pct: float = Field(default=0.25, ge=0.01, le=1.0)
    maintenance_pct: float = Field(default=0.15, ge=0.01, le=1.0)


class GapRiskRequest(BaseModel):
    """Compute gap risk under a named scenario."""
    scenario_name: str = "OVERNIGHT_5PCT"
    gap_pct: float = Field(default=0.05, ge=0, le=1.0)


class LiquidityRiskRequest(BaseModel):
    """Compute liquidity risk at a given participation rate."""
    participation_rate: float = Field(default=0.25, ge=0.01, le=1.0)


# ===========================================================================
# 6. PORTFOLIO INTELLIGENCE
# ===========================================================================

class UpdateHoldingRequest(BaseModel):
    """Add or update a holding in the portfolio intelligence engine."""
    ticker: str = Field(min_length=1, max_length=20)
    weight: float = Field(ge=0, le=1)
    sector: str = "UNKNOWN"
    expected_return: float = 0.08
    volatility: float = Field(default=0.20, ge=0)
    cost_basis: float = Field(default=100.0, gt=0)
    current_price: float = Field(default=100.0, gt=0)
    quantity: float = Field(default=0.0, ge=0)


class BrinsonAttributionRequest(BaseModel):
    """Brinson-Hood-Beebower attribution inputs."""
    portfolio_sector_weights: Dict[str, float]
    benchmark_sector_weights: Dict[str, float]
    portfolio_sector_returns: Dict[str, float]
    benchmark_sector_returns: Dict[str, float]
    benchmark_total_return: float


class FactorAttributionRequest(BaseModel):
    """Factor-based attribution inputs."""
    portfolio_return: float
    factor_exposures: Dict[str, float]
    factor_returns: Dict[str, float]


class RebalancingRequest(BaseModel):
    """Request portfolio rebalancing recommendations."""
    target_weights: Dict[str, float]
    tolerance: float = Field(default=0.01, ge=0, le=0.5)

    @field_validator("target_weights")
    @classmethod
    def weights_reasonable(cls, v: Dict[str, float]) -> Dict[str, float]:
        if sum(v.values()) > 1.01:
            raise ValueError("Target weights must sum to at most 1.0")
        return v


class EfficientFrontierRequest(BaseModel):
    """Efficient frontier computation request."""
    tickers: List[str] = Field(min_length=2)
    expected_returns: Dict[str, float]
    covariance_matrix: Dict[str, Dict[str, float]]
    n_points: int = Field(default=20, ge=5, le=100)
    risk_free: float = Field(default=0.04, ge=0)


class AddReturnObservationRequest(BaseModel):
    """Record a daily return observation for tail risk analytics."""
    portfolio_return: float
    benchmark_return: float = 0.0


class PortfolioIntelSetNavRequest(BaseModel):
    """Set portfolio NAV for intelligence engine."""
    nav: float = Field(gt=0)


# ===========================================================================
# 7. ALERT ENGINE
# ===========================================================================

class AddAlertRuleRequest(BaseModel):
    """Create a new alert rule."""
    name: str = Field(min_length=1)
    alert_type: str
    severity: str
    field: str
    direction: str
    threshold: float
    ticker: Optional[str] = None
    cooldown_seconds: int = Field(default=300, ge=0)
    max_triggers: int = Field(default=0, ge=0)
    tags: List[str] = Field(default_factory=list)


class RegisterWebhookRequest(BaseModel):
    """Register a webhook for alert delivery."""
    url: str = Field(min_length=1)
    severity_filter: Optional[List[str]] = None
    alert_type_filter: Optional[List[str]] = None


class EvaluateAlertRequest(BaseModel):
    """Evaluate a market data point against all rules."""
    data: Dict[str, Any] = Field(default_factory=dict)
    ticker: Optional[str] = None
    field: str = "price"
    value: float = 0.0
    extra: Dict[str, Any] = Field(default_factory=dict)


class FireCustomAlertRequest(BaseModel):
    """Fire a custom alert without an associated rule."""
    title: Optional[str] = None
    name: Optional[str] = None
    severity: str
    message: str
    ticker: Optional[str] = None
    alert_type: str = "CUSTOM"
    value: float = 0.0
    threshold: float = 0.0


class AlertHistoryRequest(BaseModel):
    """Query alert history with optional filters."""
    ticker: Optional[str] = None
    severity: Optional[str] = None
    alert_type: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=1000)


# ===========================================================================
# 8. ECONOMIC INTELLIGENCE
# ===========================================================================

class RecordIndicatorRequest(BaseModel):
    """Record an economic indicator release."""
    name: str = Field(min_length=1)
    country: str = Field(min_length=2, max_length=3)
    indicator_type: str
    value: float
    previous_value: float = 0.0
    forecast: float = 0.0
    unit: str = ""
    frequency: str = "Monthly"


class RecordYieldCurveRequest(BaseModel):
    """Record a yield curve snapshot."""
    country: str = Field(min_length=2, max_length=3)
    tenors: Dict[str, float]

    @field_validator("tenors")
    @classmethod
    def tenors_not_empty(cls, v: Dict[str, float]) -> Dict[str, float]:
        if not v:
            raise ValueError("tenors must contain at least one entry")
        return v


class ScheduleEconomicEventRequest(BaseModel):
    """Schedule an economic calendar event."""
    name: str = Field(min_length=1)
    country: str = Field(min_length=2, max_length=3)
    indicator_type: str
    scheduled_time: datetime
    forecast: float = 0.0
    previous: float = 0.0
    importance: str = "MEDIUM"


class AssessCountryRiskRequest(BaseModel):
    """Assess macro risk for a country."""
    country: str = Field(min_length=2, max_length=3)
    fiscal_risk: float = Field(default=30.0, ge=0, le=100)
    monetary_risk: float = Field(default=25.0, ge=0, le=100)
    external_risk: float = Field(default=20.0, ge=0, le=100)
    political_risk: float = Field(default=20.0, ge=0, le=100)
    growth_outlook: float = 0.025
    key_risks: List[str] = Field(default_factory=list)


class ListIndicatorsRequest(BaseModel):
    """Filter economic indicators."""
    country: Optional[str] = None
    indicator_type: Optional[str] = None


# ===========================================================================
# 9. NEWS INTELLIGENCE
# ===========================================================================

class IngestNewsRequest(BaseModel):
    """Ingest a news article for NLP annotation."""
    headline: str = Field(min_length=1)
    body: str = ""
    source: str = "UNKNOWN"
    url: str = ""
    tags: List[str] = Field(default_factory=list)


class NewsSearchRequest(BaseModel):
    """Search ingested news articles."""
    query: str = ""
    ticker: Optional[str] = None
    category: Optional[str] = None
    sentiment: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=500)


class RegisterTickersRequest(BaseModel):
    """Register known ticker symbols for accurate extraction."""
    tickers: List[str] = Field(min_length=1)


class NewsArticleResponse(BaseModel):
    """Single news article with NLP annotations."""
    article_id: str
    headline: str
    source: str
    sentiment: str
    sentiment_score: float
    category: str
    tickers_mentioned: List[str]
    market_signal: str
    signal_strength: str
    published_at: str
    ingested_at: str


class NewsTrendResponse(BaseModel):
    """A detected news trend."""
    trend_id: str
    topic: str
    article_count: int
    velocity: float
    avg_sentiment: float
    top_tickers: List[str]
    description: str
    detected_at: str


class NewsSignalResponse(BaseModel):
    """News-driven trading signal."""
    signal_id: str
    ticker: str
    direction: str
    confidence: float
    rationale: str
    generated_at: str


class DetectTrendsRequest(BaseModel):
    """Request trend detection in the news stream."""
    window_hours: float = Field(default=4.0, ge=0.1, le=168.0)
    min_articles: int = Field(default=3, ge=1)


# ===========================================================================
# 10. EARNINGS INTELLIGENCE
# ===========================================================================

class RecordEarningsReleaseRequest(BaseModel):
    """Record an earnings release."""
    ticker: str = Field(min_length=1, max_length=20)
    fiscal_quarter: str = Field(min_length=1)
    reported_eps: float
    consensus_eps: float
    reported_revenue: float = Field(ge=0)
    consensus_revenue: float = Field(ge=0)
    gross_margin: float = Field(default=0.0, ge=0, le=1.0)
    operating_margin: float = Field(default=0.0, ge=-5.0, le=1.0)
    net_income_usd_m: float = 0.0
    guidance_direction: str = "NOT_PROVIDED"
    guidance_eps_low: float = 0.0
    guidance_eps_high: float = 0.0
    post_earnings_drift_1d: float = 0.0


class AddEarningsEstimateRequest(BaseModel):
    """Add an analyst earnings estimate."""
    ticker: str = Field(min_length=1, max_length=20)
    fiscal_quarter: str = Field(min_length=1)
    analyst_firm: str = Field(min_length=1)
    eps_estimate: float
    revenue_estimate: float = Field(ge=0)
    price_target: float = Field(default=0.0, ge=0)
    rating: str = "HOLD"


class ScheduleEarningsRequest(BaseModel):
    """Schedule an earnings calendar event."""
    ticker: str = Field(min_length=1, max_length=20)
    fiscal_quarter: str = Field(min_length=1)
    expected_date: datetime
    time_of_day: str = "AMC"
    consensus_eps: float = 0.0
    consensus_revenue: float = Field(default=0.0, ge=0)
    num_estimates: int = Field(default=0, ge=0)


class GenerateEarningsSignalRequest(BaseModel):
    """Generate a trading signal from earnings data."""
    ticker: str = Field(min_length=1, max_length=20)
    eps_surprise_pct: float = 0.0
    revenue_surprise_pct: float = 0.0
    guidance_direction: str = "NOT_PROVIDED"


class ForecastDriftRequest(BaseModel):
    """Forecast post-earnings price drift."""
    ticker: str = Field(min_length=1, max_length=20)
    eps_surprise_pct: float


class EarningsSignalResponse(BaseModel):
    """Earnings-driven trading signal."""
    signal_id: str
    ticker: str
    signal: str
    confidence: float
    factors: Dict[str, float]
    rationale: str
    generated_at: str


# ===========================================================================
# 11. AI AGENTS
# ===========================================================================

class RunAgentRequest(BaseModel):
    """Run a single AI agent with a task payload."""
    agent_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class RunAllAgentsRequest(BaseModel):
    """Run multiple agents and aggregate results."""
    payloads: Dict[str, Dict[str, Any]]
    include_report: bool = True


class AgentResultResponse(BaseModel):
    """Result from a single AI agent run."""
    run_id: str
    agent_type: str
    status: str
    action: str
    confidence: float
    summary: str
    findings: Dict[str, Any]
    recommendations: List[str]
    risk_flags: List[str]
    duration_ms: float
    timestamp: str


class OrchestratorResultResponse(BaseModel):
    """Aggregated multi-agent orchestration result."""
    session_id: str
    consensus_action: str
    consensus_confidence: float
    summary: str
    total_duration_ms: float
    agent_results: Dict[str, AgentResultResponse]
    timestamp: str


class AgentHistoryRequest(BaseModel):
    """Request agent run history."""
    agent_type: str
    limit: int = Field(default=20, ge=1, le=200)


# ===========================================================================
# 12. WATCHLIST SYSTEM
# ===========================================================================

class CreateWatchlistRequest(BaseModel):
    """Create a new watchlist."""
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    category: str = "CUSTOM"
    owner: str = "default"
    is_shared: bool = False
    tags: List[str] = Field(default_factory=list)


class UpdateWatchlistRequest(BaseModel):
    """Update watchlist metadata."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_shared: Optional[bool] = None
    tags: Optional[List[str]] = None


class AddWatchlistItemRequest(BaseModel):
    """Add an instrument to a watchlist."""
    ticker: str = Field(min_length=1, max_length=20)
    notes: str = ""
    tags: List[str] = Field(default_factory=list)
    target_price: float = Field(default=0.0, ge=0)
    stop_loss: float = Field(default=0.0, ge=0)
    sector: str = "UNKNOWN"
    conviction: int = Field(default=5, ge=1, le=10)
    alert_thresholds: Dict[str, float] = Field(default_factory=dict)


class UpdateWatchlistItemRequest(BaseModel):
    """Update metadata on a watchlist item."""
    notes: Optional[str] = None
    target_price: Optional[float] = Field(default=None, ge=0)
    stop_loss: Optional[float] = Field(default=None, ge=0)
    conviction: Optional[int] = Field(default=None, ge=1, le=10)
    tags: Optional[List[str]] = None


class UpdateWatchlistPriceRequest(BaseModel):
    """Update market price for a watchlist item."""
    ticker: str = Field(min_length=1, max_length=20)
    price: float = Field(gt=0)
    volume_ratio: float = Field(default=1.0, ge=0)
    rsi: float = Field(default=50.0, ge=0, le=100)


class WatchlistScreenRequest(BaseModel):
    """Screen watchlist items against criteria."""
    min_conviction: Optional[int] = Field(default=None, ge=1, le=10)
    max_conviction: Optional[int] = Field(default=None, ge=1, le=10)
    sector: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class PortfolioOverlapRequest(BaseModel):
    """Analyse overlap between a watchlist and a portfolio."""
    list_id: str
    portfolio_tickers: List[str] = Field(min_length=1)


class WatchlistItemResponse(BaseModel):
    """Watchlist item response."""
    item_id: str
    ticker: str
    sector: str
    conviction: int
    target_price: float
    stop_loss: float
    last_price: float
    notes: str
    tags: List[str]
    added_at: str


class WatchlistResponse(BaseModel):
    """Watchlist metadata response."""
    list_id: str
    name: str
    description: str
    category: str
    owner: str
    is_shared: bool
    item_count: int
    created_at: str
    updated_at: str
    tags: List[str]


class WatchlistDetailResponse(WatchlistResponse):
    """Full watchlist with items."""
    items: List[WatchlistItemResponse]


# ===========================================================================
# COMMON / SHARED
# ===========================================================================

class SuccessResponse(BaseModel):
    """Generic success acknowledgement."""
    success: bool = True
    message: str = "OK"


class DeleteResponse(BaseModel):
    """Deletion acknowledgement."""
    deleted: bool
    id: str


class PaginatedRequest(BaseModel):
    """Common pagination parameters."""
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
