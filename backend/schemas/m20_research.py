"""M20 Pydantic v2 schemas — Regime Detection, Correlation/Covariance, Strategy Comparison."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------

class OHLCVBar(BaseModel):
    """A single OHLCV price bar."""

    date: str = Field(..., description="ISO date string (YYYY-MM-DD)")
    open: float = Field(..., gt=0, description="Open price")
    high: float = Field(..., gt=0, description="High price")
    low: float = Field(..., gt=0, description="Low price")
    close: float = Field(..., gt=0, description="Close price")
    volume: float = Field(default=0.0, ge=0, description="Volume")

    @model_validator(mode="after")
    def high_gte_low(self) -> "OHLCVBar":
        """Ensure high >= low."""
        if self.high < self.low:
            raise ValueError("high must be >= low")
        return self


# ---------------------------------------------------------------------------
# Regime Detection schemas
# ---------------------------------------------------------------------------

class RegimeDetectRequest(BaseModel):
    """Request body for POST /quant/m20/regime/detect."""

    ticker: str = Field(..., min_length=1, description="Instrument symbol")
    bars: List[OHLCVBar] = Field(..., min_length=2, description="Price bars (min 2)")
    fast_window: int = Field(default=50, ge=5, description="Fast SMA window")
    slow_window: int = Field(default=200, ge=10, description="Slow SMA window")
    vol_window: int = Field(default=20, ge=5, description="Recent vol window")
    vol_lookback: int = Field(default=252, ge=20, description="Long-term vol window")
    vol_high_threshold: float = Field(default=1.5, gt=1.0, description="Vol-ratio HIGH_VOL threshold")
    vol_low_threshold: float = Field(default=0.5, gt=0.0, lt=1.0, description="Vol-ratio LOW_VOL threshold")
    momentum_threshold: float = Field(default=0.02, gt=0.0, description="Absolute momentum BULL/BEAR threshold")


class RegimeDetectFromReturnsRequest(BaseModel):
    """Request body for POST /quant/m20/regime/detect-from-returns."""

    ticker: str = Field(..., min_length=1)
    daily_returns: List[float] = Field(..., min_length=2, description="Fractional daily returns")
    start_price: float = Field(default=100.0, gt=0)
    fast_window: int = Field(default=50, ge=5)
    slow_window: int = Field(default=200, ge=10)
    vol_window: int = Field(default=20, ge=5)
    vol_lookback: int = Field(default=252, ge=20)
    vol_high_threshold: float = Field(default=1.5, gt=1.0)
    vol_low_threshold: float = Field(default=0.5, gt=0.0, lt=1.0)
    momentum_threshold: float = Field(default=0.02, gt=0.0)


class RegimeCompareRequest(BaseModel):
    """Request body for POST /quant/m20/regime/compare."""

    tickers: List[str] = Field(..., min_length=1, description="Tickers to compare")


# ---------------------------------------------------------------------------
# Correlation / Covariance schemas
# ---------------------------------------------------------------------------

class ReturnSeriesEntry(BaseModel):
    """Single ticker return series for ingestion."""

    ticker: str = Field(..., min_length=1)
    returns: Dict[str, float] = Field(..., description="ISO date → fractional daily return")

    @field_validator("returns")
    @classmethod
    def non_empty_returns(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Require at least 2 observations."""
        if len(v) < 2:
            raise ValueError("returns must have at least 2 observations")
        return v


class AddReturnsRequest(BaseModel):
    """Request body for POST /quant/m20/correlation/add-returns."""

    ticker: str = Field(..., min_length=1)
    returns: Dict[str, float] = Field(..., description="ISO date → fractional return")


class AddReturnsBatchRequest(BaseModel):
    """Request body for POST /quant/m20/correlation/add-returns-batch."""

    entries: List[ReturnSeriesEntry] = Field(..., min_length=1)


class CorrelationMatrixRequest(BaseModel):
    """Request body for POST /quant/m20/correlation/matrix."""

    tickers: List[str] = Field(..., min_length=2, description="Tickers to include (min 2)")


class CovarianceMatrixRequest(BaseModel):
    """Request body for POST /quant/m20/covariance/matrix."""

    tickers: List[str] = Field(..., min_length=2)
    annualize: bool = Field(default=True, description="Multiply by 252 to annualise")


class RollingCorrelationRequest(BaseModel):
    """Request body for POST /quant/m20/correlation/rolling."""

    ticker_a: str = Field(..., min_length=1)
    ticker_b: str = Field(..., min_length=1)
    window: int = Field(default=60, ge=5, description="Rolling window in bars")


class ClusterRequest(BaseModel):
    """Request body for POST /quant/m20/correlation/clusters."""

    tickers: List[str] = Field(..., min_length=2)
    threshold: float = Field(default=0.70, ge=0.0, le=1.0, description="Absolute correlation cluster threshold")


class PairwiseCorrelationRequest(BaseModel):
    """Request body for POST /quant/m20/correlation/pairwise."""

    ticker_a: str = Field(..., min_length=1)
    ticker_b: str = Field(..., min_length=1)


class MostCorrelatedRequest(BaseModel):
    """Request body for POST /quant/m20/correlation/most-correlated."""

    tickers: List[str] = Field(..., min_length=2)


class LeastCorrelatedRequest(BaseModel):
    """Request body for POST /quant/m20/correlation/least-correlated."""

    tickers: List[str] = Field(..., min_length=2)


# ---------------------------------------------------------------------------
# Strategy Comparison schemas
# ---------------------------------------------------------------------------

class RegisterResultRequest(BaseModel):
    """Request body for POST /quant/m20/comparison/register — registers a pre-computed result by backtest_id."""

    strategy_name: str = Field(..., min_length=1)
    backtest_id: str = Field(..., description="backtest_id from a prior M19 backtest run")


class RunAndRegisterRequest(BaseModel):
    """Request body for POST /quant/m20/comparison/run-and-register."""

    strategy_name: str = Field(..., min_length=1)
    ticker: str = Field(..., min_length=1)
    price_data: Dict[str, List[Dict[str, Any]]] = Field(
        ..., description="Dict of ticker → list of OHLCV bar dicts"
    )
    signals: Dict[str, str] = Field(..., description="Dict of date → signal (LONG/SHORT/FLAT)")
    initial_capital: float = Field(default=100_000.0, gt=0)
    commission_rate: float = Field(default=0.001, ge=0.0, le=0.05)


class CompareRequest(BaseModel):
    """Request body for POST /quant/m20/comparison/compare."""

    strategy_ids: List[str] = Field(..., min_length=2, description="Strategy UUIDs to compare")
    primary_metric: str = Field(
        default="sharpe_ratio",
        description="Metric for primary ranking",
    )
    include_correlation: bool = Field(default=True)


class BestByMetricRequest(BaseModel):
    """Request body for POST /quant/m20/comparison/best."""

    strategy_ids: List[str] = Field(..., min_length=1)
    metric: str = Field(default="sharpe_ratio")


class RankByMetricRequest(BaseModel):
    """Request body for POST /quant/m20/comparison/rank."""

    strategy_ids: List[str] = Field(..., min_length=1)
    metric: str = Field(default="sharpe_ratio")


class HeadToHeadRequest(BaseModel):
    """Request body for POST /quant/m20/comparison/head-to-head."""

    strategy_id_a: str = Field(..., description="First strategy UUID")
    strategy_id_b: str = Field(..., description="Second strategy UUID")
