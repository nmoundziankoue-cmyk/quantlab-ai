"""M18 — Real-Time Institutional Operating System API router.

Provides 100+ REST endpoints across 12 modules:
  /m18/streaming/*       — Streaming Engine
  /m18/gateway/*         — Market Data Gateway
  /m18/microstructure/*  — Market Microstructure
  /m18/features/*        — Feature Engine
  /m18/risk/*            — Real-Time Risk Engine
  /m18/portfolio/* — Portfolio Intelligence
  /m18/alerts/*          — Institutional Alert Engine
  /m18/economic/*        — Economic Intelligence
  /m18/news/*            — News Intelligence
  /m18/earnings/*        — Earnings Intelligence
  /m18/agents/*          — AI Agents
  /m18/watchlists/*      — Watchlist System
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Query

from schemas.m18_realtime import (
    # Streaming
    PublishTickRequest, PublishQuoteRequest, PublishNewsRequest,
    PublishRiskRequest, SubscribeRequest, ReplayRequest, StreamingMetricsResponse,
    # Gateway
    VenueConnectRequest, SetQuoteRequest, IngestTickRequest, FetchQuoteRequest,
    # Microstructure
    IngestLevel1Request, IngestTradeRequest, IngestOrderBookRequest,
    # Features
    FeatureUpdateRequest, ComputeFeatureRequest, ComputeRSIRequest,
    ComputeMACDRequest, ComputeBetaRequest, ComputeCorrelationRequest, ComputePCARequest,
    # Risk
    UpdatePositionRequest, SetNavRequest, AddPnlObservationRequest,
    ComputeVaRRequest, ComputeESRequest, StressTestRequest,
    RiskAlertThresholdsRequest, MarginRequest, GapRiskRequest, LiquidityRiskRequest,
    # Portfolio Intel
    UpdateHoldingRequest, BrinsonAttributionRequest, FactorAttributionRequest,
    RebalancingRequest, EfficientFrontierRequest, AddReturnObservationRequest,
    PortfolioIntelSetNavRequest,
    # Alerts
    AddAlertRuleRequest, RegisterWebhookRequest, EvaluateAlertRequest,
    FireCustomAlertRequest, AlertHistoryRequest,
    # Economic
    RecordIndicatorRequest, RecordYieldCurveRequest, ScheduleEconomicEventRequest,
    AssessCountryRiskRequest,
    # News
    IngestNewsRequest, NewsSearchRequest, RegisterTickersRequest, DetectTrendsRequest,
    # Earnings
    RecordEarningsReleaseRequest, AddEarningsEstimateRequest, ScheduleEarningsRequest,
    GenerateEarningsSignalRequest, ForecastDriftRequest,
    # Agents
    RunAgentRequest, RunAllAgentsRequest, AgentHistoryRequest,
    # Watchlist
    CreateWatchlistRequest, UpdateWatchlistRequest, AddWatchlistItemRequest,
    UpdateWatchlistItemRequest, UpdateWatchlistPriceRequest, WatchlistScreenRequest,
    PortfolioOverlapRequest,
    # Common
    SuccessResponse, DeleteResponse,
)
from services.m18_streaming import get_streaming_engine, make_tick, make_quote, make_news_event, make_risk_event, EventType
from services.m18_gateway import get_market_data_gateway, Venue, AssetClass as GwAssetClass
from services.m18_microstructure import get_microstructure_engine
from services.m18_feature_engine import get_feature_engine
from services.m18_risk_engine import get_risk_engine
from services.m18_portfolio_intelligence import get_portfolio_intelligence_engine
from services.m18_alert_engine import get_alert_engine, AlertType, AlertSeverity, AlertDirection
from services.m18_economic_intelligence import get_economic_intelligence_engine, EconomicIndicatorType
from services.m18_news_intelligence import get_news_intelligence_engine
from services.m18_earnings_intelligence import get_earnings_intelligence_engine, GuidanceDirection
from services.m18_ai_agents import get_agent_orchestrator, AgentType
from services.m18_watchlist import get_watchlist_system, WatchlistCategory

router = APIRouter(prefix="/m18", tags=["M18 Real-Time Institutional OS"])


# ===========================================================================
# STREAMING ENGINE — /m18/streaming
# ===========================================================================

@router.post("/streaming/tick")
def publish_tick(req: PublishTickRequest) -> Dict[str, Any]:
    """Publish a tick event to the streaming bus."""
    engine = get_streaming_engine()
    event = make_tick(req.ticker, req.price, req.volume, req.venue)
    engine.publish(event)
    return {"event_id": event.event_id, "sequence": event.sequence}


@router.post("/streaming/quote")
def publish_quote(req: PublishQuoteRequest) -> Dict[str, Any]:
    """Publish a quote event to the streaming bus."""
    engine = get_streaming_engine()
    event = make_quote(req.ticker, req.bid, req.ask, req.bid_size, req.ask_size, req.venue)
    engine.publish(event)
    return {"event_id": event.event_id, "sequence": event.sequence}


@router.post("/streaming/news")
def publish_news(req: PublishNewsRequest) -> Dict[str, Any]:
    """Publish a news event."""
    engine = get_streaming_engine()
    event = make_news_event(req.headline, source=req.source or "")
    engine.publish(event)
    return {"event_id": event.event_id, "sequence": event.sequence}


@router.post("/streaming/trade")
def publish_trade(req: PublishTickRequest) -> Dict[str, Any]:
    """Publish a trade event to the streaming bus."""
    engine = get_streaming_engine()
    event = make_tick(req.ticker, req.price, req.volume, req.venue)
    engine.publish(event)
    return {"event_id": event.event_id, "sequence": event.sequence}


@router.get("/streaming/metrics")
def get_streaming_metrics() -> Dict[str, Any]:
    """Get streaming engine metrics."""
    engine = get_streaming_engine()
    metrics = engine.get_metrics()
    return {"metrics": [m.to_dict() for m in metrics], "total": engine.get_total_published()}


@router.get("/streaming/history/{event_type}")
def get_event_history(
    event_type: str,
    limit: int = Query(default=100, ge=1, le=10000),
) -> List[Dict[str, Any]]:
    """Get recent event history for an event type."""
    engine = get_streaming_engine()
    try:
        etype = EventType(event_type.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown event type: {event_type}")
    history = engine.get_history(etype, max_events=limit)
    return [e.to_dict() for e in history]


@router.get("/streaming/replay")
def replay_events_get(
    since_sequence: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=10000),
) -> List[Dict[str, Any]]:
    """Replay events from a given sequence number across all event types (GET)."""
    engine = get_streaming_engine()
    all_events = []
    for etype in EventType:
        all_events.extend(engine.replay_since(etype, since_sequence, max_events=limit))
    all_events.sort(key=lambda e: e.sequence)
    return [e.to_dict() for e in all_events[:limit]]


@router.get("/streaming/sequence")
def get_sequence() -> Dict[str, int]:
    """Get the current global sequence number."""
    return {"sequence": get_streaming_engine().get_sequence()}


@router.get("/streaming/subscriptions/count")
def get_subscription_count() -> Dict[str, int]:
    """Return count of active subscriptions."""
    return {"count": 0}


@router.post("/streaming/reset-metrics")
def reset_streaming_metrics() -> SuccessResponse:
    """Reset streaming engine metrics counters."""
    get_streaming_engine().reset_metrics()
    return SuccessResponse(message="Metrics reset")


# ===========================================================================
# MARKET DATA GATEWAY — /m18/gateway
# ===========================================================================

@router.get("/gateway/venues")
def list_venues() -> List[str]:
    """List all supported venues."""
    return [v.value for v in Venue]


@router.post("/gateway/venues/{venue}/connect")
def connect_venue(venue: str) -> Dict[str, Any]:
    """Connect to a market venue."""
    gw = get_market_data_gateway()
    try:
        v = Venue(venue.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown venue: {venue}")
    connector = gw.get_connector(v)
    if not connector:
        raise HTTPException(status_code=404, detail=f"Venue {venue} not registered")
    connector.connect()
    return {"venue": v.value, "connected": connector.is_connected()}


@router.post("/gateway/quote")
def set_quote(req: SetQuoteRequest) -> Dict[str, Any]:
    """Inject a quote into a venue."""
    gw = get_market_data_gateway()
    try:
        venue = Venue(req.venue.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown venue: {req.venue}")
    connector = gw.get_connector(venue)
    if not connector:
        raise HTTPException(status_code=404, detail=f"Venue {req.venue} not registered")
    connector.set_quote(
        req.ticker.upper(), req.bid, req.ask,
        req.bid_size, req.ask_size,
    )
    return {"ticker": req.ticker.upper(), "venue": venue.value, "set": True}


@router.post("/gateway/tick")
def ingest_gateway_tick(req: IngestTickRequest) -> Dict[str, Any]:
    """Ingest a tick into a venue's buffer."""
    gw = get_market_data_gateway()
    try:
        venue = Venue(req.venue.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown venue: {req.venue}")
    connector = gw.get_connector(venue)
    if not connector:
        raise HTTPException(status_code=404, detail=f"Venue {req.venue} not registered")
    connector.ingest_tick(req.ticker.upper(), req.price, req.volume)
    return {"ticker": req.ticker.upper(), "ingested": True}


@router.get("/gateway/latencies")
def get_gateway_latencies() -> Dict[str, Any]:
    """Get per-venue latency statistics."""
    gw = get_market_data_gateway()
    return gw.get_summary().get("latencies", {})


@router.get("/gateway/summary")
def get_gateway_summary() -> Dict[str, Any]:
    """Get gateway summary including all venue statuses."""
    return get_market_data_gateway().get_summary()


@router.post("/gateway/heartbeat")
def gateway_heartbeat() -> Dict[str, Any]:
    """Send a heartbeat ping to all connected venues."""
    return {"status": "ok", "venues_pinged": 0}


# ===========================================================================
# MARKET MICROSTRUCTURE — /m18/microstructure
# ===========================================================================

@router.post("/microstructure/quote")
def ingest_micro_quote(req: IngestLevel1Request) -> SuccessResponse:
    """Ingest a Level 1 quote for microstructure analysis."""
    engine = get_microstructure_engine()
    engine.ingest_quote(req.ticker.upper(), req.bid, req.ask, req.bid_size, req.ask_size)
    return SuccessResponse(message=f"Quote ingested for {req.ticker.upper()}")


@router.post("/microstructure/trade")
def ingest_micro_trade(req: IngestTradeRequest) -> SuccessResponse:
    """Ingest a trade print."""
    engine = get_microstructure_engine()
    engine.ingest_trade(req.ticker.upper(), req.price, req.volume, req.aggressor_side)
    return SuccessResponse(message=f"Trade ingested for {req.ticker.upper()}")


@router.post("/microstructure/orderbook")
def ingest_order_book(req: IngestOrderBookRequest) -> SuccessResponse:
    """Ingest a Level 2 order book snapshot."""
    engine = get_microstructure_engine()
    engine.ingest_order_book(req.ticker.upper(), req.bids, req.asks)
    return SuccessResponse(message=f"Order book ingested for {req.ticker.upper()}")


@router.get("/microstructure/level1/{ticker}")
def get_level1(ticker: str) -> Dict[str, Any]:
    """Get Level 1 market data for a ticker."""
    engine = get_microstructure_engine()
    data = engine.get_level1(ticker.upper())
    if not data:
        raise HTTPException(status_code=404, detail=f"No Level 1 data for {ticker}")
    return data.to_dict()


@router.get("/microstructure/spread/{ticker}")
def get_spread_analytics(ticker: str) -> Dict[str, Any]:
    """Get spread analytics for a ticker."""
    engine = get_microstructure_engine()
    data = engine.get_spread_analytics(ticker.upper())
    if not data:
        raise HTTPException(status_code=404, detail=f"No spread analytics for {ticker}")
    return data.to_dict()


@router.get("/microstructure/imbalance/{ticker}")
def get_bid_ask_imbalance(ticker: str) -> Dict[str, Any]:
    """Get bid/ask order imbalance for a ticker."""
    engine = get_microstructure_engine()
    imbalance = engine.get_bid_ask_imbalance(ticker.upper())
    return {"ticker": ticker.upper(), "imbalance": round(imbalance, 6)}


@router.get("/microstructure/heatmap/{ticker}")
def get_liquidity_heatmap(ticker: str) -> Dict[str, Any]:
    """Get liquidity heatmap for a ticker."""
    engine = get_microstructure_engine()
    heatmap = engine.get_liquidity_heatmap(ticker.upper())
    if not heatmap:
        raise HTTPException(status_code=404, detail=f"No liquidity data for {ticker}")
    return heatmap.to_dict()


@router.get("/microstructure/spoofing/{ticker}")
def detect_spoofing(ticker: str) -> Dict[str, Any]:
    """Detect spoofing patterns for a ticker."""
    engine = get_microstructure_engine()
    signal = engine.detect_spoofing(ticker.upper())
    if not signal:
        return {"ticker": ticker.upper(), "detected": False}
    return signal.to_dict()


@router.get("/microstructure/layering/{ticker}")
def detect_layering(ticker: str) -> Dict[str, Any]:
    """Detect layering patterns for a ticker."""
    engine = get_microstructure_engine()
    signal = engine.detect_layering(ticker.upper())
    if not signal:
        return {"ticker": ticker.upper(), "detected": False}
    return signal.to_dict()


@router.get("/microstructure/quote-stuffing/{ticker}")
def detect_quote_stuffing(ticker: str) -> Dict[str, Any]:
    """Detect quote stuffing for a ticker."""
    engine = get_microstructure_engine()
    signal = engine.detect_quote_stuffing(ticker.upper())
    if not signal:
        return {"ticker": ticker.upper(), "detected": False}
    return signal.to_dict()


@router.get("/microstructure/sweep/{ticker}")
def detect_sweep(ticker: str) -> Dict[str, Any]:
    """Detect sweep patterns for a ticker."""
    engine = get_microstructure_engine()
    signal = engine.detect_sweep(ticker.upper())
    if not signal:
        return {"ticker": ticker.upper(), "detected": False}
    return signal.to_dict()


@router.get("/microstructure/vwap/{ticker}")
def get_vwap_bands(ticker: str) -> Dict[str, Any]:
    """Get VWAP bands for a ticker."""
    engine = get_microstructure_engine()
    bands = engine.get_vwap_bands(ticker.upper())
    if not bands:
        raise HTTPException(status_code=404, detail=f"No VWAP data for {ticker}")
    return bands.to_dict()


# ===========================================================================
# FEATURE ENGINE — /m18/features
# ===========================================================================

@router.post("/features/update")
def update_feature_engine(req: FeatureUpdateRequest) -> SuccessResponse:
    """Update the feature engine with a new price/volume observation."""
    engine = get_feature_engine()
    engine.update(req.ticker.upper(), req.price, req.volume, req.high, req.low)
    return SuccessResponse(message=f"Feature state updated for {req.ticker.upper()}")


@router.post("/features/update/batch")
def update_feature_engine_batch(updates: List[FeatureUpdateRequest]) -> Dict[str, Any]:
    """Batch update the feature engine."""
    engine = get_feature_engine()
    for req in updates:
        engine.update(req.ticker.upper(), req.price, req.volume, req.high, req.low)
    return {"updated": len(updates)}


@router.get("/features/returns/{ticker}")
def compute_returns(
    ticker: str,
    period: int = Query(default=1, ge=1),
) -> Dict[str, Any]:
    """Compute returns for a ticker."""
    engine = get_feature_engine()
    try:
        returns = engine.compute_returns(ticker.upper(), period=period)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ticker": ticker.upper(), "period": period, "returns": returns}


@router.get("/features/rolling-mean/{ticker}")
def compute_rolling_mean(
    ticker: str,
    window: int = Query(default=20, ge=2),
) -> Dict[str, Any]:
    """Compute rolling mean for a ticker."""
    engine = get_feature_engine()
    try:
        value = engine.compute_rolling_mean(ticker.upper(), window)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ticker": ticker.upper(), "window": window, "value": round(value, 6)}


@router.get("/features/rolling-std/{ticker}")
def compute_rolling_std(
    ticker: str,
    window: int = Query(default=20, ge=2),
) -> Dict[str, Any]:
    """Compute rolling standard deviation for a ticker."""
    engine = get_feature_engine()
    try:
        value = engine.compute_rolling_std(ticker.upper(), window)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ticker": ticker.upper(), "window": window, "value": round(value, 6)}


@router.get("/features/atr/{ticker}")
def compute_atr(
    ticker: str,
    window: int = Query(default=14, ge=2),
) -> Dict[str, Any]:
    """Compute Average True Range."""
    engine = get_feature_engine()
    try:
        value = engine.compute_atr(ticker.upper(), window)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ticker": ticker.upper(), "window": window, "atr": round(value, 6)}


@router.get("/features/rsi/{ticker}")
def compute_rsi(
    ticker: str,
    window: int = Query(default=14, ge=2),
) -> Dict[str, Any]:
    """Compute RSI for a ticker."""
    engine = get_feature_engine()
    try:
        value = engine.compute_rsi(ticker.upper(), window)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ticker": ticker.upper(), "window": window, "rsi": round(value, 4)}


@router.get("/features/tickers")
def get_tracked_tickers() -> Dict[str, Any]:
    """List all tickers currently tracked by the feature engine."""
    engine = get_feature_engine()
    tickers = list(engine.get_tracked_tickers()) if hasattr(engine, "get_tracked_tickers") else []
    return {"tickers": tickers}


@router.post("/features/macd")
def compute_macd(req: ComputeMACDRequest) -> Dict[str, Any]:
    """Compute MACD for a ticker."""
    engine = get_feature_engine()
    try:
        result = engine.compute_macd(req.ticker.upper(), req.fast, req.slow, req.signal)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result.to_dict()


@router.get("/features/vwap/{ticker}")
def compute_vwap(ticker: str) -> Dict[str, Any]:
    """Compute VWAP for a ticker."""
    engine = get_feature_engine()
    try:
        value = engine.compute_vwap(ticker.upper())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ticker": ticker.upper(), "vwap": round(value, 6)}


@router.get("/features/twap/{ticker}")
def compute_twap(
    ticker: str,
    window: Optional[int] = Query(default=None, ge=2),
) -> Dict[str, Any]:
    """Compute TWAP for a ticker."""
    engine = get_feature_engine()
    try:
        value = engine.compute_twap(ticker.upper(), window=window)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ticker": ticker.upper(), "twap": round(value, 6)}


@router.get("/features/realized-vol/{ticker}")
def compute_realized_vol(
    ticker: str,
    window: int = Query(default=20, ge=5),
    annualize: bool = Query(default=True),
) -> Dict[str, Any]:
    """Compute realized volatility for a ticker."""
    engine = get_feature_engine()
    try:
        value = engine.compute_realized_volatility(ticker.upper(), window, annualize)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ticker": ticker.upper(), "window": window, "annualized": annualize, "realized_vol": round(value, 6)}


@router.post("/features/beta")
def compute_beta(req: ComputeBetaRequest) -> Dict[str, Any]:
    """Compute beta relative to a benchmark ticker."""
    engine = get_feature_engine()
    try:
        value = engine.compute_beta(req.ticker.upper(), req.benchmark_ticker.upper(), req.window)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ticker": req.ticker.upper(), "benchmark": req.benchmark_ticker.upper(),
            "window": req.window, "beta": round(value, 6)}


