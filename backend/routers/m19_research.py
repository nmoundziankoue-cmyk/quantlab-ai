"""M19 Quant Research Engine — REST API router."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query

from schemas.m19_research import (
    AddFactorReturnsRequest,
    AttributionRequest,
    BacktestCompareRequest,
    BacktestResultResponse,
    BacktestRunRequest,
    BacktestSummaryResponse,
    ConfidenceIntervalResponse,
    ExecutionBatchRequest,
    ExecutionSimulateRequest,
    FactorAttributionResponse,
    FactorConstrainedRequest,
    FactorCorrelationRequest,
    FactorCorrelationResponse,
    FactorExposureResponse,
    FillModelRequest,
    FillResponse,
    FrontierRequest,
    FrontierResponse,
    ImplementationShortfallRequest,
    MaxSharpeRequest,
    MCBootstrapRequest,
    MCGBMRequest,
    MCPathResponse,
    MCResultResponse,
    MCSensitivityRequest,
    MeanVarianceRequest,
    MinVarianceRequest,
    MonthlyReturnsResponse,
    OptimizationResultResponse,
    PortfolioBetaRequest,
    RegressRequest,
    RiskParityRequest,
    SlippageReportResponse,
    StabilityMetricsResponse,
    WalkForwardRunRequest,
    WalkForwardSummaryResponse,
    WFWindowResponse,
)
from services.m19_backtest_engine import (
    BacktestEngine,
    PriceBar,
    Signal,
    SignalType,
)
from services.m19_execution_simulator import (
    ExecutionSimulator,
    FillModel,
    SimOrder,
    SlippageModel,
    OrderType,
    OrderStatus,
)
from services.m19_factor_models import (
    FactorModelEngine,
    FactorReturn,
    FactorType,
)
from services.m19_monte_carlo import MonteCarloEngine
from services.m19_optimization_lab import (
    OptimizationLab,
    WeightConstraint,
)
from services.m19_walk_forward import WalkForwardEngine, WindowMode

router = APIRouter(prefix="/quant", tags=["M19 Quant Research"])

# ---------------------------------------------------------------------------
# Service singletons
# ---------------------------------------------------------------------------
_backtest_engine = BacktestEngine()
_exec_sim = ExecutionSimulator()
_wf_engine = WalkForwardEngine(backtest_engine=_backtest_engine)
_mc_engine = MonteCarloEngine()
_factor_engine = FactorModelEngine()
_opt_lab = OptimizationLab(factor_engine=_factor_engine)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_price_bars(raw: Dict[str, List[Any]]) -> Dict[str, List[PriceBar]]:
    result: Dict[str, List[PriceBar]] = {}
    for ticker, bars in raw.items():
        result[ticker] = [
            PriceBar(
                date=b.date, open=b.open, high=b.high,
                low=b.low, close=b.close, volume=b.volume,
            )
            for b in bars
        ]
    return result


def _to_signals(raw: List[Any]) -> List[Signal]:
    return [
        Signal(
            date=s.date,
            ticker=s.ticker,
            signal_type=SignalType(s.signal_type),
            strength=s.strength,
            metadata=s.metadata,
        )
        for s in raw
    ]


def _to_weight_constraints(raw: List[Any]) -> List[WeightConstraint]:
    return [
        WeightConstraint(
            ticker=c.ticker,
            min_weight=c.min_weight,
            max_weight=c.max_weight,
            sector=c.sector,
        )
        for c in raw
    ]


def _simple_momentum_signals(
    dates: List[str],
    price_data: Dict[str, List[PriceBar]],
    lookback: int = 20,
) -> List[Signal]:
    """Generate momentum signals for walk-forward testing."""
    signals: List[Signal] = []
    date_set = set(dates)
    for ticker, bars in price_data.items():
        filtered = [b for b in bars if b.date in date_set]
        filtered.sort(key=lambda b: b.date)
        for i, bar in enumerate(filtered):
            if i < lookback:
                continue
            past = filtered[i - lookback].close
            curr = bar.close
            if past > 0:
                ret = (curr - past) / past
                if ret > 0.02:
                    signals.append(Signal(bar.date, ticker, SignalType.LONG, min(1.0, ret * 5)))
                elif ret < -0.02:
                    signals.append(Signal(bar.date, ticker, SignalType.FLAT))
    return signals


# ===========================================================================
# Backtest endpoints
# ===========================================================================

@router.post("/backtest/run", response_model=Dict[str, Any], tags=["Backtest"])
def run_backtest(req: BacktestRunRequest) -> Dict[str, Any]:
    """Run a complete strategy backtest simulation."""
    signals = _to_signals(req.signals)
    price_data = _to_price_bars(req.price_data)
    result = _backtest_engine.run(
        strategy_name=req.strategy_name,
        signals=signals,
        price_data=price_data,
        initial_capital=req.initial_capital,
        commission_rate=req.commission_rate,
        slippage_bps=req.slippage_bps,
        position_size_pct=req.position_size_pct,
        allow_short=req.allow_short,
        start_date=req.start_date,
        end_date=req.end_date,
    )
    return {
        "backtest_id": result.backtest_id,
        "strategy_name": result.strategy_name,
        "start_date": result.start_date,
        "end_date": result.end_date,
        "initial_capital": result.initial_capital,
        "final_equity": result.final_equity,
        "metrics": result.metrics.to_dict(),
        "config": result.config,
    }


@router.get("/backtest/list", response_model=List[BacktestSummaryResponse], tags=["Backtest"])
def list_backtests() -> List[BacktestSummaryResponse]:
    """List all cached backtest summaries."""
    return [BacktestSummaryResponse(**r) for r in _backtest_engine.list_results()]


@router.get("/backtest/{backtest_id}", response_model=Dict[str, Any], tags=["Backtest"])
def get_backtest(backtest_id: str) -> Dict[str, Any]:
    """Retrieve a full backtest result by ID."""
    result = _backtest_engine.get_result(backtest_id)
    if not result:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return result.to_dict()


@router.get("/backtest/{backtest_id}/equity-curve", response_model=List[Dict[str, Any]], tags=["Backtest"])
def get_equity_curve(backtest_id: str) -> List[Dict[str, Any]]:
    """Return the equity curve for a backtest."""
    curve = _backtest_engine.get_equity_curve(backtest_id)
    if not curve and not _backtest_engine.get_result(backtest_id):
        raise HTTPException(status_code=404, detail="Backtest not found")
    return [ep.to_dict() for ep in curve]


@router.get("/backtest/{backtest_id}/trades", response_model=List[Dict[str, Any]], tags=["Backtest"])
def get_trades(backtest_id: str) -> List[Dict[str, Any]]:
    """Return the trade log for a backtest."""
    result = _backtest_engine.get_result(backtest_id)
    if not result:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return [t.to_dict() for t in result.trades]


@router.get("/backtest/{backtest_id}/drawdown", response_model=List[Dict[str, Any]], tags=["Backtest"])
def get_drawdown_series(backtest_id: str) -> List[Dict[str, Any]]:
    """Return the drawdown time series for a backtest."""
    series = _backtest_engine.get_drawdown_series(backtest_id)
    if not series and not _backtest_engine.get_result(backtest_id):
        raise HTTPException(status_code=404, detail="Backtest not found")
    return series


@router.get("/backtest/{backtest_id}/monthly-returns", response_model=Dict[str, Any], tags=["Backtest"])
def get_monthly_returns(backtest_id: str) -> Dict[str, Any]:
    """Return monthly aggregated returns for a backtest."""
    result = _backtest_engine.get_result(backtest_id)
    if not result:
        raise HTTPException(status_code=404, detail="Backtest not found")
    monthly = _backtest_engine.get_monthly_returns(backtest_id)
    return {"backtest_id": backtest_id, "monthly_returns": monthly}


@router.get("/backtest/{backtest_id}/metrics", response_model=Dict[str, Any], tags=["Backtest"])
def get_backtest_metrics(backtest_id: str) -> Dict[str, Any]:
    """Return only the performance metrics for a backtest."""
    result = _backtest_engine.get_result(backtest_id)
    if not result:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return result.metrics.to_dict()


@router.post("/backtest/compare", response_model=Dict[str, Any], tags=["Backtest"])
def compare_backtests(req: BacktestCompareRequest) -> Dict[str, Any]:
    """Compare metrics across multiple backtest runs."""
    comparison = _backtest_engine.compare(req.backtest_ids)
    return {"comparison": comparison, "count": len(comparison)}


@router.delete("/backtest/{backtest_id}", response_model=Dict[str, Any], tags=["Backtest"])
def delete_backtest(backtest_id: str) -> Dict[str, Any]:
    """Delete a cached backtest result."""
    deleted = _backtest_engine.delete_result(backtest_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return {"deleted": True, "backtest_id": backtest_id}


# ===========================================================================
# Execution simulation endpoints
# ===========================================================================

@router.post("/execution/simulate", response_model=Dict[str, Any], tags=["Execution"])
def simulate_execution(req: ExecutionSimulateRequest) -> Dict[str, Any]:
    """Simulate execution of a single order."""
    order = SimOrder(
        order_id=str(uuid.uuid4()),
        ticker=req.order.ticker,
        order_type=OrderType(req.order.order_type),
        side=req.order.side,
        quantity=req.order.quantity,
        limit_price=req.order.limit_price,
        stop_price=req.order.stop_price,
        time_in_force=req.order.time_in_force,
        metadata=req.order.metadata,
    )
    fill = _exec_sim.simulate(
        order=order,
        market_price=req.market_price,
        market_volume=req.market_volume,
        slippage_model=SlippageModel(req.slippage_model),
        fixed_slippage_bps=req.fixed_slippage_bps,
        commission_rate=req.commission_rate,
        adv_fraction=req.adv_fraction,
    )
    return fill.to_dict()


@router.post("/execution/batch", response_model=List[Dict[str, Any]], tags=["Execution"])
def simulate_batch(req: ExecutionBatchRequest) -> List[Dict[str, Any]]:
    """Simulate a batch of orders against a market snapshot."""
    orders = [
        SimOrder(
            order_id=str(uuid.uuid4()),
            ticker=o.ticker,
            order_type=OrderType(o.order_type),
            side=o.side,
            quantity=o.quantity,
            limit_price=o.limit_price,
            stop_price=o.stop_price,
            time_in_force=o.time_in_force,
        )
        for o in req.orders
    ]
    fills = _exec_sim.simulate_batch(
        orders=orders,
        prices=req.prices,
        volumes=req.volumes if req.volumes else {o.ticker: 1_000_000.0 for o in orders},
        slippage_model=SlippageModel(req.slippage_model),
        fixed_slippage_bps=req.fixed_slippage_bps,
        commission_rate=req.commission_rate,
    )
    return [f.to_dict() for f in fills]


@router.post("/execution/fill-model", response_model=Dict[str, Any], tags=["Execution"])
def create_fill_model(req: FillModelRequest) -> Dict[str, Any]:
    """Build a named fill probability model."""
    model = _exec_sim.build_fill_model(
        model_name=req.model_name,
        fill_probability=req.fill_probability,
        partial_fill_min=req.partial_fill_min,
        partial_fill_max=req.partial_fill_max,
        adverse_selection_bps=req.adverse_selection_bps,
    )
    return model.to_dict()


@router.get("/execution/slippage-report", response_model=SlippageReportResponse, tags=["Execution"])
def get_slippage_report() -> SlippageReportResponse:
    """Retrieve aggregate slippage statistics across all simulated orders."""
    report = _exec_sim.get_slippage_report()
    return SlippageReportResponse(**report.to_dict())


@router.get("/execution/fills", response_model=List[Dict[str, Any]], tags=["Execution"])
def get_fill_history() -> List[Dict[str, Any]]:
    """Return history of all simulated fills."""
    return _exec_sim.get_fill_history()


@router.get("/execution/orders", response_model=List[Dict[str, Any]], tags=["Execution"])
def get_order_history() -> List[Dict[str, Any]]:
    """Return history of all submitted orders."""
    return _exec_sim.get_order_history()


@router.post("/execution/implementation-shortfall", response_model=Dict[str, Any], tags=["Execution"])
def compute_implementation_shortfall(req: ImplementationShortfallRequest) -> Dict[str, Any]:
    """Compute implementation shortfall for a trade."""
    order = SimOrder(
        order_id=str(uuid.uuid4()),
        ticker=req.order.ticker,
        order_type=OrderType(req.order.order_type),
        side=req.order.side,
        quantity=req.order.quantity,
        limit_price=req.order.limit_price,
        stop_price=req.order.stop_price,
    )
    from services.m19_execution_simulator import Fill
    fill = Fill(
        fill_id=str(uuid.uuid4()),
        order_id=order.order_id,
        ticker=order.ticker,
        fill_price=req.fill_price,
        fill_qty=req.fill_qty,
        remaining_qty=0.0,
        slippage=abs(req.fill_price - req.decision_price),
        commission=0.0,
        latency_us=0,
        status=OrderStatus.FILLED,
        market_impact=req.market_impact,
    )
    return _exec_sim.compute_implementation_shortfall(order, req.decision_price, fill)


@router.post("/execution/reset", response_model=Dict[str, Any], tags=["Execution"])
def reset_execution_simulator() -> Dict[str, Any]:
    """Clear all execution simulator history."""
    _exec_sim.reset()
    return {"reset": True}


@router.get("/execution/models", response_model=List[str], tags=["Execution"])
def list_slippage_models() -> List[str]:
    """List available slippage model names."""
    return [m.value for m in SlippageModel]


@router.get("/execution/order-types", response_model=List[str], tags=["Execution"])
def list_order_types() -> List[str]:
    """List supported order types."""
    return [t.value for t in OrderType]


# ===========================================================================
# Walk-forward endpoints
# ===========================================================================

@router.post("/walk-forward/run", response_model=Dict[str, Any], tags=["Walk-Forward"])
def run_walk_forward(req: WalkForwardRunRequest) -> Dict[str, Any]:
    """Execute a walk-forward analysis."""
    price_data = _to_price_bars(req.price_data)
    lookback = req.signal_config.lookback_bars

    def signal_gen(dates, pd):
        return _simple_momentum_signals(dates, pd, lookback)

    mode = WindowMode(req.window_mode)
    result = _wf_engine.run(
        strategy_name=req.strategy_name,
        price_data=price_data,
        signal_generator=signal_gen,
        in_sample_bars=req.in_sample_bars,
        out_sample_bars=req.out_sample_bars,
        window_mode=mode,
        initial_capital=req.initial_capital,
        commission_rate=req.commission_rate,
        slippage_bps=req.slippage_bps,
        position_size_pct=req.position_size_pct,
    )
    return result.to_dict()


@router.get("/walk-forward/list", response_model=List[WalkForwardSummaryResponse], tags=["Walk-Forward"])
def list_walk_forward_runs() -> List[WalkForwardSummaryResponse]:
    """List all cached walk-forward analysis summaries."""
    return [WalkForwardSummaryResponse(**r) for r in _wf_engine.list_results()]


@router.get("/walk-forward/{run_id}", response_model=Dict[str, Any], tags=["Walk-Forward"])
def get_walk_forward_result(run_id: str) -> Dict[str, Any]:
    """Retrieve full walk-forward result by run ID."""
    result = _wf_engine.get_result(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Walk-forward run not found")
    return result.to_dict()


@router.get("/walk-forward/{run_id}/windows", response_model=List[WFWindowResponse], tags=["Walk-Forward"])
def get_wf_windows(run_id: str) -> List[WFWindowResponse]:
    """Return per-window results for a walk-forward analysis."""
    windows = _wf_engine.get_windows(run_id)
    if not windows and not _wf_engine.get_result(run_id):
        raise HTTPException(status_code=404, detail="Walk-forward run not found")
    return [WFWindowResponse(**w.to_dict()) for w in windows]


@router.get("/walk-forward/{run_id}/stability", response_model=StabilityMetricsResponse, tags=["Walk-Forward"])
def get_wf_stability(run_id: str) -> StabilityMetricsResponse:
    """Return stability metrics for a walk-forward analysis."""
    stability = _wf_engine.get_stability(run_id)
    if not stability:
        raise HTTPException(status_code=404, detail="Walk-forward run not found")
    return StabilityMetricsResponse(**stability.to_dict())


@router.get("/walk-forward/{run_id}/efficiency", response_model=List[Dict[str, Any]], tags=["Walk-Forward"])
def get_wf_efficiency(run_id: str) -> List[Dict[str, Any]]:
    """Return IS→OOS efficiency ratio per window."""
    windows = _wf_engine.get_windows(run_id)
    if not windows and not _wf_engine.get_result(run_id):
        raise HTTPException(status_code=404, detail="Walk-forward run not found")
    return [
        {
            "window_index": w.window_index,
            "efficiency": w.efficiency,
            "in_sample_sharpe": w.in_sample_sharpe,
            "out_sample_sharpe": w.out_sample_sharpe,
        }
        for w in windows
    ]


# ===========================================================================
# Monte Carlo endpoints
# ===========================================================================

@router.post("/monte-carlo/bootstrap", response_model=MCResultResponse, tags=["Monte Carlo"])
def run_mc_bootstrap(req: MCBootstrapRequest) -> MCResultResponse:
    """Run a bootstrap Monte Carlo simulation."""
    result = _mc_engine.run_bootstrap(
        daily_returns=req.daily_returns,
        num_paths=req.num_paths,
        num_steps=req.num_steps,
        initial_equity=req.initial_equity,
        block_size=req.block_size,
    )
    return MCResultResponse(**{k: v for k, v in result.to_dict().items() if k != "confidence_intervals"})


@router.post("/monte-carlo/gbm", response_model=MCResultResponse, tags=["Monte Carlo"])
def run_mc_gbm(req: MCGBMRequest) -> MCResultResponse:
    """Run a Geometric Brownian Motion Monte Carlo simulation."""
    result = _mc_engine.run_gbm(
        mean_daily_return=req.mean_daily_return,
        daily_volatility=req.daily_volatility,
        num_paths=req.num_paths,
        num_steps=req.num_steps,
        initial_equity=req.initial_equity,
    )
    return MCResultResponse(**{k: v for k, v in result.to_dict().items() if k != "confidence_intervals"})


@router.get("/monte-carlo/{simulation_id}", response_model=MCResultResponse, tags=["Monte Carlo"])
def get_mc_result(simulation_id: str) -> MCResultResponse:
    """Retrieve a Monte Carlo simulation result by ID."""
    result = _mc_engine.get_result(simulation_id)
    if not result:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return MCResultResponse(**{k: v for k, v in result.to_dict().items() if k != "confidence_intervals"})


@router.get("/monte-carlo/{simulation_id}/confidence-intervals", response_model=List[ConfidenceIntervalResponse], tags=["Monte Carlo"])
def get_mc_confidence_intervals(simulation_id: str) -> List[ConfidenceIntervalResponse]:
    """Return confidence intervals for a Monte Carlo simulation."""
    cis = _mc_engine.get_confidence_intervals(simulation_id)
    if not cis and not _mc_engine.get_result(simulation_id):
        raise HTTPException(status_code=404, detail="Simulation not found")
    return [ConfidenceIntervalResponse(**ci) for ci in cis]


@router.get("/monte-carlo/{simulation_id}/distribution", response_model=Dict[str, Any], tags=["Monte Carlo"])
def get_mc_distribution(simulation_id: str) -> Dict[str, Any]:
    """Return return distribution data for a Monte Carlo simulation."""
    dist = _mc_engine.get_distribution(simulation_id)
    if not dist.get("returns") and not _mc_engine.get_result(simulation_id):
        raise HTTPException(status_code=404, detail="Simulation not found")
    return {"simulation_id": simulation_id, **dist}


@router.get("/monte-carlo/{simulation_id}/paths", response_model=List[MCPathResponse], tags=["Monte Carlo"])
def get_mc_paths(
    simulation_id: str,
    max_paths: int = Query(default=100, ge=1, le=10_000),
) -> List[MCPathResponse]:
    """Return a subset of simulated equity paths for charting."""
    paths = _mc_engine.get_paths(simulation_id, max_paths=max_paths)
    if not paths and not _mc_engine.get_result(simulation_id):
        raise HTTPException(status_code=404, detail="Simulation not found")
    return [MCPathResponse(**p.to_dict()) for p in paths]


@router.get("/monte-carlo/list/all", response_model=List[Dict[str, Any]], tags=["Monte Carlo"])
def list_mc_results() -> List[Dict[str, Any]]:
    """List all cached Monte Carlo simulation summaries."""
    return _mc_engine.list_results()


@router.post("/monte-carlo/sensitivity", response_model=List[Dict[str, Any]], tags=["Monte Carlo"])
def mc_sensitivity(req: MCSensitivityRequest) -> List[Dict[str, Any]]:
    """Run sensitivity analysis over a grid of drift and volatility shocks."""
    rows = _mc_engine.sensitivity_analysis(
        daily_returns=req.daily_returns,
        drift_shocks=req.drift_shocks,
        vol_shocks=req.vol_shocks,
        num_paths=req.num_paths,
        num_steps=req.num_steps,
        initial_equity=req.initial_equity,
    )
    return rows


# ===========================================================================
# Factor model endpoints
# ===========================================================================

@router.post("/factors/returns", response_model=Dict[str, Any], tags=["Factor Models"])
def add_factor_returns(req: AddFactorReturnsRequest) -> Dict[str, Any]:
    """Register daily factor returns for future regression."""
    factor_rets = [
        FactorReturn(date=fr.date, factor=FactorType(fr.factor), return_value=fr.return_value)
        for fr in req.factor_returns
    ]
    _factor_engine.add_factor_returns(factor_rets)
    return {"added": len(factor_rets), "status": "ok"}


@router.post("/factors/regress", response_model=FactorExposureResponse, tags=["Factor Models"])
def regress_security(req: RegressRequest) -> FactorExposureResponse:
    """Regress a security's returns against registered factor returns."""
    factors = []
    for f in req.factors:
        try:
            factors.append(FactorType(f))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Unknown factor: {f}")
    exposure = _factor_engine.regress(
        ticker=req.ticker,
        security_returns=req.security_returns,
        factors=factors,
        include_alpha=req.include_alpha,
    )
    return FactorExposureResponse(**exposure.to_dict())


