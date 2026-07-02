"""M9 Phase 3/4 — Options strategy builder API."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from services.options_strategies import build_strategy, list_strategies, binomial_tree, bs_greeks

router = APIRouter(prefix="/options/strategies", tags=["options_strategies"])


class StrategyRequest(BaseModel):
    strategy: str
    spot: float
    strike: float
    expiry_T: float       # years to expiry
    risk_free_rate: float = 0.05
    volatility: float = 0.20
    strike2: Optional[float] = None
    strike_put: Optional[float] = None


@router.get("/list")
def get_strategies():
    return {"strategies": list_strategies()}


@router.post("/build")
def build(req: StrategyRequest):
    try:
        result = build_strategy(
            req.strategy, req.spot, req.strike, req.expiry_T,
            req.risk_free_rate, req.volatility,
            K2=req.strike2, K_put=req.strike_put,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return result


class BinomialRequest(BaseModel):
    spot: float
    strike: float
    expiry_T: float
    risk_free_rate: float = 0.05
    volatility: float = 0.20
    option_type: str = "call"
    american: bool = False
    steps: int = 100


@router.post("/binomial")
def binomial_price(req: BinomialRequest):
    price = binomial_tree(
        req.spot, req.strike, req.expiry_T, req.risk_free_rate,
        req.volatility, req.option_type, req.american, req.steps,
    )
    greeks = bs_greeks(req.spot, req.strike, req.expiry_T, req.risk_free_rate, req.volatility, req.option_type)
    return {"price": price, "greeks": greeks, "model": "binomial_crr", "american": req.american}