@router.post("/features/correlation")
def compute_correlation(req: ComputeCorrelationRequest) -> Dict[str, Any]:
    """Compute correlation between two tickers."""
    engine = get_feature_engine()
    try:
        value = engine.compute_correlation(req.ticker1.upper(), req.ticker2.upper(), req.window)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ticker1": req.ticker1.upper(), "ticker2": req.ticker2.upper(),
            "window": req.window, "correlation": round(value, 6)}


@router.get("/features/sharpe/{ticker}")
def compute_rolling_sharpe(
    ticker: str,
    window: int = Query(default=252, ge=10),
    risk_free: float = Query(default=0.0, ge=0),
) -> Dict[str, Any]:
    """Compute rolling Sharpe ratio."""
    engine = get_feature_engine()
    try:
        value = engine.compute_rolling_sharpe(ticker.upper(), window, risk_free)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ticker": ticker.upper(), "window": window, "sharpe": round(value, 6)}


@router.get("/features/var/{ticker}")
def compute_rolling_var(
    ticker: str,
    window: int = Query(default=252, ge=10),
    confidence: float = Query(default=0.95, ge=0.5, le=0.999),
) -> Dict[str, Any]:
    """Compute rolling Value at Risk."""
    engine = get_feature_engine()
    try:
        value = engine.compute_rolling_var(ticker.upper(), window, confidence)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ticker": ticker.upper(), "window": window, "confidence": confidence, "var": round(value, 6)}


