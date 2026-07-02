"""M20 Quant Research Platform Closeout — REST API router.

Provides endpoints for:
- Regime Detection (/quant/m20/regime/*)
- Correlation & Covariance (/quant/m20/correlation/*, /quant/m20/covariance/*)
- Strategy Comparison (/quant/m20/comparison/*)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from schemas.m20_research import (
    AddReturnsBatchRequest,
    AddReturnsRequest,
    BestByMetricRequest,
    ClusterRequest,
    CompareRequest,
    CovarianceMatrixRequest,
    CorrelationMatrixRequest,
    HeadToHeadRequest,
    LeastCorrelatedRequest,
    MostCorrelatedRequest,
    PairwiseCorrelationRequest,
    RankByMetricRequest,
    RegimeCompareRequest,
    RegimeDetectFromReturnsRequest,
    RegimeDetectRequest,
    RegisterResultRequest,
    RollingCorrelationRequest,
    RunAndRegisterRequest,
)
from services.m19_backtest_engine import BacktestEngine, PriceBar, SignalType
from services.m20_correlation_covariance import CorrelationCovarianceEngine
from services.m20_regime_detection import RegimeDetectionEngine
from services.m20_strategy_comparison import StrategyComparisonEngine

router = APIRouter(prefix="/quant/m20", tags=["M20 Quant Closeout"])

# ---------------------------------------------------------------------------
# Service singletons
# ---------------------------------------------------------------------------
_regime_engine = RegimeDetectionEngine()
_corr_engine = CorrelationCovarianceEngine()
_backtest_engine_m20 = BacktestEngine()
_comparison_engine = StrategyComparisonEngine(backtest_engine=_backtest_engine_m20)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bars_to_native(bars: list) -> list:
    """Convert OHLCVBar Pydantic models to PriceBar dataclass instances."""
    return [
        PriceBar(
            date=b.date,
            open=b.open,
            high=b.high,
            low=b.low,
            close=b.close,
            volume=b.volume,
        )
        for b in bars
    ]


def _dict_to_price_bar(d: Dict[str, Any]) -> PriceBar:
    """Convert a raw dict to a PriceBar dataclass."""
    return PriceBar(
        date=d["date"],
        open=float(d.get("open", d["close"])),
        high=float(d.get("high", d["close"])),
        low=float(d.get("low", d["close"])),
        close=float(d["close"]),
        volume=float(d.get("volume", 0.0)),
    )


# ---------------------------------------------------------------------------
# Regime Detection endpoints
# ---------------------------------------------------------------------------

@router.post("/regime/detect", response_model=Dict[str, Any], tags=["Regime"])
def regime_detect(body: RegimeDetectRequest) -> Dict[str, Any]:
    """Detect market regime from OHLCV price bars.

    Args:
        body: RegimeDetectRequest with ticker and bars.

    Returns:
        RegimeResult serialized as dict.
    """
    engine = RegimeDetectionEngine(
        fast_window=body.fast_window,
        slow_window=body.slow_window,
        vol_window=body.vol_window,
        vol_lookback=body.vol_lookback,
        vol_high_threshold=body.vol_high_threshold,
        vol_low_threshold=body.vol_low_threshold,
        momentum_threshold=body.momentum_threshold,
    )
    native_bars = _bars_to_native(body.bars)
    result = engine.detect(body.ticker, native_bars)
    _regime_engine._results[body.ticker] = result
    return result.to_dict()


@router.post("/regime/detect-from-returns", response_model=Dict[str, Any], tags=["Regime"])
def regime_detect_from_returns(body: RegimeDetectFromReturnsRequest) -> Dict[str, Any]:
    """Detect market regime from a daily-return series.

    Args:
        body: RegimeDetectFromReturnsRequest.

    Returns:
        RegimeResult serialized as dict.
    """
    engine = RegimeDetectionEngine(
        fast_window=body.fast_window,
        slow_window=body.slow_window,
        vol_window=body.vol_window,
        vol_lookback=body.vol_lookback,
        vol_high_threshold=body.vol_high_threshold,
        vol_low_threshold=body.vol_low_threshold,
        momentum_threshold=body.momentum_threshold,
    )
    result = engine.detect_from_returns(body.ticker, body.daily_returns, body.start_price)
    _regime_engine._results[body.ticker] = result
    return result.to_dict()


@router.get("/regime/result/{ticker}", response_model=Dict[str, Any], tags=["Regime"])
def regime_get_result(ticker: str) -> Dict[str, Any]:
    """Retrieve cached regime result for a ticker.

    Args:
        ticker: Instrument symbol.

    Returns:
        Cached RegimeResult as dict.

    Raises:
        HTTPException 404: If ticker has no cached result.
    """
    result = _regime_engine.get_result(ticker)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No regime result for ticker '{ticker}'")
    return result.to_dict()


@router.get("/regime/current/{ticker}", response_model=Dict[str, Any], tags=["Regime"])
def regime_get_current(ticker: str) -> Dict[str, Any]:
    """Return the most recent regime point for a ticker.

    Args:
        ticker: Instrument symbol.

    Returns:
        Most recent RegimePoint as dict.

    Raises:
        HTTPException 404: If ticker is unknown.
    """
    point = _regime_engine.get_current_regime(ticker)
    if point is None:
        raise HTTPException(status_code=404, detail=f"No regime data for ticker '{ticker}'")
    return point.to_dict()


@router.get("/regime/history/{ticker}", response_model=List[Dict[str, Any]], tags=["Regime"])
def regime_get_history(ticker: str) -> List[Dict[str, Any]]:
    """Return full regime history for a ticker.

    Args:
        ticker: Instrument symbol.

    Returns:
        List of RegimePoint dicts.
    """
    history = _regime_engine.get_history(ticker)
    return [p.to_dict() for p in history]


@router.get("/regime/tickers", response_model=List[str], tags=["Regime"])
def regime_list_tickers() -> List[str]:
    """List all tickers with cached regime results.

    Returns:
        Sorted list of ticker symbols.
    """
    return _regime_engine.list_tickers()


@router.get("/regime/summary", response_model=Dict[str, Any], tags=["Regime"])
def regime_summary() -> Dict[str, Any]:
    """Summarise current regimes across all cached tickers.

    Returns:
        RegimeSummary as dict.
    """
    return _regime_engine.get_summary().to_dict()


@router.post("/regime/compare", response_model=Dict[str, Any], tags=["Regime"])
def regime_compare(body: RegimeCompareRequest) -> Dict[str, Any]:
    """Compare current regimes across a list of tickers.

    Args:
        body: RegimeCompareRequest with ticker list.

    Returns:
        Dict of ticker → regime info.
    """
    return _regime_engine.compare_regimes(body.tickers)


@router.delete("/regime/reset", response_model=Dict[str, str], tags=["Regime"])
def regime_reset() -> Dict[str, str]:
    """Clear all cached regime detection results.

    Returns:
        Confirmation message.
    """
    _regime_engine.reset()
    return {"status": "ok", "message": "Regime detection cache cleared"}


# ---------------------------------------------------------------------------
# Correlation endpoints
# ---------------------------------------------------------------------------

@router.post("/correlation/add-returns", response_model=Dict[str, str], tags=["Correlation"])
def correlation_add_returns(body: AddReturnsRequest) -> Dict[str, str]:
    """Store or replace a return series for a ticker.

    Args:
        body: AddReturnsRequest with ticker and returns dict.

    Returns:
        Confirmation with ticker and observation count.
    """
    _corr_engine.add_returns(body.ticker, body.returns)
    return {"status": "ok", "ticker": body.ticker, "observations": str(len(body.returns))}


@router.post("/correlation/add-returns-batch", response_model=Dict[str, Any], tags=["Correlation"])
def correlation_add_returns_batch(body: AddReturnsBatchRequest) -> Dict[str, Any]:
    """Store return series for multiple tickers at once.

    Args:
        body: AddReturnsBatchRequest with list of ticker/returns pairs.

    Returns:
        Summary of ingested tickers.
    """
    ingested: List[str] = []
    for entry in body.entries:
        _corr_engine.add_returns(entry.ticker, entry.returns)
        ingested.append(entry.ticker)
    return {"status": "ok", "ingested": ingested, "count": len(ingested)}


@router.post("/correlation/matrix", response_model=Dict[str, Any], tags=["Correlation"])
def correlation_matrix(body: CorrelationMatrixRequest) -> Dict[str, Any]:
    """Compute N×N Pearson correlation matrix.

    Args:
        body: CorrelationMatrixRequest with ticker list.

    Returns:
        CorrelationMatrix as dict.

    Raises:
        HTTPException 422: If any ticker has no stored returns.
    """
    try:
        matrix = _corr_engine.compute_correlation_matrix(body.tickers)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return matrix.to_dict()


@router.get("/correlation/matrix/{matrix_id}", response_model=Dict[str, Any], tags=["Correlation"])
def correlation_get_matrix(matrix_id: str) -> Dict[str, Any]:
    """Retrieve a cached correlation matrix by ID.

    Args:
        matrix_id: UUID of the matrix.

    Returns:
        CorrelationMatrix as dict.

    Raises:
        HTTPException 404: If not found.
    """
    matrix = _corr_engine.get_correlation_matrix(matrix_id)
    if matrix is None:
        raise HTTPException(status_code=404, detail=f"Correlation matrix '{matrix_id}' not found")
    return matrix.to_dict()


@router.post("/correlation/rolling", response_model=Dict[str, Any], tags=["Correlation"])
def correlation_rolling(body: RollingCorrelationRequest) -> Dict[str, Any]:
    """Compute rolling-window correlation between two tickers.

    Args:
        body: RollingCorrelationRequest.

    Returns:
        RollingCorrelation as dict.

    Raises:
        HTTPException 422: If either ticker is not stored.
    """
    try:
        result = _corr_engine.compute_rolling_correlation(body.ticker_a, body.ticker_b, body.window)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result.to_dict()


@router.post("/correlation/clusters", response_model=List[Dict[str, Any]], tags=["Correlation"])
def correlation_clusters(body: ClusterRequest) -> List[Dict[str, Any]]:
    """Detect threshold-based correlation clusters.

    Args:
        body: ClusterRequest with tickers and threshold.

    Returns:
        List of CorrelationCluster dicts.

    Raises:
        HTTPException 422: If any ticker is not stored.
    """
    try:
        clusters = _corr_engine.detect_clusters(body.tickers, body.threshold)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return [c.to_dict() for c in clusters]


@router.post("/correlation/pairwise", response_model=Dict[str, Any], tags=["Correlation"])
def correlation_pairwise(body: PairwiseCorrelationRequest) -> Dict[str, Any]:
    """Compute scalar Pearson correlation between two tickers.

    Args:
        body: PairwiseCorrelationRequest.

    Returns:
        Dict with ticker_a, ticker_b, and correlation.

    Raises:
        HTTPException 422: If either ticker is not stored.
    """
    try:
        corr = _corr_engine.pairwise_correlation(body.ticker_a, body.ticker_b)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ticker_a": body.ticker_a, "ticker_b": body.ticker_b, "correlation": corr}


@router.post("/correlation/most-correlated", response_model=Dict[str, Any], tags=["Correlation"])
def correlation_most_correlated(body: MostCorrelatedRequest) -> Dict[str, Any]:
    """Find the most correlated pair among the given tickers.

    Args:
        body: MostCorrelatedRequest with tickers list.

    Returns:
        Dict with ticker_a, ticker_b, and correlation.
    """
    ta, tb, corr = _corr_engine.most_correlated_pair(body.tickers)
    return {"ticker_a": ta, "ticker_b": tb, "correlation": corr}


@router.post("/correlation/least-correlated", response_model=Dict[str, Any], tags=["Correlation"])
def correlation_least_correlated(body: LeastCorrelatedRequest) -> Dict[str, Any]:
    """Find the least correlated pair among the given tickers.

    Args:
        body: LeastCorrelatedRequest with tickers list.

    Returns:
        Dict with ticker_a, ticker_b, and correlation.
    """
    ta, tb, corr = _corr_engine.least_correlated_pair(body.tickers)
    return {"ticker_a": ta, "ticker_b": tb, "correlation": corr}


@router.get("/correlation/tickers", response_model=List[str], tags=["Correlation"])
def correlation_list_tickers() -> List[str]:
    """List all tickers with stored return data.

    Returns:
        Sorted list of ticker symbols.
    """
    return _corr_engine.list_tickers()


@router.delete("/correlation/reset", response_model=Dict[str, str], tags=["Correlation"])
def correlation_reset() -> Dict[str, str]:
    """Clear all stored returns and cached matrices.

    Returns:
        Confirmation message.
    """
    _corr_engine.reset()
    return {"status": "ok", "message": "Correlation engine cache cleared"}


# ---------------------------------------------------------------------------
# Covariance endpoints
# ---------------------------------------------------------------------------

@router.post("/covariance/matrix", response_model=Dict[str, Any], tags=["Covariance"])
def covariance_matrix(body: CovarianceMatrixRequest) -> Dict[str, Any]:
    """Compute N×N sample covariance matrix.

    Args:
        body: CovarianceMatrixRequest with tickers and annualize flag.

    Returns:
        CovarianceMatrix as dict.

    Raises:
        HTTPException 422: If any ticker has no stored returns.
    """
    try:
        matrix = _corr_engine.compute_covariance_matrix(body.tickers, body.annualize)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return matrix.to_dict()


@router.get("/covariance/matrix/{matrix_id}", response_model=Dict[str, Any], tags=["Covariance"])
def covariance_get_matrix(matrix_id: str) -> Dict[str, Any]:
    """Retrieve a cached covariance matrix by ID.

    Args:
        matrix_id: UUID of the matrix.

    Returns:
        CovarianceMatrix as dict.

    Raises:
        HTTPException 404: If not found.
    """
    matrix = _corr_engine.get_covariance_matrix(matrix_id)
    if matrix is None:
        raise HTTPException(status_code=404, detail=f"Covariance matrix '{matrix_id}' not found")
    return matrix.to_dict()


# ---------------------------------------------------------------------------
# Strategy Comparison endpoints
# ---------------------------------------------------------------------------

@router.post("/comparison/register", response_model=Dict[str, Any], tags=["Comparison"])
def comparison_register(body: RegisterResultRequest) -> Dict[str, Any]:
    """Register a pre-computed M19 backtest result for comparison.

    The backtest_id must correspond to a result stored in the M19 BacktestEngine
    singleton.  This endpoint fetches it and derives StrategyMetrics.

    Args:
        body: RegisterResultRequest with strategy_name and backtest_id.

    Returns:
        Dict with strategy_id and strategy_name.

    Raises:
        HTTPException 404: If backtest_id is not found in the M19 engine.
    """
    from routers.m19_research import _backtest_engine as m19_engine
    result = m19_engine.get_result(body.backtest_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Backtest result '{body.backtest_id}' not found in M19 engine",
        )
    sid = _comparison_engine.register_result(body.strategy_name, result)
    return {"strategy_id": sid, "strategy_name": body.strategy_name}


@router.post("/comparison/run-and-register", response_model=Dict[str, Any], tags=["Comparison"])
def comparison_run_and_register(body: RunAndRegisterRequest) -> Dict[str, Any]:
    """Run a fresh backtest and register the result for comparison.

    Args:
        body: RunAndRegisterRequest with strategy config and price/signal data.

    Returns:
        Dict with strategy_id, strategy_name, and backtest summary.

    Raises:
        HTTPException 422: On invalid input.
    """
    try:
        price_data_native: Dict[str, list] = {}
        for ticker, bars in body.price_data.items():
            price_data_native[ticker] = [_dict_to_price_bar(b) for b in bars]

        from services.m19_backtest_engine import Signal, SignalType as ST
        signals_native = [
            Signal(date=date, ticker=body.ticker, signal_type=ST(sig))
            for date, sig in body.signals.items()
        ]

        sid = _comparison_engine.run_and_register(
            strategy_name=body.strategy_name,
            ticker=body.ticker,
            price_data=price_data_native,
            signals=signals_native,
            initial_capital=body.initial_capital,
            commission_rate=body.commission_rate,
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    metrics = _comparison_engine.get_metrics(sid)
    return {
        "strategy_id": sid,
        "strategy_name": body.strategy_name,
        "metrics": metrics.to_dict() if metrics else None,
    }


@router.post("/comparison/compare", response_model=Dict[str, Any], tags=["Comparison"])
def comparison_compare(body: CompareRequest) -> Dict[str, Any]:
    """Produce a ranked comparison table for multiple strategies.

    Args:
        body: CompareRequest with strategy IDs and ranking metric.

    Returns:
        ComparisonResult as dict.

    Raises:
        HTTPException 422: On invalid input.
    """
    try:
        result = _comparison_engine.compare(
            strategy_ids=body.strategy_ids,
            primary_metric=body.primary_metric,
            include_correlation=body.include_correlation,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result.to_dict()


@router.get("/comparison/result/{comparison_id}", response_model=Dict[str, Any], tags=["Comparison"])
def comparison_get_result(comparison_id: str) -> Dict[str, Any]:
    """Retrieve a cached comparison result.

    Args:
        comparison_id: UUID of the comparison.

    Returns:
        ComparisonResult as dict.

    Raises:
        HTTPException 404: If not found.
    """
    result = _comparison_engine.get_comparison(comparison_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Comparison '{comparison_id}' not found")
    return result.to_dict()


@router.get("/comparison/metrics/{strategy_id}", response_model=Dict[str, Any], tags=["Comparison"])
def comparison_get_metrics(strategy_id: str) -> Dict[str, Any]:
    """Retrieve metrics for a registered strategy.

    Args:
        strategy_id: UUID of the strategy.

    Returns:
        StrategyMetrics as dict.

    Raises:
        HTTPException 404: If not found.
    """
    metrics = _comparison_engine.get_metrics(strategy_id)
    if metrics is None:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_id}' not found")
    return metrics.to_dict()


@router.post("/comparison/best", response_model=Dict[str, Any], tags=["Comparison"])
def comparison_best_by_metric(body: BestByMetricRequest) -> Dict[str, Any]:
    """Return the strategy with the best value for a single metric.

    Args:
        body: BestByMetricRequest with strategy IDs and metric.

    Returns:
        Best StrategyMetrics as dict.

    Raises:
        HTTPException 422: On invalid input.
    """
    try:
        metrics = _comparison_engine.best_by_metric(body.strategy_ids, body.metric)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if metrics is None:
        raise HTTPException(status_code=404, detail="No strategies found")
    return metrics.to_dict()


@router.post("/comparison/rank", response_model=List[Dict[str, Any]], tags=["Comparison"])
def comparison_rank_by_metric(body: RankByMetricRequest) -> List[Dict[str, Any]]:
    """Return all strategies ranked by a single metric.

    Args:
        body: RankByMetricRequest with strategy IDs and metric.

    Returns:
        List of {rank, metrics} dicts sorted best-first.

    Raises:
        HTTPException 422: On invalid metric.
    """
    try:
        ranked = _comparison_engine.rank_by_metric(body.strategy_ids, body.metric)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return [{"rank": rank, **m.to_dict()} for rank, m in ranked]


@router.post("/comparison/head-to-head", response_model=Dict[str, Any], tags=["Comparison"])
def comparison_head_to_head(body: HeadToHeadRequest) -> Dict[str, Any]:
    """Produce a head-to-head comparison between two strategies.

    Args:
        body: HeadToHeadRequest with two strategy UUIDs.

    Returns:
        Per-metric winner table and overall winner.

    Raises:
        HTTPException 422: If either strategy_id is unknown.
    """
    try:
        result = _comparison_engine.head_to_head(body.strategy_id_a, body.strategy_id_b)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


@router.get("/comparison/strategies", response_model=List[Dict[str, str]], tags=["Comparison"])
def comparison_list_strategies() -> List[Dict[str, str]]:
    """List all registered strategies.

    Returns:
        List of {strategy_id, strategy_name} dicts.
    """
    return _comparison_engine.list_strategies()


@router.delete("/comparison/reset", response_model=Dict[str, str], tags=["Comparison"])
def comparison_reset() -> Dict[str, str]:
    """Clear all registered strategies and comparisons.

    Returns:
        Confirmation message.
    """
    _comparison_engine.reset()
    return {"status": "ok", "message": "Strategy comparison engine cleared"}