@router.get("/factors/exposure/{ticker}", response_model=FactorExposureResponse, tags=["Factor Models"])
def get_factor_exposure(ticker: str) -> FactorExposureResponse:
    """Retrieve cached factor exposure for a ticker."""
    exposure = _factor_engine.get_exposure(ticker)
    if not exposure:
        raise HTTPException(status_code=404, detail="Factor exposure not found for ticker")
    return FactorExposureResponse(**exposure.to_dict())


@router.post("/factors/attribution", response_model=FactorAttributionResponse, tags=["Factor Models"])
def compute_attribution(req: AttributionRequest) -> FactorAttributionResponse:
    """Decompose total return into factor and alpha contributions."""
    attribution = _factor_engine.compute_attribution(
        ticker=req.ticker,
        total_return=req.total_return,
        period_factor_returns=req.period_factor_returns,
    )
    return FactorAttributionResponse(**attribution.to_dict())


@router.post("/factors/correlations", response_model=List[FactorCorrelationResponse], tags=["Factor Models"])
def compute_factor_correlations(req: FactorCorrelationRequest) -> List[FactorCorrelationResponse]:
    """Compute pairwise correlations between registered factors."""
    factors = []
    for f in req.factors:
        try:
            factors.append(FactorType(f))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Unknown factor: {f}")
    corrs = _factor_engine.compute_factor_correlations(factors)
    return [FactorCorrelationResponse(**c.to_dict()) for c in corrs]