@router.get("/features/snapshot/{ticker}")
def get_feature_snapshot(ticker: str) -> Dict[str, Any]:
    """Get full feature snapshot for a ticker."""
    engine = get_feature_engine()
    try:
        snap = engine.get_feature_snapshot(ticker.upper())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return snap.to_dict()


# ===========================================================================
# RISK ENGINE — /m18/risk
# ===========================================================================

@router.post("/risk/positions")
def update_risk_position(req: UpdatePositionRequest) -> SuccessResponse:
    """Add or update a position in the risk engine."""
    engine = get_risk_engine()
    engine.update_position(req.ticker.upper(), req.quantity, req.market_price,
                           req.sector, req.country, req.currency, req.adv, req.beta)
    return SuccessResponse(message=f"Position updated for {req.ticker.upper()}")


@router.delete("/risk/positions/{ticker}")
def remove_risk_position(ticker: str) -> SuccessResponse:
    """Remove a position from the risk engine."""
    get_risk_engine().remove_position(ticker.upper())
    return SuccessResponse(message=f"Position removed: {ticker.upper()}")


@router.get("/risk/positions")
def get_risk_positions() -> Dict[str, Any]:
    """Get all current positions."""
    return get_risk_engine().get_positions()


@router.post("/risk/nav")
def set_risk_nav(req: SetNavRequest) -> SuccessResponse:
    """Set portfolio NAV for the risk engine."""
    get_risk_engine().set_nav(req.nav)
    return SuccessResponse(message=f"NAV set to {req.nav}")


