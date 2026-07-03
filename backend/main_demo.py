"""Demo entrypoint — memory-optimised for Render free tier (512 MB).

Differences from main.py:
  - Excludes scipy-heavy routers (analytics, portfolio_optimization, options)
  - Excludes heavy feature-engineering / events / knowledge-graph routers
  - Lazy-imports yfinance / pandas / numpy (only needed for /analyze endpoint)
  - Keeps all M18, M19, M20 routers and every route a LinkedIn visitor will hit
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import math
import re
import time
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from database import check_db_connection, engine
from models.base import Base
import models.m10  # noqa: F401

# ── Demo-critical routers ─────────────────────────────────────────────────────
# M18 / M19 / M20 — the pages shown in the LinkedIn demo
from routers.m18_realtime import router as m18_realtime_router
from routers.m19_research import router as m19_research_router
from routers.m20_research_closeout import router as m20_research_router

# Core platform
from routers.system import router as system_router
from routers.auth import router as auth_router
from routers.auth_enterprise import router as auth_enterprise_router
from routers.portfolio import router as portfolio_router
from routers.market import router as market_router
from routers.watchlist import router as watchlist_router
from routers.research import router as research_router
from routers.notifications import router as notifications_router
from routers.streaming import router as streaming_router
from routers.streaming_v2 import router as streaming_v2_router
from routers.streaming_v3 import router as streaming_v3_router
from routers.jobs import router as jobs_router
from routers.observability import router as observability_router

# Trading / execution (M17)
from routers.trading import router as m17_trading_router
from routers.orders import router as orders_router
from routers.executions import router as executions_router
from routers.paper import router as paper_router
from routers.trading_alerts import router as trading_alerts_router

# Middleware
from middleware.security_headers import SecurityHeadersMiddleware
from middleware.request_id import RequestIdMiddleware
from middleware.request_size import RequestSizeLimitMiddleware
from services.cache import cache

# ── EXCLUDED (scipy / networkx / heavy engines) ───────────────────────────────
# routers.analytics           → scipy stats/optimize/cluster + networkx  (~80 MB)
# routers.portfolio_optimization → scipy.optimize / scipy.linalg         (~64 MB)
# routers.options             → scipy.stats norm                          (~30 MB)
# routers.options_strategies  → options analytics
# routers.events              → 10 global engine instances                (~25 MB)
# routers.knowledge_graph     → networkx                                  (~15 MB)
# routers.knowledge_graph_v2  → networkx
# routers.market_data         → FeatureStore + DatasetBuilder             (~20 MB)
# routers.alternative_data    → heavy providers                           (~20 MB)
# routers.alt_intelligence    → alt data
# routers.documents           → NLP / document ingestion
# routers.ai_copilot          → LLM clients
# routers.ai_agents           → agent runner
# routers.market_intel        → market intelligence scoring
# routers.economic_calendar   → calendar engine
# routers.walk_forward        → walk-forward engine
# routers.execution_enhanced  → advanced execution algos
# routers.orchestrator        → workflow orchestration
# routers.screener            → screener engine
# routers.brokers             → broker integrations
# routers.reports             → report generation
# routers.providers           → data provider registry
# routers.multi_asset         → multi-asset cross-asset engine
# routers.research_workspace  → workspace
# routers.agents              → legacy agent router
# routers.oauth               → OAuth providers

# =============================================================================
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)

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

app.include_router(m20_research_router)
app.include_router(m19_research_router)
app.include_router(m18_realtime_router)
app.include_router(system_router)
app.include_router(auth_router)
app.include_router(auth_enterprise_router)
app.include_router(portfolio_router)
app.include_router(market_router)
app.include_router(watchlist_router)
app.include_router(research_router)
app.include_router(notifications_router)
app.include_router(streaming_router)
app.include_router(streaming_v2_router)
app.include_router(streaming_v3_router)
app.include_router(jobs_router)
app.include_router(observability_router)
app.include_router(m17_trading_router)
app.include_router(orders_router)
app.include_router(executions_router)
app.include_router(paper_router)
app.include_router(trading_alerts_router)


@app.on_event("startup")
def on_startup() -> None:
    import logging
    log = logging.getLogger("uvicorn.error")
    try:
        cache.connect(settings.redis_url)
        log.info("Cache backend: %s", cache.backend_name)
    except Exception as exc:
        log.warning("Cache init error: %s", exc)
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        log.warning("Could not create DB tables on startup: %s", exc)


# =============================================================================
# Lightweight stock analysis endpoint (yfinance lazy-loaded)
# =============================================================================
class AnalyzeReq(BaseModel):
    question: str


@app.get("/")
def root():
    return {"message": "QuantLab AI — demo instance"}


@app.get("/health")
def health():
    return {"ok": True, "db": check_db_connection()}


@app.post("/analyze")
def analyze(data: AnalyzeReq):
    # Lazy imports — keeps 42 MB off startup RSS
    import yfinance as yf            # noqa: PLC0415
    import pandas as pd              # noqa: PLC0415
    import numpy as np               # noqa: PLC0415

    def _prices(ticker: str, period: str = "6mo"):
        df = yf.download(ticker, period=period, interval="1d", progress=False)
        if df is None or df.empty:
            return None, None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        if df.empty:
            return None, None
        prices = df["Close"].astype(float).tolist()
        ohlc = [
            {"time": idx.strftime("%Y-%m-%d"), "open": float(r["Open"]),
             "high": float(r["High"]), "low": float(r["Low"]), "close": float(r["Close"])}
            for idx, r in df.iterrows()
        ]
        return prices, ohlc

    def _rsi(s: "pd.Series", n: int = 14):
        if len(s) < n + 1:
            return None
        d = s.diff(); g = d.clip(lower=0); l = -d.clip(upper=0)
        rs = g.rolling(n).mean() / l.rolling(n).mean()
        v = (100 - 100 / (1 + rs)).iloc[-1]
        return None if pd.isna(v) else round(float(v), 2)

    def _vol(s: "pd.Series"):
        r = s.pct_change().dropna()
        return round(float(r.std() * math.sqrt(252)), 3) if len(r) > 1 else None

    def _sr(s: "pd.Series", w: int = 20):
        t = s.tail(w)
        return round(float(t.min()), 2), round(float(t.max()), 2)

    def _pct(s: "pd.Series", d: int):
        if len(s) <= d:
            return None
        return round(float((s.iloc[-1] - s.iloc[-1 - d]) / s.iloc[-1 - d] * 100), 2)

    def _analyse(ticker: str):
        prices, ohlc = _prices(ticker)
        if prices is None:
            return None
        s = pd.Series(prices, dtype="float64")
        day = _pct(s, 1)
        sup, res = _sr(s)
        return {
            "ticker": ticker, "last": round(float(s.iloc[-1]), 2),
            "day_change_pct": day, "week_change_pct": _pct(s, 5),
            "month_change_pct": _pct(s, 21), "rsi14": _rsi(s),
            "vol_annual": _vol(s), "support": sup, "resistance": res,
            "momentum": "bullish" if (day or 0) > 1 else "bearish" if (day or 0) < -1 else "neutral",
            "ohlc": ohlc,
        }

    found = list(dict.fromkeys(re.findall(r"\b[A-Z]{2,5}\b", (data.question or "").upper())))[:2]
    if not found:
        return {"error": "Please provide a valid ticker."}

    if len(found) == 2:
        A, B = _analyse(found[0]), _analyse(found[1])
        if not A or not B:
            return {"error": "Invalid ticker(s)."}
        return {"left": A, "right": B, "request_id": str(uuid.uuid4()), "timestamp": int(time.time())}

    A = _analyse(found[0])
    if not A:
        return {"error": "Invalid ticker."}
    return {"data": A, "ohlc": A["ohlc"], "request_id": str(uuid.uuid4()), "timestamp": int(time.time())}
