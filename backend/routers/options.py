"""Options Analytics router (M7) — Black-Scholes, Greeks, IV surface, max pain."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter

import services.options_analytics as svc
from schemas.options import (
    BlackScholesRequest,
    BlackScholesResponse,
    ExpectedMoveRequest,
    ExpectedMoveResponse,
    IVRequest,
    IVResponse,
    IVSurfaceRequest,
    IVSurfaceResponse,
    MaxPainRequest,
    MaxPainResponse,
    OptionsChainRequest,
    OptionsChainResponse,
    VolatilitySkewRequest,
    VolatilitySkewResponse,
)

router = APIRouter(prefix="/options", tags=["Options Analytics"])


@router.post("/price", response_model=Dict[str, Any])
def price_option(req: BlackScholesRequest):
    """Calculate theoretical option price and Greeks."""
    price = svc.black_scholes_price(req.S, req.K, req.T, req.sigma, req.option_type, req.r)
    greeks = svc.calculate_greeks(req.S, req.K, req.T, req.sigma, req.option_type, req.r)
    return {
        "price": round(price, 6),
        "greeks": greeks,
        "option_type": req.option_type,
        "S": req.S,
        "K": req.K,
        "T": req.T,
        "sigma": req.sigma,
    }


@router.post("/implied-vol", response_model=Dict[str, Any])
def get_implied_vol(req: IVRequest):
    """Calculate implied volatility from market price."""
    iv = svc.implied_volatility(req.market_price, req.S, req.K, req.T, req.option_type, req.r)
    return {
        "implied_vol": iv,
        "market_price": req.market_price,
        "S": req.S,
        "K": req.K,
        "T": req.T,
        "option_type": req.option_type,
    }


@router.post("/chain", response_model=Dict[str, Any])
def get_options_chain(req: OptionsChainRequest):
    """Return a full options chain for a ticker."""
    return svc.options_chain(
        ticker=req.ticker,
        underlying_price=req.underlying_price,
        strikes=req.strikes,
        expiry_days_list=req.expiry_days_list,
        r=req.r,
    )


@router.post("/iv-surface", response_model=Dict[str, Any])
def get_iv_surface(req: IVSurfaceRequest):
    """Return implied volatility surface across strikes and expiries."""
    return svc.iv_surface(
        ticker=req.ticker,
        underlying_price=req.underlying_price,
        strike_pcts=req.strike_pcts,
        expiry_days_list=req.expiry_days_list,
    )


@router.post("/max-pain", response_model=Dict[str, Any])
def get_max_pain(req: MaxPainRequest):
    """Calculate max pain strike for an options chain."""
    return svc.max_pain(req.strikes, req.calls_oi, req.puts_oi)


@router.post("/expected-move", response_model=Dict[str, Any])
def get_expected_move(req: ExpectedMoveRequest):
    """Calculate expected move (1σ and 2σ) for a given expiry."""
    return svc.expected_move(req.underlying_price, req.atm_iv, req.expiry_days)


@router.post("/gamma-exposure", response_model=Dict[str, Any])
def get_gamma_exposure(body: Dict[str, Any]):
    """Calculate aggregate gamma exposure (GEX) across the chain."""
    chain = body.get("chain", [])
    underlying_price = body.get("underlying_price", 100.0)
    return svc.gamma_exposure(chain, underlying_price)


@router.post("/skew", response_model=Dict[str, Any])
def get_volatility_skew(req: VolatilitySkewRequest):
    """Return volatility skew metrics: 25Δ risk reversal and skew slope."""
    return svc.volatility_skew(req.underlying_price, req.atm_iv, req.expiry_days, req.r)


@router.get("/ticker/{ticker}", response_model=Dict[str, Any])
def get_ticker_options_summary(
    ticker: str,
    underlying_price: float = 150.0,
    atm_iv: float = 0.25,
):
    """Return a comprehensive options summary for a ticker."""
    chain_data = svc.options_chain(ticker, underlying_price)
    surface = svc.iv_surface(ticker, underlying_price)
    exp_move = svc.expected_move(underlying_price, atm_iv, 30)
    skew = svc.volatility_skew(underlying_price, atm_iv)
    gex = svc.gamma_exposure(chain_data["chain"], underlying_price)

    return {
        "ticker": ticker,
        "underlying_price": underlying_price,
        "atm_iv": atm_iv,
        "expected_move_30d": exp_move,
        "volatility_skew": skew,
        "gamma_exposure": gex,
        "iv_surface": surface,
        "chain_summary": {
            "total_contracts": chain_data["total_contracts"],
            "sample_chain": chain_data["chain"][:10],
        },
    }