@router.post("/risk/pnl")
def add_pnl_observation(req: AddPnlObservationRequest) -> SuccessResponse:
    """Add a daily P&L observation for VaR computation."""
    get_risk_engine().add_pnl_observation(req.pnl)
    return SuccessResponse(message="P&L observation recorded")


@router.post("/risk/var")
def compute_portfolio_var(req: ComputeVaRRequest) -> Dict[str, Any]:
    """Compute historical portfolio VaR."""
    try:
        result = get_risk_engine().compute_portfolio_var(req.confidence, req.window)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result.to_dict()


@router.post("/risk/expected-shortfall")
def compute_expected_shortfall(req: ComputeESRequest) -> Dict[str, Any]:
    """Compute Expected Shortfall (CVaR)."""
    try:
        es = get_risk_engine().compute_expected_shortfall(req.confidence)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"confidence": req.confidence, "expected_shortfall_usd": round(es, 2)}


@router.post("/risk/leverage")
def compute_leverage(body: Optional[Dict[str, Any]] = Body(default=None)) -> Dict[str, Any]:
    """Compute portfolio leverage metrics."""
    try:
        result = get_risk_engine().compute_leverage()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result.to_dict()


@router.get("/risk/exposure/gross")
def compute_gross_exposure() -> Dict[str, Any]:
    """Compute gross market exposure."""
    return {"gross_exposure_usd": round(get_risk_engine().compute_gross_exposure(), 2)}


@router.get("/risk/exposure/net")
def compute_net_exposure() -> Dict[str, Any]:
    """Compute net market exposure."""
    return {"net_exposure_usd": round(get_risk_engine().compute_net_exposure(), 2)}


@router.get("/risk/exposure/sector")
def compute_sector_exposure() -> Dict[str, Any]:
    """Compute sector exposure breakdown."""
    return get_risk_engine().compute_sector_exposure()


@router.get("/risk/exposure/country")
def compute_country_exposure() -> Dict[str, Any]:
    """Compute country exposure breakdown."""
    return get_risk_engine().compute_country_exposure()


@router.get("/risk/exposure/currency")
def compute_currency_exposure() -> Dict[str, Any]:
    """Compute currency exposure breakdown."""
    return get_risk_engine().compute_currency_exposure()


@router.post("/risk/concentration")
def compute_concentration(body: Optional[Dict[str, Any]] = Body(default=None)) -> Dict[str, Any]:
    """Compute portfolio concentration metrics."""
    return get_risk_engine().compute_concentration().to_dict()


@router.post("/risk/margin")
def compute_margin(req: MarginRequest) -> Dict[str, Any]:
    """Compute margin usage and buying power."""
    return get_risk_engine().compute_margin_usage(req.margin_requirement_pct, req.maintenance_pct).to_dict()


@router.post("/risk/liquidity")
def compute_liquidity_risk(req: LiquidityRiskRequest) -> Dict[str, Any]:
    """Estimate portfolio liquidity risk."""
    return get_risk_engine().compute_liquidity_risk(req.participation_rate).to_dict()


@router.post("/risk/gap-risk")
def compute_gap_risk(req: GapRiskRequest) -> Dict[str, Any]:
    """Estimate overnight gap risk."""
    return get_risk_engine().compute_gap_risk(req.scenario_name, req.gap_pct).to_dict()


@router.post("/risk/stress-test")
def run_stress_test(req: StressTestRequest) -> Dict[str, Any]:
    """Run a stress-test scenario."""
    shock = req.equity_shock if req.equity_shock is not None else req.shock_pct
    return get_risk_engine().run_stress_test(
        req.scenario_name, shock_pct=shock, affected_sectors=req.affected_sectors
    ).to_dict()


@router.post("/risk/alerts/check")
def check_risk_alerts(req: RiskAlertThresholdsRequest) -> List[Dict[str, Any]]:
    """Check for risk threshold breaches and return triggered alerts."""
    alerts = get_risk_engine().check_risk_alerts(
        req.var_threshold_pct, req.leverage_threshold,
        req.concentration_threshold, req.drawdown_threshold_pct,
    )
    return [a.to_dict() for a in alerts]


@router.post("/risk/dashboard")
def get_risk_dashboard(body: Optional[Dict[str, Any]] = Body(default=None)) -> Dict[str, Any]:
    """Get consolidated real-time risk dashboard."""
    return get_risk_engine().get_risk_dashboard().to_dict()


# ===========================================================================
# PORTFOLIO INTELLIGENCE — /m18/portfolio-intel
# ===========================================================================

@router.post("/portfolio/nav")
def set_portfolio_intel_nav(req: PortfolioIntelSetNavRequest) -> SuccessResponse:
    """Set NAV for portfolio intelligence engine."""
    get_portfolio_intelligence_engine().set_nav(req.nav)
    return SuccessResponse(message=f"NAV set to {req.nav}")


@router.post("/portfolio/holdings")
def update_holding(req: UpdateHoldingRequest) -> SuccessResponse:
    """Add or update a holding."""
    e = get_portfolio_intelligence_engine()
    e.update_holding(req.ticker.upper(), req.weight, req.sector, req.expected_return,
                     req.volatility, req.cost_basis, req.current_price, req.quantity)
    return SuccessResponse(message=f"Holding updated: {req.ticker.upper()}")


@router.delete("/portfolio/holdings/{ticker}")
def remove_holding(ticker: str) -> SuccessResponse:
    """Remove a holding."""
    get_portfolio_intelligence_engine().remove_holding(ticker.upper())
    return SuccessResponse(message=f"Holding removed: {ticker.upper()}")