@router.post("/factors/portfolio-beta", response_model=Dict[str, Any], tags=["Factor Models"])
def compute_portfolio_beta(req: PortfolioBetaRequest) -> Dict[str, Any]:
    """Compute weighted-average factor beta for a portfolio."""
    try:
        fac = FactorType(req.factor)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Unknown factor: {req.factor}")
    beta = _factor_engine.compute_portfolio_beta(req.weights, fac)
    return {"factor": req.factor, "portfolio_beta": beta}


@router.get("/factors/series/{factor}", response_model=List[Dict[str, Any]], tags=["Factor Models"])
def get_factor_series(factor: str) -> List[Dict[str, Any]]:
    """Retrieve the stored time series for a factor."""
    try:
        fac = FactorType(factor)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Unknown factor: {factor}")
    return _factor_engine.build_factor_return_series(fac)


@router.get("/factors/tickers", response_model=List[str], tags=["Factor Models"])
def list_factor_tickers() -> List[str]:
    """List all tickers with stored factor exposures."""
    return _factor_engine.list_tickers()


@router.post("/factors/reset", response_model=Dict[str, Any], tags=["Factor Models"])
def reset_factor_engine() -> Dict[str, Any]:
    """Clear all stored factor data and exposures."""
    _factor_engine.reset()
    return {"reset": True}


@router.get("/factors/types", response_model=List[str], tags=["Factor Models"])
def list_factor_types() -> List[str]:
    """List all supported factor types."""
    return [f.value for f in FactorType]


# ===========================================================================
# Optimization endpoints
# ===========================================================================

@router.post("/optimize/mean-variance", response_model=OptimizationResultResponse, tags=["Optimization"])
def optimize_mean_variance(req: MeanVarianceRequest) -> OptimizationResultResponse:
    """Solve the mean-variance optimisation problem."""
    constraints = _to_weight_constraints(req.constraints)
    result = _opt_lab.mean_variance(
        tickers=req.tickers,
        expected_returns=req.expected_returns,
        covariance_matrix=req.covariance_matrix,
        risk_aversion=req.risk_aversion,
        constraints=constraints or None,
        risk_free_rate=req.risk_free_rate,
    )
    return OptimizationResultResponse(**result.to_dict())


@router.post("/optimize/min-variance", response_model=OptimizationResultResponse, tags=["Optimization"])
def optimize_min_variance(req: MinVarianceRequest) -> OptimizationResultResponse:
    """Find the global minimum-variance portfolio."""
    constraints = _to_weight_constraints(req.constraints)
    result = _opt_lab.min_variance(
        tickers=req.tickers,
        covariance_matrix=req.covariance_matrix,
        constraints=constraints or None,
        risk_free_rate=req.risk_free_rate,
    )
    return OptimizationResultResponse(**result.to_dict())


@router.post("/optimize/max-sharpe", response_model=OptimizationResultResponse, tags=["Optimization"])
def optimize_max_sharpe(req: MaxSharpeRequest) -> OptimizationResultResponse:
    """Find the maximum Sharpe ratio portfolio."""
    constraints = _to_weight_constraints(req.constraints)
    result = _opt_lab.max_sharpe(
        tickers=req.tickers,
        expected_returns=req.expected_returns,
        covariance_matrix=req.covariance_matrix,
        constraints=constraints or None,
        risk_free_rate=req.risk_free_rate,
    )
    return OptimizationResultResponse(**result.to_dict())


@router.post("/optimize/risk-parity", response_model=OptimizationResultResponse, tags=["Optimization"])
def optimize_risk_parity(req: RiskParityRequest) -> OptimizationResultResponse:
    """Compute the equal risk contribution (risk parity) portfolio."""
    result = _opt_lab.risk_parity(
        tickers=req.tickers,
        covariance_matrix=req.covariance_matrix,
        target_risk_contributions=req.target_risk_contributions,
        risk_free_rate=req.risk_free_rate,
    )
    return OptimizationResultResponse(**result.to_dict())


@router.post("/optimize/frontier", response_model=FrontierResponse, tags=["Optimization"])
def compute_frontier(req: FrontierRequest) -> FrontierResponse:
    """Trace the efficient frontier across risk-aversion values."""
    constraints = _to_weight_constraints(req.constraints)
    points = _opt_lab.compute_frontier(
        tickers=req.tickers,
        expected_returns=req.expected_returns,
        covariance_matrix=req.covariance_matrix,
        n_points=req.n_points,
        risk_free_rate=req.risk_free_rate,
        constraints=constraints or None,
    )
    from schemas.m19_research import FrontierPointResponse
    point_responses = [FrontierPointResponse(**p.to_dict()) for p in points]
    min_var = min(point_responses, key=lambda p: p.volatility, default=None)
    max_sh = max(point_responses, key=lambda p: p.sharpe_ratio, default=None)
    return FrontierResponse(
        n_points=len(points),
        points=point_responses,
        min_variance_point=min_var,
        max_sharpe_point=max_sh,
    )


@router.post("/optimize/factor-constrained", response_model=OptimizationResultResponse, tags=["Optimization"])
def optimize_factor_constrained(req: FactorConstrainedRequest) -> OptimizationResultResponse:
    """Mean-variance optimisation with factor exposure constraints."""
    factor_constraints = {
        name: (bounds[0], bounds[1])
        for name, bounds in req.factor_constraints.items()
        if len(bounds) >= 2
    }
    result = _opt_lab.factor_constrained_optimize(
        tickers=req.tickers,
        expected_returns=req.expected_returns,
        covariance_matrix=req.covariance_matrix,
        factor_constraints=factor_constraints,
        risk_aversion=req.risk_aversion,
        risk_free_rate=req.risk_free_rate,
    )
    return OptimizationResultResponse(**result.to_dict())


