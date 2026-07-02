"""Pydantic v2 schemas for M3 — Quantitative Research Engine."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------

AVAILABLE_STRATEGIES = {
    # ---- Original four (M3) ----
    "sma_crossover": {
        "display_name": "SMA Crossover",
        "description": "Buy when the fast SMA crosses above the slow SMA; sell on the reverse.",
        "params": {
            "fast_period": {"type": "int", "default": 10, "min": 2, "max": 200},
            "slow_period": {"type": "int", "default": 30, "min": 5, "max": 500},
        },
    },
    "rsi_mean_reversion": {
        "display_name": "RSI Mean Reversion",
        "description": "Buy when RSI crosses above the oversold level; sell when it crosses above overbought.",
        "params": {
            "period": {"type": "int", "default": 14, "min": 2, "max": 100},
            "oversold": {"type": "float", "default": 30, "min": 1, "max": 49},
            "overbought": {"type": "float", "default": 70, "min": 51, "max": 99},
        },
    },
    "macd_momentum": {
        "display_name": "MACD Momentum",
        "description": "Buy when the MACD line crosses above the signal line; sell on the reverse.",
        "params": {
            "fast": {"type": "int", "default": 12, "min": 2, "max": 100},
            "slow": {"type": "int", "default": 26, "min": 5, "max": 200},
            "signal": {"type": "int", "default": 9, "min": 1, "max": 50},
        },
    },
    "bollinger_band": {
        "display_name": "Bollinger Band Mean Reversion",
        "description": "Buy when price touches the lower band; sell when it reaches the middle band.",
        "params": {
            "period": {"type": "int", "default": 20, "min": 5, "max": 200},
            "std_dev": {"type": "float", "default": 2.0, "min": 0.5, "max": 4.0},
        },
    },
    # ---- M11 Phase 2 — seven new strategies ----
    "buy_and_hold": {
        "display_name": "Buy and Hold",
        "description": "Buy on the first bar and hold to the end. Benchmark for active strategies.",
        "params": {},
    },
    "dual_ma": {
        "display_name": "Dual Moving Average",
        "description": "Buy when the fast EMA crosses above the slow SMA; sell on the reverse.",
        "params": {
            "fast_period": {"type": "int", "default": 10, "min": 2, "max": 200},
            "slow_period": {"type": "int", "default": 30, "min": 5, "max": 500},
        },
    },
    "momentum": {
        "display_name": "Momentum (ROC)",
        "description": "Buy when Rate-of-Change rises above the threshold; sell when it falls below the negative threshold.",
        "params": {
            "period": {"type": "int", "default": 20, "min": 2, "max": 252},
            "threshold": {"type": "float", "default": 0.0, "min": -50.0, "max": 50.0},
        },
    },
    "mean_reversion": {
        "display_name": "Mean Reversion (Z-Score)",
        "description": "Buy when price z-score falls below -z_entry (oversold); sell when it reverts above z_exit.",
        "params": {
            "lookback": {"type": "int", "default": 20, "min": 5, "max": 252},
            "z_entry": {"type": "float", "default": 1.5, "min": 0.5, "max": 5.0},
            "z_exit": {"type": "float", "default": 0.0, "min": -2.0, "max": 2.0},
        },
    },
    "channel_breakout": {
        "display_name": "Channel Breakout (Donchian)",
        "description": "Buy when close exceeds the highest close of the previous N bars; sell on new lows.",
        "params": {
            "period": {"type": "int", "default": 20, "min": 5, "max": 252},
        },
    },
    "pairs_trading": {
        "display_name": "Pairs Trading (Z-Score)",
        "description": "Buy when the spread z-score drops below -z_entry; sell when it reverts inside z_exit.",
        "params": {
            "lookback": {"type": "int", "default": 60, "min": 10, "max": 504},
            "z_entry": {"type": "float", "default": 2.0, "min": 0.5, "max": 5.0},
            "z_exit": {"type": "float", "default": 0.5, "min": 0.0, "max": 3.0},
        },
    },
    "volatility_breakout": {
        "display_name": "Volatility Breakout (ATR)",
        "description": "Buy when close exceeds open by multiplier×ATR; sell when close falls below open by multiplier×ATR.",
        "params": {
            "atr_period": {"type": "int", "default": 14, "min": 2, "max": 100},
            "multiplier": {"type": "float", "default": 1.5, "min": 0.1, "max": 10.0},
        },
    },
}


# ---------------------------------------------------------------------------
# Indicator request / response
# ---------------------------------------------------------------------------


class IndicatorSpec(BaseModel):
    """Single indicator instance with its parameters."""

    period: Optional[int] = None
    fast: Optional[int] = None
    slow: Optional[int] = None
    signal: Optional[int] = None
    std_dev: Optional[float] = None
    k_period: Optional[int] = None
    d_period: Optional[int] = None


class IndicatorRequest(BaseModel):
    """POST /research/indicators — request body."""

    ticker: str = Field(..., min_length=1, max_length=10)
    period: str = Field(default="6mo")
    interval: str = Field(default="1d")
    # Map of indicator type → list of param sets (allows multiple instances, e.g. SMA-20 and SMA-50)
    indicators: Dict[str, List[IndicatorSpec]] = Field(default_factory=dict)

    @field_validator("ticker")
    @classmethod
    def upper_ticker(cls, v: str) -> str:
        return v.upper().strip()


class OHLCVBar(BaseModel):
    """Single OHLCV candlestick bar."""

    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class IndicatorResponse(BaseModel):
    """POST /research/indicators — response body."""

    ticker: str
    period: str
    interval: str
    ohlcv: List[OHLCVBar]
    # Each key maps to either a list of floats (single-line) or a dict of named lists (multi-line)
    indicators: Dict[str, Union[List[Optional[float]], Dict[str, List[Optional[float]]]]]


# ---------------------------------------------------------------------------
# Strategy schemas
# ---------------------------------------------------------------------------


class StrategyCreate(BaseModel):
    """POST /research/strategies — save a named strategy configuration."""

    name: str = Field(..., min_length=1, max_length=100)
    strategy_type: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("strategy_type")
    @classmethod
    def validate_strategy_type(cls, v: str) -> str:
        if v not in AVAILABLE_STRATEGIES:
            raise ValueError(
                f"Unknown strategy_type '{v}'. Valid options: {list(AVAILABLE_STRATEGIES)}"
            )
        return v


class StrategyRead(BaseModel):
    """Stored strategy response."""

    id: uuid.UUID
    name: str
    strategy_type: str
    description: Optional[str]
    params: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AvailableStrategyParam(BaseModel):
    type: str
    default: Any
    min: Optional[float] = None
    max: Optional[float] = None


class AvailableStrategy(BaseModel):
    key: str
    display_name: str
    description: str
    params: Dict[str, Dict[str, Any]]


# ---------------------------------------------------------------------------
# Backtest request / response
# ---------------------------------------------------------------------------


class RunBacktestRequest(BaseModel):
    """POST /research/backtest/run — run a backtest."""

    ticker: str = Field(..., min_length=1, max_length=10)
    benchmark: str = Field(default="SPY", max_length=10)
    start_date: date
    end_date: date
    initial_capital: float = Field(default=100_000, gt=0)
    commission_pct: float = Field(default=0.001, ge=0, le=0.05)
    slippage_pct: float = Field(default=0.001, ge=0, le=0.05)
    position_size_pct: float = Field(default=1.0, gt=0, le=1.0)
    strategy_name: str = Field(..., min_length=1, max_length=50)
    strategy_params: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("ticker", "benchmark")
    @classmethod
    def upper(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("strategy_name")
    @classmethod
    def validate_strategy_name(cls, v: str) -> str:
        if v not in AVAILABLE_STRATEGIES:
            raise ValueError(
                f"Unknown strategy '{v}'. Valid options: {list(AVAILABLE_STRATEGIES)}"
            )
        return v

    @model_validator(mode="after")
    def date_range_valid(self) -> "RunBacktestRequest":
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        delta = (self.end_date - self.start_date).days
        if delta < 60:
            raise ValueError("Backtest window must be at least 60 days")
        return self


class TradeRecord(BaseModel):
    """Single completed round-trip trade."""

    entry_date: str
    exit_date: str
    direction: str
    entry_price: float
    exit_price: float
    shares: float
    gross_pnl: float
    net_pnl: float
    pnl_pct: float
    duration_days: int
    commissions_paid: float


class EquityPoint(BaseModel):
    """Daily equity snapshot for the equity curve."""

    date: str
    equity: float
    cash: float
    position_value: float
    drawdown_pct: float


class BacktestMetrics(BaseModel):
    """Full set of performance metrics for a completed backtest."""

    # Return
    total_return_pct: float
    annual_return_pct: float
    benchmark_return_pct: float
    alpha: float
    beta: float

    # Risk
    volatility_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown_pct: float
    max_drawdown_duration_days: int

    # Trade stats
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    avg_win_pct: float
    avg_loss_pct: float
    profit_factor: float
    avg_trade_duration_days: float
    best_trade_pct: float
    worst_trade_pct: float

    # Exposure
    time_in_market_pct: float
    final_equity: float


class BacktestSummary(BaseModel):
    """Lightweight list entry — no equity curve or trades."""

    id: uuid.UUID
    ticker: str
    benchmark: str
    start_date: date
    end_date: date
    initial_capital: float
    strategy_name: str
    strategy_params: Dict[str, Any]
    status: str
    total_return_pct: Optional[float]
    annual_return_pct: Optional[float]
    sharpe_ratio: Optional[float]
    max_drawdown_pct: Optional[float]
    total_trades: Optional[int]
    win_rate_pct: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}


class BacktestResult(BaseModel):
    """Full backtest result including equity curve, trades, and metrics."""

    id: uuid.UUID
    ticker: str
    benchmark: str
    start_date: date
    end_date: date
    initial_capital: float
    commission_pct: float
    slippage_pct: float
    position_size_pct: float
    strategy_name: str
    strategy_params: Dict[str, Any]
    status: str
    error_message: Optional[str]
    metrics: Optional[BacktestMetrics]
    equity_curve: List[EquityPoint]
    trades: List[TradeRecord]
    # {year: {month: pct_return}} — for the monthly heatmap
    monthly_returns: Dict[str, Dict[str, float]]
    created_at: datetime

    model_config = {"from_attributes": True}
