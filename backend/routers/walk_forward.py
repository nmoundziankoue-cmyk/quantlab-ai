"""M9 Phase 5 — Walk-forward backtesting API."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from services.walk_forward import walk_forward_test, parameter_sweep, rolling_optimization, kelly_criterion

router = APIRouter(prefix="/backtest/walkforward", tags=["walk_forward"])


def _sma_crossover(prices: List[float], params: Dict[str, Any]) -> List[float]:
    fast = int(params.get("fast", 10))
    slow = int(params.get("slow", 30))
    if len(prices) < slow + 1:
        return []
    returns = []
    position = 0
    for i in range(slow, len(prices)):
        sma_fast = sum(prices[i - fast:i]) / fast
        sma_slow = sum(prices[i - slow:i]) / slow
        signal = 1 if sma_fast > sma_slow else -1
        if i > slow and len(prices) > i:
            daily_return = (prices[i] - prices[i - 1]) / prices[i - 1]
            returns.append(position * daily_return)
        position = signal
    return returns


class WalkForwardRequest(BaseModel):
    prices: List[float]
    in_sample_size: int = 126
    out_sample_size: int = 21
    fast_window: int = 10
    slow_window: int = 30


class SweepRequest(BaseModel):
    prices: List[float]
    fast_values: List[int] = [5, 10, 20]
    slow_values: List[int] = [20, 30, 50]
    metric: str = "sharpe"


class KellyRequest(BaseModel):
    win_prob: float
    win_return: float
    loss_return: float


@router.post("/run")
def run_walk_forward(req: WalkForwardRequest):
    params = {"fast": req.fast_window, "slow": req.slow_window}
    result = walk_forward_test(req.prices, _sma_crossover, params, req.in_sample_size, req.out_sample_size)
    return {
        "windows": result.windows,
        "aggregate": result.aggregate,
    }


@router.post("/sweep")
def run_sweep(req: SweepRequest):
    grid = {"fast": req.fast_values, "slow": req.slow_values}
    result = parameter_sweep(req.prices, _sma_crossover, grid, req.metric)
    return {
        "best_params": result.best_params,
        "best_metric": result.best_metric,
        "top_5": result.all_results[:5],
    }


@router.post("/kelly")
def kelly(req: KellyRequest):
    return kelly_criterion(req.win_prob, req.win_return, req.loss_return)