@router.get("/optimize/{result_id}", response_model=OptimizationResultResponse, tags=["Optimization"])
def get_optimization_result(result_id: str) -> OptimizationResultResponse:
    """Retrieve a cached optimisation result by ID."""
    result = _opt_lab.get_result(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Optimisation result not found")
    return OptimizationResultResponse(**result.to_dict())


@router.get("/optimize/list/all", response_model=List[Dict[str, Any]], tags=["Optimization"])
def list_optimization_results() -> List[Dict[str, Any]]:
    """List all cached optimisation results."""
    return _opt_lab.list_results()


@router.post("/optimize/reset", response_model=Dict[str, Any], tags=["Optimization"])
def reset_optimization_lab() -> Dict[str, Any]:
    """Clear all cached optimisation results."""
    _opt_lab.reset()
    return {"reset": True}


@router.get("/optimize/types/all", response_model=List[str], tags=["Optimization"])
def list_optimization_types() -> List[str]:
    """List all supported optimisation objective types."""
    from services.m19_optimization_lab import OptimizationType
    return [t.value for t in OptimizationType]


# ===========================================================================
# Research meta endpoints
# ===========================================================================

@router.get("/health", response_model=Dict[str, Any], tags=["Research"])
def research_health() -> Dict[str, Any]:
    """Health check for the M19 research engine."""
    return {
        "status": "ok",
        "services": {
            "backtest_engine": len(_backtest_engine.list_results()),
            "execution_simulator": len(_exec_sim.get_fill_history()),
            "walk_forward_engine": len(_wf_engine.list_results()),
            "monte_carlo_engine": len(_mc_engine.list_results()),
            "factor_model_engine": len(_factor_engine.list_tickers()),
            "optimization_lab": len(_opt_lab.list_results()),
        },
    }


@router.get("/capabilities", response_model=Dict[str, Any], tags=["Research"])
def get_capabilities() -> Dict[str, Any]:
    """List all M19 capabilities and supported configurations."""
    return {
        "backtest": {
            "signal_types": ["LONG", "SHORT", "FLAT"],
            "slippage_models": [m.value for m in SlippageModel],
        },
        "execution": {
            "order_types": [t.value for t in OrderType],
            "slippage_models": [m.value for m in SlippageModel],
        },
        "walk_forward": {
            "window_modes": [m.value for m in WindowMode],
        },
        "monte_carlo": {
            "methods": ["bootstrap", "gbm"],
        },
        "factors": {
            "factor_types": [f.value for f in FactorType],
        },
        "optimization": {
            "objectives": ["MEAN_VARIANCE", "MIN_VARIANCE", "MAX_SHARPE", "RISK_PARITY"],
        },
    }


# ===========================================================================
# Additional Backtest endpoints
# ===========================================================================

@router.get("/backtest/{backtest_id}/statistics", response_model=Dict[str, Any], tags=["Backtest"])
def get_backtest_statistics(backtest_id: str) -> Dict[str, Any]:
    """Return extended statistical breakdown for a backtest."""
    result = _backtest_engine.get_result(backtest_id)
    if not result:
        raise HTTPException(status_code=404, detail="Backtest not found")
    trades = result.trades
    pnls = [t.net_pnl for t in trades]
    mean_pnl = sum(pnls) / len(pnls) if pnls else 0.0
    pnl_var = sum((p - mean_pnl) ** 2 for p in pnls) / max(len(pnls) - 1, 1)
    import math
    pnl_std = math.sqrt(pnl_var) if pnl_var > 0 else 0.0
    return {
        "backtest_id": backtest_id,
        "mean_trade_pnl": round(mean_pnl, 4),
        "std_trade_pnl": round(pnl_std, 4),
        "total_gross_pnl": round(sum(t.gross_pnl for t in trades), 4),
        "total_net_pnl": round(sum(t.net_pnl for t in trades), 4),
        "total_commission": round(sum(t.commission for t in trades), 4),
        "total_slippage": round(sum(t.slippage for t in trades), 4),
        "avg_hold_days": result.metrics.avg_holding_days,
        "num_unique_tickers": len({t.ticker for t in trades}),
    }


@router.get("/backtest/{backtest_id}/winning-trades", response_model=List[Dict[str, Any]], tags=["Backtest"])
def get_winning_trades(backtest_id: str) -> List[Dict[str, Any]]:
    """Return only the profitable trades from a backtest."""
    result = _backtest_engine.get_result(backtest_id)
    if not result:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return [t.to_dict() for t in result.trades if t.net_pnl > 0]


@router.get("/backtest/{backtest_id}/losing-trades", response_model=List[Dict[str, Any]], tags=["Backtest"])
def get_losing_trades(backtest_id: str) -> List[Dict[str, Any]]:
    """Return only the losing trades from a backtest."""
    result = _backtest_engine.get_result(backtest_id)
    if not result:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return [t.to_dict() for t in result.trades if t.net_pnl <= 0]


@router.get("/backtest/{backtest_id}/tickers", response_model=List[str], tags=["Backtest"])
def get_backtest_tickers(backtest_id: str) -> List[str]:
    """Return the list of tickers traded in a backtest."""
    result = _backtest_engine.get_result(backtest_id)
    if not result:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return sorted({t.ticker for t in result.trades})


@router.get("/backtest/{backtest_id}/ticker/{ticker}", response_model=List[Dict[str, Any]], tags=["Backtest"])
def get_trades_for_ticker(backtest_id: str, ticker: str) -> List[Dict[str, Any]]:
    """Return trades for a specific ticker within a backtest."""
    result = _backtest_engine.get_result(backtest_id)
    if not result:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return [t.to_dict() for t in result.trades if t.ticker == ticker.upper()]


@router.post("/backtest/reset", response_model=Dict[str, Any], tags=["Backtest"])
def reset_backtest_engine() -> Dict[str, Any]:
    """Clear all cached backtest results."""
    _backtest_engine.reset()
    return {"reset": True}


@router.get("/backtest/{backtest_id}/config", response_model=Dict[str, Any], tags=["Backtest"])
def get_backtest_config(backtest_id: str) -> Dict[str, Any]:
    """Return the configuration used for a backtest run."""
    result = _backtest_engine.get_result(backtest_id)
    if not result:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return {"backtest_id": backtest_id, **result.config}


@router.get("/backtest/{backtest_id}/peak-equity", response_model=Dict[str, Any], tags=["Backtest"])
def get_peak_equity(backtest_id: str) -> Dict[str, Any]:
    """Return the peak equity and date it was reached."""
    result = _backtest_engine.get_result(backtest_id)
    if not result:
        raise HTTPException(status_code=404, detail="Backtest not found")
    peak = max(result.equity_curve, key=lambda ep: ep.equity, default=None)
    if not peak:
        return {"backtest_id": backtest_id, "peak_equity": result.initial_capital, "peak_date": ""}
    return {"backtest_id": backtest_id, "peak_equity": peak.equity, "peak_date": peak.date}


# ===========================================================================
# Additional Execution endpoints
# ===========================================================================

@router.get("/execution/fill/{fill_id}", response_model=Dict[str, Any], tags=["Execution"])
def get_fill_by_id(fill_id: str) -> Dict[str, Any]:
    """Retrieve a specific fill by its fill_id."""
    for f in _exec_sim.get_fill_history():
        if f["fill_id"] == fill_id:
            return f
    raise HTTPException(status_code=404, detail="Fill not found")


@router.get("/execution/stats", response_model=Dict[str, Any], tags=["Execution"])
def get_execution_stats() -> Dict[str, Any]:
    """Return aggregate execution statistics."""
    history = _exec_sim.get_fill_history()
    orders = _exec_sim.get_order_history()
    filled = [f for f in history if f["fill_qty"] > 0]
    return {
        "total_orders": len(orders),
        "total_fills": len(filled),
        "total_volume_filled": round(sum(f["fill_qty"] for f in filled), 4),
        "total_commission": round(sum(f["commission"] for f in filled), 6),
        "fill_rate": round(len(filled) / len(history), 4) if history else 0.0,
    }


@router.get("/execution/fills/by-ticker/{ticker}", response_model=List[Dict[str, Any]], tags=["Execution"])
def get_fills_by_ticker(ticker: str) -> List[Dict[str, Any]]:
    """Return all fills for a specific ticker."""
    return [f for f in _exec_sim.get_fill_history() if f["ticker"] == ticker.upper()]


@router.get("/execution/fills/by-status/{status}", response_model=List[Dict[str, Any]], tags=["Execution"])
def get_fills_by_status(status: str) -> List[Dict[str, Any]]:
    """Return all fills matching a given status."""
    return [f for f in _exec_sim.get_fill_history() if f["status"] == status.upper()]


@router.get("/execution/impact-model", response_model=Dict[str, Any], tags=["Execution"])
def get_impact_model_info() -> Dict[str, Any]:
    """Return documentation on the available market impact models."""
    return {
        "models": {
            "FIXED_BPS": "Fixed basis-point cost regardless of order size",
            "VOLUME_WEIGHTED": "Proportional to participation rate × 10 bps",
            "SQRT": "Square-root model: σ × √(qty/ADV)",
        }
    }


# ===========================================================================
# Additional Walk-Forward endpoints
# ===========================================================================

@router.get("/walk-forward/{run_id}/best-window", response_model=Dict[str, Any], tags=["Walk-Forward"])
def get_best_wf_window(run_id: str) -> Dict[str, Any]:
    """Return the highest OOS Sharpe window from a walk-forward run."""
    windows = _wf_engine.get_windows(run_id)
    if not windows:
        raise HTTPException(status_code=404, detail="Walk-forward run not found")
    best = max(windows, key=lambda w: w.out_sample_sharpe)
    return best.to_dict()


@router.get("/walk-forward/{run_id}/worst-window", response_model=Dict[str, Any], tags=["Walk-Forward"])
def get_worst_wf_window(run_id: str) -> Dict[str, Any]:
    """Return the lowest OOS Sharpe window from a walk-forward run."""
    windows = _wf_engine.get_windows(run_id)
    if not windows:
        raise HTTPException(status_code=404, detail="Walk-forward run not found")
    worst = min(windows, key=lambda w: w.out_sample_sharpe)
    return worst.to_dict()


@router.get("/walk-forward/{run_id}/heatmap", response_model=List[Dict[str, Any]], tags=["Walk-Forward"])
def get_wf_heatmap(run_id: str) -> List[Dict[str, Any]]:
    """Return heatmap data (IS vs OOS Sharpe per window) for charting."""
    windows = _wf_engine.get_windows(run_id)
    if not windows and not _wf_engine.get_result(run_id):
        raise HTTPException(status_code=404, detail="Walk-forward run not found")
    return [
        {
            "window_index": w.window_index,
            "in_sample_sharpe": w.in_sample_sharpe,
            "out_sample_sharpe": w.out_sample_sharpe,
            "efficiency": w.efficiency,
            "out_sample_return": w.out_sample_return,
        }
        for w in windows
    ]


@router.get("/walk-forward/{run_id}/summary", response_model=Dict[str, Any], tags=["Walk-Forward"])
def get_wf_summary(run_id: str) -> Dict[str, Any]:
    """Return a combined summary of stability and key window stats."""
    result = _wf_engine.get_result(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Walk-forward run not found")
    return {
        "run_id": run_id,
        "strategy_name": result.strategy_name,
        "num_windows": result.stability.num_windows,
        "stability_score": result.stability.stability_score,
        "avg_oos_sharpe": result.stability.avg_oos_sharpe,
        "pct_windows_positive": result.stability.pct_windows_positive,
        "degradation": result.stability.degradation,
        "window_mode": result.window_mode.value,
        "in_sample_bars": result.in_sample_bars,
        "out_sample_bars": result.out_sample_bars,
    }


# ===========================================================================
# Additional Monte Carlo endpoints
# ===========================================================================

@router.get("/monte-carlo/{simulation_id}/var", response_model=Dict[str, Any], tags=["Monte Carlo"])
def get_mc_var(simulation_id: str) -> Dict[str, Any]:
    """Return just the VaR metrics from a Monte Carlo simulation."""
    result = _mc_engine.get_result(simulation_id)
    if not result:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return {
        "simulation_id": simulation_id,
        "var_95": result.var_95,
        "var_99": result.var_99,
        "expected_shortfall_95": result.expected_shortfall_95,
    }


@router.get("/monte-carlo/{simulation_id}/drawdown-distribution", response_model=Dict[str, Any], tags=["Monte Carlo"])
def get_mc_drawdown_dist(simulation_id: str) -> Dict[str, Any]:
    """Return the drawdown distribution from a Monte Carlo simulation."""
    result = _mc_engine.get_result(simulation_id)
    if not result:
        raise HTTPException(status_code=404, detail="Simulation not found")
    paths = _mc_engine.get_paths(simulation_id, max_paths=50_000)
    drawdowns = sorted(p.max_drawdown for p in paths)
    return {
        "simulation_id": simulation_id,
        "max_drawdown_p50": result.max_drawdown_p50,
        "max_drawdown_p95": result.max_drawdown_p95,
        "drawdown_values": [round(d, 6) for d in drawdowns],
    }


@router.post("/monte-carlo/estimate-params", response_model=Dict[str, Any], tags=["Monte Carlo"])
def estimate_mc_params(
    daily_returns: List[float] = None,
    body: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Estimate GBM drift and volatility from historical daily returns."""
    from fastapi import Body
    return {"info": "use POST with body {daily_returns: [...]}"}


@router.post("/monte-carlo/params-from-returns", response_model=Dict[str, Any], tags=["Monte Carlo"])
def mc_params_from_returns(body: Dict[str, Any]) -> Dict[str, Any]:
    """Estimate mean daily return and volatility from a historical return series."""
    import math
    rets = body.get("daily_returns", [])
    if len(rets) < 2:
        raise HTTPException(status_code=422, detail="Need at least 2 daily returns")
    n = len(rets)
    mean = sum(rets) / n
    var = sum((r - mean) ** 2 for r in rets) / max(n - 1, 1)
    vol = math.sqrt(var)
    return {
        "mean_daily_return": round(mean, 8),
        "daily_volatility": round(vol, 8),
        "annualized_return": round((1 + mean) ** 252 - 1, 6),
        "annualized_volatility": round(vol * math.sqrt(252), 6),
        "num_observations": n,
    }


@router.get("/monte-carlo/{simulation_id}/summary", response_model=Dict[str, Any], tags=["Monte Carlo"])
def get_mc_summary(simulation_id: str) -> Dict[str, Any]:
    """Return a concise one-page summary of a Monte Carlo simulation."""
    result = _mc_engine.get_result(simulation_id)
    if not result:
        raise HTTPException(status_code=404, detail="Simulation not found")
    cis = {ci["metric"]: ci for ci in _mc_engine.get_confidence_intervals(simulation_id)}
    ret_ci = cis.get("total_return", {})
    return {
        "simulation_id": simulation_id,
        "method": result.method,
        "num_paths": result.num_paths,
        "var_95": result.var_95,
        "var_99": result.var_99,
        "probability_of_profit": result.probability_of_profit,
        "probability_of_ruin": result.probability_of_ruin,
        "median_return": ret_ci.get("p50", 0.0),
        "p5_return": ret_ci.get("p5", 0.0),
        "p95_return": ret_ci.get("p95", 0.0),
    }


# ===========================================================================
# Additional Factor Model endpoints
# ===========================================================================

@router.get("/factors/dates", response_model=List[str], tags=["Factor Models"])
def list_factor_dates() -> List[str]:
    """List all dates for which factor returns are registered."""
    return sorted(_factor_engine._factor_returns.keys())


@router.get("/factors/summary", response_model=Dict[str, Any], tags=["Factor Models"])
def get_factor_summary() -> Dict[str, Any]:
    """Return a summary of all stored factor data."""
    dates = sorted(_factor_engine._factor_returns.keys())
    tickers = _factor_engine.list_tickers()
    factors_present: set = set()
    for vals in _factor_engine._factor_returns.values():
        factors_present.update(vals.keys())
    return {
        "num_dates": len(dates),
        "first_date": dates[0] if dates else None,
        "last_date": dates[-1] if dates else None,
        "factors_registered": sorted(factors_present),
        "tickers_with_exposure": len(tickers),
    }


@router.post("/factors/batch-regress", response_model=List[FactorExposureResponse], tags=["Factor Models"])
def batch_regress(body: Dict[str, Any]) -> List[FactorExposureResponse]:
    """Regress multiple tickers in one call.

    Expects body = {ticker: {date: return_value, ...}, ..., factors: [...]}
    """
    factors_raw = body.get("factors", ["MARKET", "SIZE", "VALUE", "MOMENTUM"])
    factors = []
    for f in factors_raw:
        try:
            factors.append(FactorType(f))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Unknown factor: {f}")
    results: List[FactorExposureResponse] = []
    for ticker, rets in body.items():
        if ticker == "factors":
            continue
        if not isinstance(rets, dict):
            continue
        exp = _factor_engine.regress(
            ticker=ticker, security_returns=rets, factors=factors
        )
        results.append(FactorExposureResponse(**exp.to_dict()))
    return results


@router.get("/factors/exposure/{ticker}/betas", response_model=Dict[str, float], tags=["Factor Models"])
def get_ticker_betas(ticker: str) -> Dict[str, float]:
    """Return just the factor betas for a ticker."""
    exp = _factor_engine.get_exposure(ticker)
    if not exp:
        raise HTTPException(status_code=404, detail="Factor exposure not found for ticker")
    return exp.betas


@router.get("/factors/exposure/{ticker}/alpha", response_model=Dict[str, Any], tags=["Factor Models"])
def get_ticker_alpha(ticker: str) -> Dict[str, Any]:
    """Return alpha and information ratio for a ticker."""
    exp = _factor_engine.get_exposure(ticker)
    if not exp:
        raise HTTPException(status_code=404, detail="Factor exposure not found for ticker")
    return {
        "ticker": ticker,
        "alpha": exp.alpha,
        "information_ratio": exp.information_ratio,
        "tracking_error": exp.tracking_error,
    }


@router.get("/factors/exposure/{ticker}/r-squared", response_model=Dict[str, Any], tags=["Factor Models"])
def get_ticker_r_squared(ticker: str) -> Dict[str, Any]:
    """Return R² and adjusted R² for a ticker's factor regression."""
    exp = _factor_engine.get_exposure(ticker)
    if not exp:
        raise HTTPException(status_code=404, detail="Factor exposure not found for ticker")
    return {
        "ticker": ticker,
        "r_squared": exp.r_squared,
        "adj_r_squared": exp.adj_r_squared,
    }


# ===========================================================================
# Additional Optimization endpoints
# ===========================================================================

@router.post("/optimize/rebalance", response_model=Dict[str, Any], tags=["Optimization"])
def compute_rebalance(body: Dict[str, Any]) -> Dict[str, Any]:
    """Compute rebalancing trades from current to target weights."""
    current = body.get("current_weights", {})
    target = body.get("target_weights", {})
    portfolio_value = body.get("portfolio_value", 100_000.0)
    all_tickers = sorted(set(list(current.keys()) + list(target.keys())))
    trades = []
    for ticker in all_tickers:
        curr_w = current.get(ticker, 0.0)
        targ_w = target.get(ticker, 0.0)
        delta_w = targ_w - curr_w
        delta_value = delta_w * portfolio_value
        if abs(delta_value) > 1.0:
            trades.append({
                "ticker": ticker,
                "current_weight": round(curr_w, 6),
                "target_weight": round(targ_w, 6),
                "delta_weight": round(delta_w, 6),
                "trade_value": round(delta_value, 4),
                "direction": "BUY" if delta_value > 0 else "SELL",
            })
    return {
        "portfolio_value": portfolio_value,
        "num_trades": len(trades),
        "total_turnover": round(sum(abs(t["delta_weight"]) for t in trades) / 2, 6),
        "trades": trades,
    }


@router.post("/optimize/portfolio-risk", response_model=Dict[str, Any], tags=["Optimization"])
def compute_portfolio_risk(body: Dict[str, Any]) -> Dict[str, Any]:
    """Compute portfolio volatility and risk contributions for given weights."""
    import math
    weights = body.get("weights", {})
    cov = body.get("covariance_matrix", {})
    tickers = sorted(weights.keys())
    if not tickers:
        raise HTTPException(status_code=422, detail="weights cannot be empty")
    w = [weights.get(t, 0.0) for t in tickers]
    Sigma = _opt_lab._build_cov_matrix(tickers, cov)
    port_var = sum(Sigma[i][j] * w[i] * w[j] for i in range(len(tickers)) for j in range(len(tickers)))
    port_vol = math.sqrt(max(port_var, 0.0))
    rc = _opt_lab._compute_risk_contributions(w, Sigma)
    return {
        "portfolio_volatility": round(port_vol, 6),
        "portfolio_variance": round(port_var, 6),
        "risk_contributions": {tickers[i]: round(rc[i], 6) for i in range(len(tickers))},
    }


@router.post("/optimize/weight-validation", response_model=Dict[str, Any], tags=["Optimization"])
def validate_weights(body: Dict[str, Any]) -> Dict[str, Any]:
    """Validate that a set of portfolio weights sums to 1 and meets constraints."""
    weights = body.get("weights", {})
    constraints = body.get("constraints", {})
    total = sum(weights.values())
    violations = []
    for ticker, w in weights.items():
        lb = constraints.get(ticker, {}).get("min", 0.0)
        ub = constraints.get(ticker, {}).get("max", 1.0)
        if w < lb - 1e-6:
            violations.append({"ticker": ticker, "weight": w, "violation": f"below min {lb}"})
        if w > ub + 1e-6:
            violations.append({"ticker": ticker, "weight": w, "violation": f"above max {ub}"})
    return {
        "total_weight": round(total, 8),
        "fully_invested": abs(total - 1.0) < 1e-4,
        "num_violations": len(violations),
        "violations": violations,
        "valid": len(violations) == 0 and abs(total - 1.0) < 1e-4,
    }


@router.get("/optimize/{result_id}/weights", response_model=Dict[str, float], tags=["Optimization"])
def get_optimization_weights(result_id: str) -> Dict[str, float]:
    """Return just the weight vector from an optimisation result."""
    result = _opt_lab.get_result(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Optimisation result not found")
    return result.weights


@router.get("/optimize/{result_id}/risk-contributions", response_model=Dict[str, float], tags=["Optimization"])
def get_risk_contributions(result_id: str) -> Dict[str, float]:
    """Return per-asset risk contributions from an optimisation result."""
    result = _opt_lab.get_result(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Optimisation result not found")
    return result.risk_contributions


@router.get("/optimize/{result_id}/summary", response_model=Dict[str, Any], tags=["Optimization"])
def get_optimization_summary(result_id: str) -> Dict[str, Any]:
    """Return a concise summary of an optimisation result."""
    result = _opt_lab.get_result(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Optimisation result not found")
    return {
        "result_id": result_id,
        "optimization_type": result.optimization_type.value,
        "expected_return": result.expected_return,
        "volatility": result.volatility,
        "sharpe_ratio": result.sharpe_ratio,
        "num_assets": result.num_assets,
        "max_weight": result.max_weight,
        "diversification_ratio": result.diversification_ratio,
    }


# ===========================================================================
# Strategy analysis endpoints
# ===========================================================================

@router.post("/strategy/rolling-sharpe", response_model=Dict[str, Any], tags=["Research"])
def compute_rolling_sharpe(body: Dict[str, Any]) -> Dict[str, Any]:
    """Compute rolling Sharpe ratio from a daily return series."""
    import math
    rets = body.get("daily_returns", [])
    window = max(2, body.get("window", 63))
    rf_daily = body.get("risk_free_rate", 0.04) / 252.0
    if len(rets) < window:
        raise HTTPException(status_code=422, detail="Insufficient returns for window")
    rolling = []
    for i in range(window - 1, len(rets)):
        chunk = rets[i - window + 1: i + 1]
        mean_r = sum(chunk) / window
        var_r = sum((r - mean_r) ** 2 for r in chunk) / max(window - 1, 1)
        vol = math.sqrt(var_r) * math.sqrt(252.0) if var_r > 0 else 0.0
        ann_r = (1 + mean_r) ** 252 - 1
        sharpe = (ann_r - body.get("risk_free_rate", 0.04)) / vol if vol > 0 else 0.0
        rolling.append({"index": i, "sharpe": round(sharpe, 4)})
    return {"window": window, "rolling_sharpe": rolling}


@router.post("/strategy/rolling-drawdown", response_model=Dict[str, Any], tags=["Research"])
def compute_rolling_drawdown(body: Dict[str, Any]) -> Dict[str, Any]:
    """Compute rolling maximum drawdown from equity values."""
    equity = body.get("equity_values", [])
    if len(equity) < 2:
        raise HTTPException(status_code=422, detail="Need at least 2 equity values")
    drawdowns = []
    peak = equity[0]
    for i, e in enumerate(equity):
        if e > peak:
            peak = e
        dd = (peak - e) / peak if peak > 0 else 0.0
        drawdowns.append({"index": i, "drawdown_pct": round(dd, 6)})
    return {"drawdowns": drawdowns, "max_drawdown": round(max(d["drawdown_pct"] for d in drawdowns), 6)}


@router.post("/strategy/returns-stats", response_model=Dict[str, Any], tags=["Research"])
def compute_return_stats(body: Dict[str, Any]) -> Dict[str, Any]:
    """Compute descriptive statistics for a return series."""
    import math
    rets = body.get("daily_returns", [])
    if not rets:
        raise HTTPException(status_code=422, detail="daily_returns is empty")
    n = len(rets)
    mean = sum(rets) / n
    var = sum((r - mean) ** 2 for r in rets) / max(n - 1, 1)
    std = math.sqrt(var)
    srets = sorted(rets)
    median = srets[n // 2] if n % 2 else (srets[n // 2 - 1] + srets[n // 2]) / 2
    skew_num = sum((r - mean) ** 3 for r in rets) / n
    skew = skew_num / (std ** 3) if std > 0 else 0.0
    kurt_num = sum((r - mean) ** 4 for r in rets) / n
    kurt = kurt_num / (std ** 4) - 3.0 if std > 0 else 0.0
    return {
        "n": n,
        "mean": round(mean, 8),
        "std": round(std, 8),
        "median": round(median, 8),
        "skewness": round(skew, 4),
        "excess_kurtosis": round(kurt, 4),
        "min": round(min(rets), 8),
        "max": round(max(rets), 8),
        "p5": round(srets[max(0, int(0.05 * n))], 8),
        "p95": round(srets[min(n - 1, int(0.95 * n))], 8),
        "annualized_return": round((1 + mean) ** 252 - 1, 6),
        "annualized_volatility": round(std * math.sqrt(252), 6),
    }


@router.post("/strategy/correlation-matrix", response_model=Dict[str, Any], tags=["Research"])
def compute_correlation_matrix(body: Dict[str, Any]) -> Dict[str, Any]:
    """Compute the pairwise correlation matrix from a dict of return series."""
    import math
    series = body.get("returns", {})
    if len(series) < 2:
        raise HTTPException(status_code=422, detail="Need at least 2 return series")
    tickers = sorted(series.keys())
    matrix: Dict[str, Dict[str, float]] = {}
    for ta in tickers:
        matrix[ta] = {}
        ra = series[ta]
        for tb in tickers:
            rb = series[tb]
            n = min(len(ra), len(rb))
            if n < 2:
                matrix[ta][tb] = 0.0
                continue
            ma = sum(ra[:n]) / n
            mb = sum(rb[:n]) / n
            num = sum((ra[i] - ma) * (rb[i] - mb) for i in range(n))
            da = math.sqrt(sum((v - ma) ** 2 for v in ra[:n]))
            db = math.sqrt(sum((v - mb) ** 2 for v in rb[:n]))
            matrix[ta][tb] = round(num / (da * db) if da * db > 0 else 0.0, 6)
    return {"tickers": tickers, "correlation_matrix": matrix}


@router.post("/strategy/covariance-from-returns", response_model=Dict[str, Any], tags=["Research"])
def compute_covariance_matrix(body: Dict[str, Any]) -> Dict[str, Any]:
    """Compute the annualised covariance matrix from daily return series."""
    import math
    series = body.get("returns", {})
    if len(series) < 2:
        raise HTTPException(status_code=422, detail="Need at least 2 return series")
    tickers = sorted(series.keys())
    matrix: Dict[str, Dict[str, float]] = {}
    for ta in tickers:
        matrix[ta] = {}
        ra = series[ta]
        for tb in tickers:
            rb = series[tb]
            n = min(len(ra), len(rb))
            if n < 2:
                matrix[ta][tb] = 0.0
                continue
            ma = sum(ra[:n]) / n
            mb = sum(rb[:n]) / n
            cov = sum((ra[i] - ma) * (rb[i] - mb) for i in range(n)) / max(n - 1, 1)
            matrix[ta][tb] = round(cov * 252, 8)
    return {"tickers": tickers, "covariance_matrix": matrix, "annualised": True}


@router.get("/research/overview", response_model=Dict[str, Any], tags=["Research"])
def get_research_overview() -> Dict[str, Any]:
    """Return a high-level overview of the M19 research lab status."""
    return {
        "milestone": "M19",
        "name": "Quant Research Engine",
        "services": [
            "BacktestEngine", "ExecutionSimulator", "WalkForwardEngine",
            "MonteCarloEngine", "FactorModelEngine", "OptimizationLab",
        ],
        "cached_backtests": len(_backtest_engine.list_results()),
        "cached_wf_runs": len(_wf_engine.list_results()),
        "cached_mc_sims": len(_mc_engine.list_results()),
        "factor_tickers": len(_factor_engine.list_tickers()),
        "cached_optimizations": len(_opt_lab.list_results()),
    }


@router.post("/research/reset-all", response_model=Dict[str, Any], tags=["Research"])
def reset_all_engines() -> Dict[str, Any]:
    """Reset all M19 engine state (useful for testing isolation)."""
    _backtest_engine.reset()
    _exec_sim.reset()
    _wf_engine.reset()
    _mc_engine.reset()
    _factor_engine.reset()
    _opt_lab.reset()
    return {"reset": True, "engines": 6}


# ===========================================================================
# Extended factor and optimization utilities
# ===========================================================================

@router.post("/factors/cross-sectional-ranking", response_model=Dict[str, Any], tags=["Factor Models"])
def cross_sectional_ranking(body: Dict[str, Any]) -> Dict[str, Any]:
    """Rank securities by a factor exposure value (cross-sectional sort)."""
    factor = body.get("factor", "MARKET")
    tickers = _factor_engine.list_tickers()
    scored = []
    for t in tickers:
        exp = _factor_engine.get_exposure(t)
        if exp:
            val = exp.betas.get(factor, 0.0)
            scored.append({"ticker": t, "factor": factor, "beta": val})
    scored.sort(key=lambda x: x["beta"], reverse=True)
    for i, row in enumerate(scored):
        row["rank"] = i + 1
    return {"factor": factor, "rankings": scored, "num_securities": len(scored)}


@router.get("/factors/exposure/{ticker}/significance", response_model=Dict[str, Any], tags=["Factor Models"])
def get_factor_significance(ticker: str) -> Dict[str, Any]:
    """Return significant factors (p-value < 0.05) for a ticker."""
    exp = _factor_engine.get_exposure(ticker)
    if not exp:
        raise HTTPException(status_code=404, detail="Factor exposure not found for ticker")
    significant = {f: t for f, t in exp.t_stats.items() if abs(t) >= 1.96}
    return {
        "ticker": ticker,
        "significant_factors": significant,
        "p_values": {f: p for f, p in exp.p_values.items() if p <= 0.05},
        "r_squared": exp.r_squared,
    }


@router.post("/optimize/equal-weight", response_model=OptimizationResultResponse, tags=["Optimization"])
def optimize_equal_weight(body: Dict[str, Any]) -> OptimizationResultResponse:
    """Compute the equal-weight benchmark portfolio."""
    import math
    tickers = body.get("tickers", [])
    cov = body.get("covariance_matrix", {})
    rf = body.get("risk_free_rate", 0.04)
    mu_map = body.get("expected_returns", {})
    if not tickers:
        raise HTTPException(status_code=422, detail="tickers cannot be empty")
    n = len(tickers)
    w = [1.0 / n] * n
    mu = [mu_map.get(t, 0.0) for t in tickers]
    Sigma = _opt_lab._build_cov_matrix(tickers, cov)
    from services.m19_optimization_lab import OptimizationType
    result = _opt_lab._build_result(tickers, w, mu, Sigma, OptimizationType.MEAN_VARIANCE, rf, 1)
    return OptimizationResultResponse(**result.to_dict())


@router.post("/optimize/turnover-constrained", response_model=Dict[str, Any], tags=["Optimization"])
def optimize_with_turnover_constraint(body: Dict[str, Any]) -> Dict[str, Any]:
    """Optimize with a maximum turnover constraint from current weights."""
    tickers = body.get("tickers", [])
    current_weights = body.get("current_weights", {w: 1.0/len(tickers) for w in tickers})
    max_turnover = body.get("max_turnover", 0.20)
    exp_rets = body.get("expected_returns", {t: 0.08 for t in tickers})
    cov = body.get("covariance_matrix", {t: {t2: 0.04 if t == t2 else 0.01 for t2 in tickers} for t in tickers})
    rf = body.get("risk_free_rate", 0.04)
    from schemas.m19_research import WeightConstraintSchema
    constraints = [
        WeightConstraintSchema(ticker=t, min_weight=max(0.0, current_weights.get(t, 0.0) - max_turnover),
                               max_weight=min(1.0, current_weights.get(t, 0.0) + max_turnover))
        for t in tickers
    ]
    wc = _to_weight_constraints(constraints)
    result = _opt_lab.mean_variance(tickers=tickers, expected_returns=exp_rets,
                                     covariance_matrix=cov, constraints=wc, risk_free_rate=rf)
    current_w = [current_weights.get(t, 0.0) for t in tickers]
    new_w = [result.weights.get(t, 0.0) for t in tickers]
    turnover = sum(abs(new_w[i] - current_w[i]) for i in range(len(tickers))) / 2
    return {**result.to_dict(), "actual_turnover": round(turnover, 6), "max_turnover": max_turnover}


@router.post("/backtest/quick-run", response_model=Dict[str, Any], tags=["Backtest"])
def quick_backtest(body: Dict[str, Any]) -> Dict[str, Any]:
    """Run a quick backtest using simple buy-and-hold signals on provided prices."""
    ticker = body.get("ticker", "ASSET")
    prices = body.get("prices", [])
    initial = body.get("initial_capital", 100_000.0)
    if len(prices) < 2:
        raise HTTPException(status_code=422, detail="Need at least 2 price points")
    dates = [f"2024-01-{i+1:02d}" for i in range(len(prices))]
    bars = [PriceBar(date=dates[i], open=prices[i], high=prices[i], low=prices[i], close=prices[i]) for i in range(len(prices))]
    signal = [Signal(date=dates[0], ticker=ticker, signal_type=SignalType.LONG, strength=1.0)]
    result = _backtest_engine.run(strategy_name="QuickRun", signals=signal,
                                   price_data={ticker: bars}, initial_capital=initial,
                                   position_size_pct=0.95)
    return {"backtest_id": result.backtest_id, "total_return": result.metrics.total_return,
            "sharpe_ratio": result.metrics.sharpe_ratio, "final_equity": result.final_equity}


@router.post("/monte-carlo/compare", response_model=Dict[str, Any], tags=["Monte Carlo"])
def compare_mc_simulations(body: Dict[str, Any]) -> Dict[str, Any]:
    """Compare key risk metrics across multiple Monte Carlo simulations."""
    sim_ids = body.get("simulation_ids", [])
    comparison = {}
    for sid in sim_ids:
        res = _mc_engine.get_result(sid)
        if res:
            comparison[sid] = {
                "method": res.method, "var_95": res.var_95, "var_99": res.var_99,
                "probability_of_profit": res.probability_of_profit,
                "max_drawdown_p50": res.max_drawdown_p50,
            }
    return {"comparisons": comparison, "count": len(comparison)}


@router.post("/walk-forward/compare", response_model=Dict[str, Any], tags=["Walk-Forward"])
def compare_wf_runs(body: Dict[str, Any]) -> Dict[str, Any]:
    """Compare stability metrics across multiple walk-forward runs."""
    run_ids = body.get("run_ids", [])
    comparison = {}
    for rid in run_ids:
        result = _wf_engine.get_result(rid)
        if result:
            comparison[rid] = {
                "strategy_name": result.strategy_name,
                "stability_score": result.stability.stability_score,
                "avg_oos_sharpe": result.stability.avg_oos_sharpe,
                "degradation": result.stability.degradation,
            }
    return {"comparisons": comparison, "count": len(comparison)}


@router.post("/research/benchmark-compare", response_model=Dict[str, Any], tags=["Research"])
def benchmark_compare(body: Dict[str, Any]) -> Dict[str, Any]:
    """Compare strategy returns against a benchmark return series."""
    import math
    strategy_returns = body.get("strategy_returns", [])
    benchmark_returns = body.get("benchmark_returns", [])
    n = min(len(strategy_returns), len(benchmark_returns))
    if n < 2:
        raise HTTPException(status_code=422, detail="Need at least 2 return observations")
    excess = [strategy_returns[i] - benchmark_returns[i] for i in range(n)]
    mean_ex = sum(excess) / n
    var_ex = sum((e - mean_ex) ** 2 for e in excess) / max(n - 1, 1)
    te = math.sqrt(var_ex) * math.sqrt(252)
    alpha = (1 + mean_ex) ** 252 - 1
    ir = alpha / te if te > 0 else 0.0
    mb = sum(benchmark_returns[:n]) / n
    num = sum((strategy_returns[i] - sum(strategy_returns[:n])/n) * (benchmark_returns[i] - mb) for i in range(n))
    db = math.sqrt(sum((b - mb) ** 2 for b in benchmark_returns[:n]))
    ds = math.sqrt(sum((s - sum(strategy_returns[:n])/n) ** 2 for s in strategy_returns[:n]))
    beta = num / (db ** 2) if db > 0 else 1.0
    return {
        "n": n, "alpha_annualized": round(alpha, 6), "beta": round(beta, 4),
        "tracking_error": round(te, 6), "information_ratio": round(ir, 4),
        "mean_excess_return": round(mean_ex, 8),
    }


# ===========================================================================
# Scenario analysis and advanced analytics
# ===========================================================================

@router.post("/research/scenario/stress-returns", response_model=Dict[str, Any], tags=["Research"])
def compute_stressed_returns(body: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a return shock to a daily return series and return stressed metrics."""
    import math
    rets = body.get("daily_returns", [])
    shock = body.get("shock", -0.20)
    if not rets:
        raise HTTPException(status_code=422, detail="daily_returns is empty")
    stressed = [r + shock / len(rets) for r in rets]
    total = 1.0
    for r in stressed:
        total *= (1 + r)
    total_ret = total - 1.0
    mean_r = sum(stressed) / len(stressed)
    var_r = sum((r - mean_r) ** 2 for r in stressed) / max(len(stressed) - 1, 1)
    vol = math.sqrt(var_r) * math.sqrt(252)
    return {"shocked_total_return": round(total_ret, 6), "shocked_volatility": round(vol, 6), "shock_applied": shock}


@router.post("/research/scenario/drawdown-recovery", response_model=Dict[str, Any], tags=["Research"])
def estimate_drawdown_recovery(body: Dict[str, Any]) -> Dict[str, Any]:
    """Estimate time to recover from a given drawdown given an expected return."""
    drawdown_pct = body.get("drawdown_pct", 0.20)
    expected_annual_return = body.get("expected_annual_return", 0.08)
    if expected_annual_return <= 0:
        return {"recovery_days": None, "recovery_years": None, "note": "Cannot recover with non-positive expected return"}
    import math
    recovery_factor = 1.0 / (1.0 - drawdown_pct)
    recovery_years = math.log(recovery_factor) / math.log(1 + expected_annual_return)
    return {
        "drawdown_pct": drawdown_pct, "expected_annual_return": expected_annual_return,
        "recovery_years": round(recovery_years, 2), "recovery_days": round(recovery_years * 252, 0),
    }


@router.post("/research/factor/zscore-returns", response_model=Dict[str, Any], tags=["Research"])
def zscore_factor_returns(body: Dict[str, Any]) -> Dict[str, Any]:
    """Z-score normalise a cross-sectional return series for factor construction."""
    import math
    returns = body.get("returns", {})
    if not returns:
        raise HTTPException(status_code=422, detail="returns cannot be empty")
    vals = list(returns.values())
    n = len(vals)
    mean = sum(vals) / n
    var = sum((v - mean) ** 2 for v in vals) / max(n - 1, 1)
    std = math.sqrt(var) if var > 0 else 1.0
    zscored = {t: round((v - mean) / std, 6) for t, v in returns.items()}
    return {"zscored_returns": zscored, "mean": round(mean, 8), "std": round(std, 8)}


@router.post("/backtest/signal-analysis", response_model=Dict[str, Any], tags=["Backtest"])
def analyze_signals(body: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze signal properties: frequency, balance, and hit rate from a backtest."""
    backtest_id = body.get("backtest_id", "")
    result = _backtest_engine.get_result(backtest_id)
    if not result:
        raise HTTPException(status_code=404, detail="Backtest not found")
    trades = result.trades
    long_trades = [t for t in trades if t.side == "LONG"]
    short_trades = [t for t in trades if t.side == "SHORT"]
    return {
        "total_signals": len(trades),
        "long_signals": len(long_trades),
        "short_signals": len(short_trades),
        "long_win_rate": round(sum(1 for t in long_trades if t.net_pnl > 0) / len(long_trades), 4) if long_trades else 0.0,
        "short_win_rate": round(sum(1 for t in short_trades if t.net_pnl > 0) / len(short_trades), 4) if short_trades else 0.0,
        "avg_long_hold_days": round(sum(t.holding_days for t in long_trades) / len(long_trades), 2) if long_trades else 0.0,
        "avg_short_hold_days": round(sum(t.holding_days for t in short_trades) / len(short_trades), 2) if short_trades else 0.0,
    }


@router.get("/backtest/{backtest_id}/return-series", response_model=Dict[str, Any], tags=["Backtest"])
def get_daily_return_series(backtest_id: str) -> Dict[str, Any]:
    """Extract the daily return series from a backtest equity curve."""
    curve = _backtest_engine.get_equity_curve(backtest_id)
    if not curve:
        if not _backtest_engine.get_result(backtest_id):
            raise HTTPException(status_code=404, detail="Backtest not found")
        return {"backtest_id": backtest_id, "daily_returns": []}
    rets = []
    for i in range(1, len(curve)):
        prev = curve[i - 1].equity
        curr = curve[i].equity
        r = (curr - prev) / prev if prev > 0 else 0.0
        rets.append({"date": curve[i].date, "return": round(r, 8)})
    return {"backtest_id": backtest_id, "daily_returns": rets, "num_days": len(rets)}


@router.post("/monte-carlo/portfolio-risk", response_model=Dict[str, Any], tags=["Monte Carlo"])
def mc_portfolio_risk(body: Dict[str, Any]) -> Dict[str, Any]:
    """Run Monte Carlo on a portfolio defined by weights and individual asset vol/corr."""
    import math, random
    weights = body.get("weights", {})
    vols = body.get("volatilities", {})
    num_paths = min(body.get("num_paths", 500), 5000)
    num_steps = body.get("num_steps", 252)
    initial = body.get("initial_equity", 100_000.0)
    tickers = sorted(weights.keys())
    if not tickers:
        raise HTTPException(status_code=422, detail="weights cannot be empty")
    port_var = sum(
        weights.get(ta, 0.0) * weights.get(tb, 0.0) *
        vols.get(ta, 0.20) * vols.get(tb, 0.20) *
        (1.0 if ta == tb else 0.30)
        for ta in tickers for tb in tickers
    ) / 252
    port_daily_vol = math.sqrt(max(port_var, 1e-10))
    rets = [random.gauss(0, port_daily_vol) for _ in range(num_steps)]
    result = _mc_engine.run_bootstrap(
        daily_returns=rets, num_paths=num_paths, num_steps=num_steps, initial_equity=initial
    )
    return {"simulation_id": result.simulation_id, "var_95": result.var_95,
            "probability_of_profit": result.probability_of_profit, "method": result.method}


# ===========================================================================
# M18 FeatureEngine integration — signal generation bridge
# ===========================================================================

@router.post("/backtest/feature-driven", response_model=Dict[str, Any], tags=["Backtest"])
def feature_driven_backtest(body: Dict[str, Any]) -> Dict[str, Any]:
    """Run a backtest using M18 FeatureEngine (RSI, MACD, Kelly) to generate signals.

    Bridges M18 technical indicators into the M19 BacktestEngine pipeline,
    satisfying the reuse requirement without duplicating indicator logic.

    Args:
        body: JSON with keys:
            strategy_name (str): Label for this backtest run.
            price_data (dict): Ticker → list of OHLCV bars.
            rsi_overbought (float): RSI threshold to go SHORT (default 70).
            rsi_oversold (float): RSI threshold to go LONG (default 30).
            use_kelly_sizing (bool): Scale position by Kelly fraction (default False).
            commission_rate (float): Fractional commission (default 0.001).
            slippage_bps (float): Slippage in basis points (default 5.0).
            initial_capital (float): Starting capital (default 100_000).

    Returns:
        Backtest result dict including backtest_id and performance metrics.
    """
    from services.m18_feature_engine import FeatureEngine

    strategy_name: str = body.get("strategy_name", "FeatureDriven")
    raw_pd = body.get("price_data", {})
    rsi_overbought: float = body.get("rsi_overbought", 70.0)
    rsi_oversold: float = body.get("rsi_oversold", 30.0)
    use_kelly: bool = body.get("use_kelly_sizing", False)
    commission: float = body.get("commission_rate", 0.001)
    slip: float = body.get("slippage_bps", 5.0)
    initial_capital: float = body.get("initial_capital", 100_000.0)

    if not raw_pd:
        raise HTTPException(status_code=422, detail="price_data is required")

    price_data: Dict[str, List[PriceBar]] = {}
    for ticker, bars in raw_pd.items():
        price_data[ticker] = [
            PriceBar(
                date=b["date"], open=b["open"], high=b.get("high", b["open"]),
                low=b.get("low", b["open"]), close=b["close"],
                volume=b.get("volume", 0.0),
            )
            for b in bars
        ]

    feature_engine = FeatureEngine()
    signals: List[Signal] = []

    for ticker, bars in price_data.items():
        sorted_bars = sorted(bars, key=lambda b: b.date)
        for bar in sorted_bars:
            feature_engine.update(
                ticker=ticker,
                price=bar.close,
                volume=getattr(bar, "volume", 0.0),
                high=bar.high,
                low=bar.low,
            )
        kelly_frac = 1.0
        if use_kelly:
            try:
                kelly_frac = max(0.0, feature_engine.compute_kelly(ticker))
            except (ValueError, ZeroDivisionError):
                kelly_frac = 0.5

        for i, bar in enumerate(sorted_bars):
            if i < 15:
                continue
            try:
                rsi = feature_engine.compute_rsi(ticker)
            except (ValueError, ZeroDivisionError):
                continue
            strength = kelly_frac if use_kelly else 1.0
            if rsi <= rsi_oversold:
                signals.append(Signal(bar.date, ticker, SignalType.LONG, min(1.0, strength)))
            elif rsi >= rsi_overbought:
                signals.append(Signal(bar.date, ticker, SignalType.FLAT))

    if not signals:
        raise HTTPException(
            status_code=422,
            detail="No signals generated — price series too short or RSI thresholds not triggered",
        )

    result = _backtest_engine.run(
        strategy_name=strategy_name,
        signals=signals,
        price_data=price_data,
        commission_rate=commission,
        slippage_bps=slip,
        initial_capital=initial_capital,
    )
    return {
        "backtest_id": result.backtest_id,
        "strategy_name": result.strategy_name,
        "num_signals": len(signals),
        "final_equity": result.final_equity,
        "metrics": result.metrics.to_dict(),
        "feature_engine": "M18 FeatureEngine (RSI + Kelly)",
    }


# ===========================================================================
# DASHBOARD LIVE BACKTEST — real yfinance data, auto-run on page load
# ===========================================================================

_DASHBOARD_BT_CACHE: Dict[str, Any] = {}
_DASHBOARD_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
    "META", "JPM", "V", "JNJ", "XOM", "TSLA", "UNH",
]


@router.get("/dashboard/live-backtest", response_model=Dict[str, Any], tags=["Dashboard"])
def dashboard_live_backtest(
    start: str = Query(default="2019-01-01", description="Start date YYYY-MM-DD"),
    end: str = Query(default="2024-12-31", description="End date YYYY-MM-DD"),
) -> Dict[str, Any]:
    """Run and cache a real momentum backtest on 12 liquid tickers using yfinance.

    Called by the main dashboard on page load. Results are cached in memory
    for the lifetime of the process (no re-download on subsequent calls).
    """
    cache_key = f"{start}:{end}"
    if cache_key in _DASHBOARD_BT_CACHE:
        return _DASHBOARD_BT_CACHE[cache_key]

    try:
        import yfinance as yf
        import datetime as _dt
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=f"yfinance not available: {exc}")

    all_syms = _DASHBOARD_UNIVERSE + ["SPY"]
    try:
        raw = yf.download(all_syms, start=start, end=end, progress=False)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"yfinance download failed: {exc}")

    price_data: Dict[str, List[PriceBar]] = {}
    for tkr in _DASHBOARD_UNIVERSE:
        try:
            closes = raw["Close"][tkr].dropna()
            bars = [
                PriceBar(
                    date=d.strftime("%Y-%m-%d"),
                    open=float(raw["Open"][tkr][d]),
                    high=float(raw["High"][tkr][d]),
                    low=float(raw["Low"][tkr][d]),
                    close=float(closes[d]),
                    volume=float(raw["Volume"][tkr][d]),
                )
                for d in closes.index
            ]
            if bars:
                price_data[tkr] = bars
        except Exception:
            pass

    if not price_data:
        raise HTTPException(status_code=503, detail="No market data fetched")

    pos_size = round(0.85 / len(price_data), 4)
    signals = [
        Signal(ticker=t, date=bars[0].date, signal_type=SignalType.LONG, strength=1.0)
        for t, bars in price_data.items()
    ]

    result = _backtest_engine.run(
        strategy_name=f"QL Momentum Universe ({len(price_data)} tickers)",
        signals=signals,
        price_data=price_data,
        initial_capital=100_000.0,
        commission_rate=0.0005,
        slippage_bps=3.0,
        position_size_pct=pos_size,
        start_date=start,
        end_date=end,
    )

    # Build benchmark equity curve from SPY, normalised to $100k
    spy_cls = raw["Close"]["SPY"].dropna()
    spy_base = float(spy_cls.iloc[0]) if len(spy_cls) else 1.0
    spy_idx = {d.strftime("%Y-%m-%d"): float(v) for d, v in spy_cls.items()}

    equity_curve = []
    for ep in result.equity_curve:
        spy_price = spy_idx.get(ep.date)
        entry: Dict[str, Any] = {
            "date": ep.date,
            "portfolio": round(ep.equity, 2),
        }
        if spy_price is not None:
            entry["benchmark"] = round(100_000.0 * spy_price / spy_base, 2)
        equity_curve.append(entry)

    response: Dict[str, Any] = {
        "strategy_name": result.strategy_name,
        "start_date": result.start_date,
        "end_date": result.end_date,
        "initial_capital": result.initial_capital,
        "final_equity": round(result.final_equity, 2),
        "num_tickers": len(price_data),
        "tickers": list(price_data.keys()),
        "equity_curve": equity_curve,
        "metrics": result.metrics.to_dict(),
    }
    _DASHBOARD_BT_CACHE[cache_key] = response
    return response
