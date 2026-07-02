import sys
from pathlib import Path

# Resolve import path — directory name contains a hyphen, blocking standard package import.
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import yfinance as yf
import pandas as pd
import numpy as np
import math
import uuid
import time
import re

from config import settings
from database import check_db_connection, engine
from models.base import Base
import models.m10  # noqa: F401 — register M10 tables in Base.metadata
from routers.portfolio import router as portfolio_router
from routers.market import router as market_router
from routers.watchlist import router as watchlist_router
from routers.research import router as research_router
from routers.analytics import router as analytics_router
from routers.orders import router as orders_router
from routers.executions import router as executions_router
from routers.paper import router as paper_router
from routers.brokers import router as brokers_router
from routers.trading_alerts import router as trading_alerts_router
from routers.streaming import router as streaming_router
from routers.research_workspace import router as research_workspace_router
from routers.documents import router as documents_router
from routers.ai_copilot import router as ai_copilot_router
from routers.alternative_data import router as alternative_data_router
from routers.news_intelligence import router as news_intelligence_router
from routers.reports import router as reports_router
from routers.screener import router as screener_router
from routers.agents import router as agents_router
from routers.options import router as options_router
from routers.orchestrator import router as orchestrator_router
from routers.market_intel import router as market_intel_router
from routers.knowledge_graph import router as knowledge_graph_router
from routers.economic_calendar import router as economic_calendar_router
from routers.auth import router as auth_router
from routers.auth_enterprise import router as auth_enterprise_router
from routers.notifications import router as notifications_router
from routers.system import router as system_router
from routers.providers import router as providers_router
from routers.options_strategies import router as options_strategies_router
from routers.walk_forward import router as walk_forward_router
from routers.knowledge_graph_v2 import router as knowledge_graph_v2_router
from routers.ai_agents import router as ai_agents_router
from routers.execution_enhanced import router as execution_enhanced_router
from routers.oauth import router as oauth_router
from routers.observability import router as observability_router
from routers.streaming_v2 import router as streaming_v2_router
from routers.streaming_v3 import router as streaming_v3_router
from routers.jobs import router as jobs_router
from routers.portfolio_optimization import router as portfolio_optimization_router
from routers.market_data import router as market_data_router
from routers.alt_intelligence import router as alt_intelligence_router
from routers.events import router as events_router
from routers.multi_asset import router as multi_asset_router
from routers.trading import router as m17_trading_router
from routers.m18_realtime import router as m18_realtime_router
from routers.m19_research import router as m19_research_router
from routers.m20_research_closeout import router as m20_research_router
from middleware.security_headers import SecurityHeadersMiddleware
from middleware.request_id import RequestIdMiddleware
from middleware.request_size import RequestSizeLimitMiddleware
from services.cache import cache

# =========================
# API SETUP
# =========================
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Autorise le front (Vite) + Swagger
app.add_middleware(RequestIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)

# CORS: use explicit origins list in production; fall back to localhost regex for dev.
_cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://localhost:\d+|http://127\.0\.0\.1:\d+",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Mount routers
app.include_router(portfolio_router)
app.include_router(market_router)
app.include_router(watchlist_router)
app.include_router(research_router)
app.include_router(analytics_router)
app.include_router(orders_router)
app.include_router(executions_router)
app.include_router(paper_router)
app.include_router(brokers_router)
app.include_router(trading_alerts_router)
app.include_router(streaming_router)
app.include_router(research_workspace_router)
app.include_router(documents_router)
app.include_router(ai_copilot_router)
app.include_router(alternative_data_router)
app.include_router(news_intelligence_router)
app.include_router(reports_router)
app.include_router(screener_router)
app.include_router(agents_router)
app.include_router(options_router)
app.include_router(orchestrator_router)
app.include_router(market_intel_router)
app.include_router(knowledge_graph_router)
app.include_router(economic_calendar_router)
app.include_router(auth_router)
app.include_router(auth_enterprise_router)
app.include_router(notifications_router)
app.include_router(system_router)
app.include_router(providers_router)
app.include_router(options_strategies_router)
app.include_router(walk_forward_router)
app.include_router(knowledge_graph_v2_router)
app.include_router(ai_agents_router)
app.include_router(execution_enhanced_router)
app.include_router(oauth_router)
app.include_router(observability_router)
app.include_router(streaming_v2_router)
app.include_router(streaming_v3_router)
app.include_router(jobs_router)
app.include_router(portfolio_optimization_router)
app.include_router(market_data_router)
app.include_router(alt_intelligence_router)
app.include_router(events_router)
app.include_router(multi_asset_router)
app.include_router(m17_trading_router)
app.include_router(m18_realtime_router)
app.include_router(m19_research_router)
app.include_router(m20_research_router)


@app.on_event("startup")
def on_startup() -> None:
    """Create all tables (idempotent), connect cache, and verify DB on startup."""
    import logging
    log = logging.getLogger("uvicorn.error")

    # Connect Redis (no-op if redis_url is empty — falls back to in-memory)
    try:
        cache.connect(settings.redis_url)
        log.info("Cache backend: %s", cache.backend_name)
    except Exception as exc:
        log.warning("Cache init error: %s", exc)

    # Create DB tables
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        log.warning("Could not create DB tables on startup: %s", exc)

# =========================
# MODELS
# =========================
class AnalyzeReq(BaseModel):
    question: str