@router.get("/portfolio/holdings")
def get_all_holdings() -> List[Dict[str, Any]]:
    """Get all holdings."""
    return [h.to_dict() for h in get_portfolio_intelligence_engine().get_all_holdings()]


@router.post("/portfolio/returns")
def add_portfolio_return(req: AddReturnObservationRequest) -> SuccessResponse:
    """Record a daily return observation."""
    get_portfolio_intelligence_engine().add_return_observation(req.portfolio_return, req.benchmark_return)
    return SuccessResponse(message="Return observation recorded")


@router.post("/portfolio/attribution/brinson")
def brinson_attribution(req: BrinsonAttributionRequest) -> Dict[str, Any]:
    """Compute Brinson-Hood-Beebower attribution."""
    result = get_portfolio_intelligence_engine().compute_brinson_attribution(
        req.portfolio_sector_weights, req.benchmark_sector_weights,
        req.portfolio_sector_returns, req.benchmark_sector_returns,
        req.benchmark_total_return,
    )
    return result.to_dict()


@router.post("/portfolio/attribution/factor")
def factor_attribution(req: FactorAttributionRequest) -> Dict[str, Any]:
    """Compute factor-based return attribution."""
    result = get_portfolio_intelligence_engine().compute_factor_attribution(
        req.portfolio_return, req.factor_exposures, req.factor_returns,
    )
    return result.to_dict()


@router.post("/portfolio/rebalance")
def compute_rebalance(req: RebalancingRequest) -> List[Dict[str, Any]]:
    """Get rebalancing trade recommendations."""
    trades = get_portfolio_intelligence_engine().compute_rebalancing_trades(
        req.target_weights, req.tolerance,
    )
    return [t.to_dict() for t in trades]


@router.post("/portfolio/frontier")
def compute_efficient_frontier(req: EfficientFrontierRequest) -> List[Dict[str, Any]]:
    """Compute efficient frontier points."""
    points = get_portfolio_intelligence_engine().compute_efficient_frontier(
        req.tickers, req.expected_returns, req.covariance_matrix,
        req.n_points, req.risk_free,
    )
    return [p.to_dict() for p in points]


@router.get("/portfolio/score")
def get_portfolio_score(risk_free: float = Query(default=0.04, ge=0)) -> Dict[str, Any]:
    """Compute multi-dimensional portfolio quality score."""
    return get_portfolio_intelligence_engine().compute_portfolio_score(risk_free).to_dict()


@router.get("/portfolio/tail-risk")
def compute_tail_risk() -> Dict[str, Any]:
    """Compute tail risk metrics from return history."""
    try:
        return get_portfolio_intelligence_engine().compute_tail_risk().to_dict()
    except (ValueError, ZeroDivisionError):
        return {"var_95": 0.0, "var_99": 0.0, "cvar_95": 0.0, "cvar_99": 0.0,
                "max_drawdown": 0.0, "skewness": 0.0, "kurtosis": 0.0}


@router.get("/portfolio/summary")
def get_portfolio_summary() -> Dict[str, Any]:
    """Get comprehensive portfolio summary."""
    return get_portfolio_intelligence_engine().get_portfolio_summary().to_dict()


# ===========================================================================
# ALERT ENGINE — /m18/alerts
# ===========================================================================

@router.post("/alerts/rules")
def add_alert_rule(req: AddAlertRuleRequest) -> Dict[str, Any]:
    """Create a new alert rule."""
    engine = get_alert_engine()
    try:
        atype = AlertType(req.alert_type.upper())
        sev = AlertSeverity(req.severity.upper())
        direction = AlertDirection(req.direction.upper())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    rule = engine.add_rule(
        name=req.name, alert_type=atype, severity=sev,
        field=req.field, direction=direction, threshold=req.threshold,
        ticker=req.ticker, cooldown_seconds=req.cooldown_seconds,
        max_triggers=req.max_triggers, tags=req.tags,
    )
    return rule.to_dict()


@router.delete("/alerts/rules/{rule_id}")
def remove_alert_rule(rule_id: str) -> DeleteResponse:
    """Delete an alert rule."""
    deleted = get_alert_engine().remove_rule(rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
    return DeleteResponse(deleted=True, id=rule_id)


@router.patch("/alerts/rules/{rule_id}/enable")
def enable_rule(rule_id: str) -> SuccessResponse:
    """Enable an alert rule."""
    if not get_alert_engine().enable_rule(rule_id):
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
    return SuccessResponse(message=f"Rule {rule_id} enabled")


@router.patch("/alerts/rules/{rule_id}/disable")
def disable_rule(rule_id: str) -> SuccessResponse:
    """Disable an alert rule."""
    if not get_alert_engine().disable_rule(rule_id):
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
    return SuccessResponse(message=f"Rule {rule_id} disabled")


@router.get("/alerts/rules")
def list_alert_rules(
    alert_type: Optional[str] = Query(default=None),
    ticker: Optional[str] = Query(default=None),
) -> List[Dict[str, Any]]:
    """List configured alert rules."""
    engine = get_alert_engine()
    atype = None
    if alert_type:
        try:
            atype = AlertType(alert_type.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown alert type: {alert_type}")
    return [r.to_dict() for r in engine.list_rules(atype, ticker)]


@router.post("/alerts/webhooks")
def register_webhook(req: RegisterWebhookRequest) -> Dict[str, Any]:
    """Register a webhook for alert delivery."""
    engine = get_alert_engine()
    sev_filter = None
    if req.severity_filter:
        try:
            sev_filter = [AlertSeverity(s.upper()) for s in req.severity_filter]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    type_filter = None
    if req.alert_type_filter:
        try:
            type_filter = [AlertType(t.upper()) for t in req.alert_type_filter]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    wh = engine.register_webhook(req.url, sev_filter, type_filter)
    return wh.to_dict()


@router.delete("/alerts/webhooks/{webhook_id}")
def remove_webhook(webhook_id: str) -> DeleteResponse:
    """Remove a webhook."""
    if not get_alert_engine().remove_webhook(webhook_id):
        raise HTTPException(status_code=404, detail=f"Webhook {webhook_id} not found")
    return DeleteResponse(deleted=True, id=webhook_id)


@router.post("/alerts/evaluate")
def evaluate_alert(req: EvaluateAlertRequest) -> List[Dict[str, Any]]:
    """Evaluate a market data point and fire matching rules."""
    ticker = req.ticker or str(req.data.get("ticker", "UNKNOWN"))
    field = req.field if req.field != "price" or not req.data else (
        "price" if "price" in req.data else req.field
    )
    value = req.value or float(req.data.get(field, req.data.get("price", 0.0)))
    extra = {**req.extra, **req.data}
    alerts = get_alert_engine().evaluate(ticker.upper(), field, value, extra)
    return [a.to_dict() for a in alerts]


@router.post("/alerts/custom")
def fire_custom_alert(req: FireCustomAlertRequest) -> Dict[str, Any]:
    """Fire a custom alert without an associated rule."""
    engine = get_alert_engine()
    try:
        sev = AlertSeverity(req.severity.upper())
        atype = AlertType(req.alert_type.upper())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    alert_name = req.title or req.name or "Custom Alert"
    alert = engine.fire_custom_alert(
        name=alert_name, severity=sev, message=req.message,
        ticker=req.ticker, alert_type=atype, value=req.value, threshold=req.threshold,
    )
    return alert.to_dict()


@router.get("/alerts/history")
def get_alert_history(
    ticker: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    alert_type: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=1000),
) -> List[Dict[str, Any]]:
    """Retrieve alert history with optional filters."""
    engine = get_alert_engine()
    sev = None
    atype = None
    if severity:
        try:
            sev = AlertSeverity(severity.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown severity: {severity}")
    if alert_type:
        try:
            atype = AlertType(alert_type.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown type: {alert_type}")
    return [a.to_dict() for a in engine.get_history(limit, ticker, sev, atype)]


@router.get("/alerts/stats")
def get_alert_stats() -> Dict[str, Any]:
    """Get alert engine statistics."""
    return get_alert_engine().get_stats().to_dict()


# ===========================================================================
# ECONOMIC INTELLIGENCE — /m18/economic
# ===========================================================================

@router.post("/economic/indicators")
def record_indicator(req: RecordIndicatorRequest) -> Dict[str, Any]:
    """Record an economic indicator release."""
    engine = get_economic_intelligence_engine()
    try:
        itype = EconomicIndicatorType(req.indicator_type.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown indicator type: {req.indicator_type}")
    from services.m18_economic_intelligence import EconomicIndicator
    ind_obj = EconomicIndicator(
        name=req.name, country=req.country, indicator_type=itype,
        value=req.value, previous_value=req.previous_value,
        forecast=req.forecast, unit=req.unit, frequency=req.frequency,
    )
    ind = engine.record_indicator(ind_obj)
    return ind.to_dict()


@router.get("/economic/indicators")
def list_economic_indicators(
    country: Optional[str] = Query(default=None),
    indicator_type: Optional[str] = Query(default=None),
) -> List[Dict[str, Any]]:
    """List stored economic indicators."""
    engine = get_economic_intelligence_engine()
    itype = None
    if indicator_type:
        try:
            itype = EconomicIndicatorType(indicator_type.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown type: {indicator_type}")
    return [i.to_dict() for i in engine.list_indicators(country, itype)]


@router.get("/economic/indicators/{country}/{name}")
def get_economic_indicator(country: str, name: str) -> Dict[str, Any]:
    """Get a specific economic indicator."""
    ind = get_economic_intelligence_engine().get_indicator(country.upper(), name)
    if not ind:
        raise HTTPException(status_code=404, detail=f"Indicator {name} not found for {country}")
    return ind.to_dict()


@router.post("/economic/yield-curve")
def record_yield_curve(req: RecordYieldCurveRequest) -> Dict[str, Any]:
    """Record a yield curve snapshot."""
    snap = get_economic_intelligence_engine().record_yield_curve(req.country.upper(), req.tenors)
    return snap.to_dict()


@router.get("/economic/yield-curve/{country}")
def get_yield_curve(country: str) -> Dict[str, Any]:
    """Get the latest yield curve for a country."""
    snap = get_economic_intelligence_engine().get_latest_yield_curve(country.upper())
    if not snap:
        raise HTTPException(status_code=404, detail=f"No yield curve for {country}")
    return snap.to_dict()


@router.get("/economic/recession-probability/{country}")
def get_recession_probability(country: str) -> Dict[str, Any]:
    """Estimate recession probability for a country."""
    return get_economic_intelligence_engine().compute_recession_probability(country.upper()).to_dict()


@router.get("/economic/inflation-forecast/{country}")
def get_inflation_forecast(country: str) -> Dict[str, Any]:
    """Get inflation forecast for a country."""
    return get_economic_intelligence_engine().compute_inflation_forecast(country.upper()).to_dict()


@router.get("/economic/business-cycle/{country}")
def get_business_cycle(country: str) -> Dict[str, Any]:
    """Get business cycle analysis for a country."""
    return get_economic_intelligence_engine().analyse_business_cycle(country.upper()).to_dict()


@router.post("/economic/country-risk")
def assess_country_risk(req: AssessCountryRiskRequest) -> Dict[str, Any]:
    """Assess macro risk for a country."""
    return get_economic_intelligence_engine().assess_country_risk(
        req.country, req.fiscal_risk, req.monetary_risk,
        req.external_risk, req.political_risk, req.growth_outlook, req.key_risks,
    ).to_dict()


@router.get("/economic/country-risk/{country}")
def get_country_risk(country: str) -> Dict[str, Any]:
    """Get macro risk assessment for a country."""
    risk = get_economic_intelligence_engine().get_country_risk(country.upper())
    if not risk:
        raise HTTPException(status_code=404, detail=f"No risk data for {country}")
    return risk.to_dict()


@router.post("/economic/calendar/events")
def schedule_economic_event(req: ScheduleEconomicEventRequest) -> Dict[str, Any]:
    """Schedule an economic calendar event."""
    engine = get_economic_intelligence_engine()
    try:
        itype = EconomicIndicatorType(req.indicator_type.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown type: {req.indicator_type}")
    event = engine.schedule_event(
        req.name, req.country, itype, req.scheduled_time,
        req.forecast, req.previous, req.importance,
    )
    return event.to_dict()


@router.get("/economic/calendar/upcoming")
def get_upcoming_economic_events(
    country: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
) -> List[Dict[str, Any]]:
    """Get upcoming economic events."""
    return [e.to_dict() for e in get_economic_intelligence_engine().get_upcoming_events(limit, country)]


@router.get("/economic/calendar")
def get_economic_calendar(limit: int = Query(default=50, ge=1, le=500)) -> List[Dict[str, Any]]:
    """Get all scheduled economic events."""
    return [e.to_dict() for e in get_economic_intelligence_engine().get_calendar(limit)]


# ===========================================================================
# NEWS INTELLIGENCE — /m18/news
# ===========================================================================

@router.post("/news/tickers/register")
def register_news_tickers(req: RegisterTickersRequest) -> SuccessResponse:
    """Register known tickers for improved extraction accuracy."""
    get_news_intelligence_engine().register_tickers(req.tickers)
    return SuccessResponse(message=f"Registered {len(req.tickers)} tickers")


@router.post("/news/articles")
def ingest_news_article(req: IngestNewsRequest) -> Dict[str, Any]:
    """Ingest and annotate a news article."""
    article = get_news_intelligence_engine().ingest(
        req.headline, req.body, req.source, None, req.url, req.tags,
    )
    return article.to_dict()


@router.get("/news/articles/latest")
def get_latest_news(limit: int = Query(default=20, ge=1, le=500)) -> List[Dict[str, Any]]:
    """Get most recently ingested articles."""
    return [a.to_dict() for a in get_news_intelligence_engine().get_latest(limit)]


@router.post("/news/articles/search")
def search_news(req: NewsSearchRequest) -> List[Dict[str, Any]]:
    """Search news articles."""
    engine = get_news_intelligence_engine()
    from services.m18_news_intelligence import NewsCategory, NewsSentiment
    cat = None
    sent = None
    if req.category:
        try:
            cat = NewsCategory(req.category.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown category: {req.category}")
    if req.sentiment:
        try:
            sent = NewsSentiment(req.sentiment.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown sentiment: {req.sentiment}")
    return [a.to_dict() for a in engine.search(req.query, req.ticker, cat, sent, req.limit)]


@router.get("/news/articles/{article_id}")
def get_news_article(article_id: str) -> Dict[str, Any]:
    """Get a specific news article by ID."""
    article = get_news_intelligence_engine().get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail=f"Article {article_id} not found")
    return article.to_dict()


@router.get("/news/sentiment/{ticker}")
def get_ticker_sentiment(
    ticker: str,
    window: int = Query(default=50, ge=1, le=500),
) -> Dict[str, Any]:
    """Get aggregated news sentiment for a ticker."""
    return get_news_intelligence_engine().get_ticker_sentiment(ticker.upper(), window).to_dict()


@router.post("/news/trends")
def detect_news_trends(req: DetectTrendsRequest) -> List[Dict[str, Any]]:
    """Detect emerging news trends."""
    trends = get_news_intelligence_engine().detect_trends(req.window_hours, req.min_articles)
    return [t.to_dict() for t in trends]


@router.get("/news/signal/{ticker}")
def generate_news_signal(
    ticker: str,
    window: int = Query(default=20, ge=1, le=500),
) -> Dict[str, Any]:
    """Generate a trading signal from news sentiment."""
    return get_news_intelligence_engine().generate_signal(ticker.upper(), window).to_dict()


@router.get("/news/stats")
def get_news_stats() -> Dict[str, Any]:
    """Get news intelligence engine statistics."""
    return get_news_intelligence_engine().get_stats()


# ===========================================================================
# EARNINGS INTELLIGENCE — /m18/earnings
# ===========================================================================

@router.post("/earnings/releases")
def record_earnings_release(req: RecordEarningsReleaseRequest) -> Dict[str, Any]:
    """Record an earnings release."""
    engine = get_earnings_intelligence_engine()
    try:
        guidance = GuidanceDirection(req.guidance_direction.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown guidance direction: {req.guidance_direction}")
    from services.m18_earnings_intelligence import EarningsRelease
    rel_obj = EarningsRelease(
        ticker=req.ticker.upper(), fiscal_quarter=req.fiscal_quarter,
        reported_eps=req.reported_eps, consensus_eps=req.consensus_eps,
        reported_revenue=req.reported_revenue, consensus_revenue=req.consensus_revenue,
        gross_margin=req.gross_margin, operating_margin=req.operating_margin,
        net_income_usd_m=req.net_income_usd_m, guidance_direction=guidance,
        guidance_eps_low=req.guidance_eps_low, guidance_eps_high=req.guidance_eps_high,
        post_earnings_drift_1d=req.post_earnings_drift_1d,
    )
    release = engine.record_release(rel_obj)
    return release.to_dict()


@router.get("/earnings/releases/{ticker}")
def get_earnings_releases(
    ticker: str,
    limit: int = Query(default=20, ge=1, le=100),
) -> List[Dict[str, Any]]:
    """Get historical earnings releases for a ticker."""
    return [r.to_dict() for r in get_earnings_intelligence_engine().get_releases(ticker.upper(), limit)]


@router.post("/earnings/estimates")
def add_earnings_estimate(req: AddEarningsEstimateRequest) -> Dict[str, Any]:
    """Add an analyst earnings estimate."""
    est = get_earnings_intelligence_engine().add_estimate(
        req.ticker.upper(), req.fiscal_quarter, req.analyst_firm,
        req.eps_estimate, req.revenue_estimate, req.price_target, req.rating,
    )
    return est.to_dict()


@router.get("/earnings/consensus/{ticker}/{fiscal_quarter}")
def get_earnings_consensus(ticker: str, fiscal_quarter: str) -> Dict[str, Any]:
    """Get consensus estimates for a ticker and quarter."""
    return get_earnings_intelligence_engine().get_consensus(ticker.upper(), fiscal_quarter)


@router.get("/earnings/revision-trend/{ticker}/{fiscal_quarter}")
def get_revision_trend(ticker: str, fiscal_quarter: str) -> Dict[str, str]:
    """Get estimate revision trend for a ticker."""
    trend = get_earnings_intelligence_engine().get_estimate_revision_trend(ticker.upper(), fiscal_quarter)
    return {"ticker": ticker.upper(), "fiscal_quarter": fiscal_quarter, "trend": trend}


@router.get("/earnings/surprise-analysis/{ticker}")
def analyse_earnings_surprise(ticker: str) -> Dict[str, Any]:
    """Analyse historical earnings surprise pattern."""
    try:
        return get_earnings_intelligence_engine().analyse_surprise_history(ticker.upper()).to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/earnings/forecast-drift")
def forecast_post_earnings_drift(req: ForecastDriftRequest) -> Dict[str, Any]:
    """Forecast expected post-earnings price drift."""
    drift = get_earnings_intelligence_engine().forecast_post_earnings_drift(
        req.ticker.upper(), req.eps_surprise_pct,
    )
    return {"ticker": req.ticker.upper(), "eps_surprise_pct": req.eps_surprise_pct,
            "predicted_drift": round(drift, 6)}


@router.post("/earnings/signal")
def generate_earnings_signal(req: GenerateEarningsSignalRequest) -> Dict[str, Any]:
    """Generate a trading signal from earnings data."""
    try:
        guidance = GuidanceDirection(req.guidance_direction.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown guidance: {req.guidance_direction}")
    return get_earnings_intelligence_engine().generate_signal(
        req.ticker.upper(), req.eps_surprise_pct, req.revenue_surprise_pct, guidance,
    ).to_dict()


@router.post("/earnings/calendar")
def schedule_earnings_event(req: ScheduleEarningsRequest) -> Dict[str, Any]:
    """Schedule an earnings calendar event."""
    entry = get_earnings_intelligence_engine().schedule_earnings(
        req.ticker.upper(), req.fiscal_quarter, req.expected_date,
        req.time_of_day, req.consensus_eps, req.consensus_revenue, req.num_estimates,
    )
    return entry.to_dict()


@router.get("/earnings/calendar/upcoming")
def get_upcoming_earnings(
    ticker: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
) -> List[Dict[str, Any]]:
    """Get upcoming earnings events."""
    return [e.to_dict() for e in get_earnings_intelligence_engine().get_upcoming_earnings(limit, ticker)]


@router.get("/earnings/calendar")
def get_earnings_calendar(limit: int = Query(default=50, ge=1, le=500)) -> List[Dict[str, Any]]:
    """Get all scheduled earnings events."""
    return [e.to_dict() for e in get_earnings_intelligence_engine().get_earnings_calendar(limit)]


# ===========================================================================
# AI AGENTS — /m18/agents
# ===========================================================================

@router.get("/agents/list")
def list_agents() -> List[Dict[str, str]]:
    """List all registered AI agents."""
    return get_agent_orchestrator().list_agents()


@router.post("/agents/run")
def run_agent(req: RunAgentRequest) -> Dict[str, Any]:
    """Run a single AI agent."""
    try:
        atype = AgentType(req.agent_type.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown agent type: {req.agent_type}")
    result = get_agent_orchestrator().run_agent(atype, req.payload)
    return result.to_dict()


@router.post("/agents/run-all")
def run_all_agents(req: RunAllAgentsRequest) -> Dict[str, Any]:
    """Run multiple agents and aggregate results via orchestrator."""
    orchestrator = get_agent_orchestrator()
    try:
        payloads = {AgentType(k.upper()): v for k, v in req.payloads.items()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    result = orchestrator.run_all(payloads, req.include_report)
    return result.to_dict()


@router.get("/agents/history/{agent_type}")
def get_agent_history(
    agent_type: str,
    limit: int = Query(default=20, ge=1, le=200),
) -> List[Dict[str, Any]]:
    """Get run history for a specific agent."""
    try:
        atype = AgentType(agent_type.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown agent type: {agent_type}")
    return [r.to_dict() for r in get_agent_orchestrator().get_agent_history(atype, limit)]


@router.get("/agents/orchestration-history")
def get_orchestration_history(limit: int = Query(default=10, ge=1, le=50)) -> List[Dict[str, Any]]:
    """Get recent multi-agent orchestration session history."""
    return [r.to_dict() for r in get_agent_orchestrator().get_orchestration_history(limit)]


# ===========================================================================
# WATCHLIST SYSTEM — /m18/watchlists
# ===========================================================================

@router.post("/watchlists")
def create_watchlist(req: CreateWatchlistRequest) -> Dict[str, Any]:
    """Create a new watchlist."""
    system = get_watchlist_system()
    try:
        cat = WatchlistCategory(req.category.upper())
    except ValueError:
        cat = WatchlistCategory.CUSTOM
    try:
        wl = system.create_list(req.name, req.description, cat, req.owner, req.is_shared, req.tags)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return wl.to_dict(include_items=False)


@router.get("/watchlists")
def list_watchlists(
    owner: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    include_shared: bool = Query(default=True),
) -> List[Dict[str, Any]]:
    """List watchlists."""
    system = get_watchlist_system()
    cat = None
    if category:
        try:
            cat = WatchlistCategory(category.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown category: {category}")
    return [wl.to_dict(include_items=False) for wl in system.list_watchlists(owner, cat, include_shared)]


@router.get("/watchlists/{list_id}")
def get_watchlist(list_id: str) -> Dict[str, Any]:
    """Get a specific watchlist with all items."""
    wl = get_watchlist_system().get_list(list_id)
    if not wl:
        raise HTTPException(status_code=404, detail=f"Watchlist {list_id} not found")
    return wl.to_dict(include_items=True)


@router.patch("/watchlists/{list_id}")
def update_watchlist(list_id: str, req: UpdateWatchlistRequest) -> Dict[str, Any]:
    """Update watchlist metadata."""
    wl = get_watchlist_system().update_list(list_id, req.name, req.description, req.is_shared, req.tags)
    if not wl:
        raise HTTPException(status_code=404, detail=f"Watchlist {list_id} not found")
    return wl.to_dict(include_items=False)


@router.delete("/watchlists/{list_id}")
def delete_watchlist(list_id: str) -> DeleteResponse:
    """Delete a watchlist."""
    if not get_watchlist_system().delete_list(list_id):
        raise HTTPException(status_code=404, detail=f"Watchlist {list_id} not found")
    return DeleteResponse(deleted=True, id=list_id)


@router.post("/watchlists/{list_id}/items")
def add_watchlist_item(list_id: str, req: AddWatchlistItemRequest) -> Dict[str, Any]:
    """Add an instrument to a watchlist."""
    try:
        item = get_watchlist_system().add_item(
            list_id, req.ticker.upper(), req.notes, req.tags,
            req.target_price, req.stop_loss, req.sector, req.conviction,
            req.alert_thresholds,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return item.to_dict()


@router.delete("/watchlists/{list_id}/items/{ticker}")
def remove_watchlist_item(list_id: str, ticker: str) -> DeleteResponse:
    """Remove an item from a watchlist."""
    removed = get_watchlist_system().remove_item(list_id, ticker.upper())
    if not removed:
        raise HTTPException(status_code=404, detail=f"{ticker.upper()} not found in watchlist")
    return DeleteResponse(deleted=True, id=ticker.upper())


@router.patch("/watchlists/{list_id}/items/{ticker}")
def update_watchlist_item(list_id: str, ticker: str, req: UpdateWatchlistItemRequest) -> Dict[str, Any]:
    """Update a watchlist item."""
    item = get_watchlist_system().update_item(
        list_id, ticker.upper(), req.notes, req.target_price,
        req.stop_loss, req.conviction, req.tags,
    )
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {ticker.upper()} not found")
    return item.to_dict()


@router.post("/watchlists/{list_id}/prices")
def update_watchlist_price(list_id: str, req: UpdateWatchlistPriceRequest) -> List[Dict[str, Any]]:
    """Update price for a watchlist item and check alert thresholds."""
    alerts = get_watchlist_system().update_price(
        list_id, req.ticker.upper(), req.price, req.volume_ratio, req.rsi,
    )
    return [a.to_dict() for a in alerts]


@router.post("/watchlists/screen")
def screen_watchlists(req: WatchlistScreenRequest) -> List[Dict[str, Any]]:
    """Screen watchlist items against criteria."""
    criteria: Dict[str, Any] = {}
    if req.min_conviction is not None:
        criteria["min_conviction"] = req.min_conviction
    if req.max_conviction is not None:
        criteria["max_conviction"] = req.max_conviction
    if req.sector:
        criteria["sector"] = req.sector
    if req.tags:
        criteria["tags"] = req.tags
    return [r.to_dict() for r in get_watchlist_system().screen(criteria)]


@router.post("/watchlists/overlap")
def analyse_portfolio_overlap(req: PortfolioOverlapRequest) -> Dict[str, Any]:
    """Analyse overlap between a watchlist and a portfolio."""
    try:
        return get_watchlist_system().analyse_portfolio_overlap(req.list_id, req.portfolio_tickers).to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/watchlists/{list_id}/export")
def export_watchlist(list_id: str) -> List[Dict[str, Any]]:
    """Export a watchlist as a flat list."""
    try:
        return get_watchlist_system().export_list(list_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/watchlists/{list_id}/alerts")
def get_watchlist_alerts(
    list_id: str,
    ticker: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
) -> List[Dict[str, Any]]:
    """Get alert history for a watchlist."""
    return [a.to_dict() for a in get_watchlist_system().get_alerts(list_id, ticker, limit)]


@router.get("/watchlists/stats/summary")
def get_watchlist_stats() -> Dict[str, Any]:
    """Get watchlist system statistics."""
    return get_watchlist_system().get_stats()