# =========================
# DATA LAYER (Yahoo Finance)
# =========================
def get_price_series(ticker: str, period: str = "6mo"):
    """
    Retourne:
      - prices: list[float] (Close)
      - ohlc: list[dict] pour candlestick (time, open, high, low, close)
    """
    data = yf.download(ticker, period=period, interval="1d", progress=False)

    if data is None or data.empty:
        return None, None

    # yfinance ≥ 0.2 returns MultiIndex columns like ('Close', 'AAPL') — flatten to 'Close'
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)

    # Nettoyage
    data = data.dropna(subset=["Open", "High", "Low", "Close"])
    if data.empty:
        return None, None

    prices = data["Close"].astype(float).tolist()

    ohlc = []
    for index, row in data.iterrows():
        ohlc.append(
            {
                "time": index.strftime("%Y-%m-%d"),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
            }
        )

    return prices, ohlc


# =========================
# INDICATORS
# =========================
def compute_rsi(series: pd.Series, period: int = 14):
    if len(series) < period + 1:
        return None
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return None if pd.isna(val) else round(float(val), 2)


def compute_volatility(series: pd.Series):
    if len(series) < 2:
        return None
    rets = series.pct_change().dropna()
    if rets.empty:
        return None
    vol = float(rets.std() * math.sqrt(252))
    return round(vol, 3)


def compute_support_resistance(series: pd.Series, window: int = 20):
    if len(series) < window:
        return None, None
    tail = series.tail(window)
    support = round(float(tail.min()), 2)
    resistance = round(float(tail.max()), 2)
    return support, resistance


def pct_change(series: pd.Series, days: int):
    if len(series) <= days:
        return None
    return round(float((series.iloc[-1] - series.iloc[-1 - days]) / series.iloc[-1 - days] * 100), 2)


def trend_label(day_change_pct: float | None):
    if day_change_pct is None:
        return "neutral"
    if day_change_pct > 1:
        return "bullish"
    if day_change_pct < -1:
        return "bearish"
    return "neutral"


# =========================
# ANALYSIS ENGINE
# =========================
def analyze_ticker(ticker: str, period: str = "6mo"):
    prices, ohlc = get_price_series(ticker, period=period)
    if prices is None or ohlc is None:
        return None

    s = pd.Series(prices, dtype="float64")
    last_price = round(float(s.iloc[-1]), 2)

    day = pct_change(s, 1)
    week = pct_change(s, 5)
    month = pct_change(s, 21)

    rsi14 = compute_rsi(s, 14)
    vol_annual = compute_volatility(s)
    support, resistance = compute_support_resistance(s, 20)

    return {
        "ticker": ticker,
        "last": last_price,
        "day_change_pct": day,
        "week_change_pct": week,
        "month_change_pct": month,
        "rsi14": rsi14,
        "vol_annual": vol_annual,
        "support": support,
        "resistance": resistance,
        "momentum": trend_label(day),
        "ohlc": ohlc,
    }


# =========================
# PARSER
# =========================
def extract_tickers(text: str):
    # capture: AAPL, MSFT, NVDA... (2 à 5 lettres)
    found = re.findall(r"\b[A-Z]{2,5}\b", (text or "").upper())
    # unique en gardant l'ordre
    uniq = []
    for t in found:
        if t not in uniq:
            uniq.append(t)
    return uniq[:2]


# =========================
# ROUTES
# =========================
@app.get("/")
def root():
    return {"message": "AI Institutional Market Engine running (REAL DATA)"}


@app.get("/health")
def health():
    return {"ok": True, "db": check_db_connection()}


@app.post("/analyze")
def analyze(data: AnalyzeReq):
    tickers = extract_tickers(data.question)

    if len(tickers) == 0:
        return {"error": "Please provide a valid ticker (e.g. AAPL or 'AAPL vs MSFT')."}

    # DUEL MODE
    if len(tickers) == 2:
        A = analyze_ticker(tickers[0])
        B = analyze_ticker(tickers[1])
        if not A or not B:
            return {"error": "Invalid ticker(s)."}

        text = f"""
📊 DUEL ANALYSIS

{A['ticker']} | Last: ${A['last']} | RSI: {A['rsi14']} | Vol: {A['vol_annual']} | 1D%: {A['day_change_pct']}
{B['ticker']} | Last: ${B['last']} | RSI: {B['rsi14']} | Vol: {B['vol_annual']} | 1D%: {B['day_change_pct']}

Momentum: {A['ticker']} ({A['momentum']}) vs {B['ticker']} ({B['momentum']})
Support/Resistance:
- {A['ticker']}: {A['support']} / {A['resistance']}
- {B['ticker']}: {B['support']} / {B['resistance']}
""".strip()

        return {
            "result": text,
            "left": A,
            "right": B,
            "meta": {
                "engine": "AI Institutional Market Engine v3.0",
                "mode": "Duel Analysis",
            },
            "request_id": str(uuid.uuid4()),
            "timestamp": int(time.time()),
        }

    # SINGLE MODE
    A = analyze_ticker(tickers[0])
    if not A:
        return {"error": "Invalid ticker."}

    text = f"""
📈 MARKET OVERVIEW

Ticker: {A['ticker']}
Last: ${A['last']}
1D%: {A['day_change_pct']} | 1W%: {A['week_change_pct']} | 1M%: {A['month_change_pct']}
RSI(14): {A['rsi14']} | Volatility(ann.): {A['vol_annual']}
Support: {A['support']} | Resistance: {A['resistance']}
Momentum: {A['momentum']}
""".strip()

    return {
        "result": text,
        "data": A,
        "ohlc": A["ohlc"],  # <- IMPORTANT pour les candlesticks côté frontend
        "meta": {
            "engine": "AI Institutional Market Engine v3.0",
            "mode": "Market Overview",
        },
        "request_id": str(uuid.uuid4()),
        "timestamp": int(time.time()),
    }