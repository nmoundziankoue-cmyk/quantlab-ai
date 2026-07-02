"""Pydantic v2 schemas for the Options Analytics desk (M7)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class GreeksSchema(BaseModel):
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float


class BlackScholesRequest(BaseModel):
    S: float = Field(..., description="Underlying price")
    K: float = Field(..., description="Strike price")
    T: float = Field(..., description="Time to expiry in years")
    sigma: float = Field(..., description="Implied volatility (annualised)")
    option_type: str = Field("CALL", description="CALL or PUT")
    r: float = Field(0.05, description="Risk-free rate")


class BlackScholesResponse(BaseModel):
    price: float
    greeks: GreeksSchema
    option_type: str
    S: float
    K: float
    T: float
    sigma: float


class IVRequest(BaseModel):
    market_price: float
    S: float
    K: float
    T: float
    option_type: str = "CALL"
    r: float = 0.05


class IVResponse(BaseModel):
    implied_vol: Optional[float]
    market_price: float
    S: float
    K: float
    T: float
    option_type: str


class OptionsChainRequest(BaseModel):
    ticker: str
    underlying_price: float
    strikes: Optional[List[float]] = None
    expiry_days_list: Optional[List[int]] = None
    r: float = 0.05


class OptionsChainItem(BaseModel):
    ticker: str
    option_type: str
    strike: float
    expiry_days: int
    expiry_label: str
    implied_vol: float
    theoretical_price: float
    open_interest: int
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float


class OptionsChainResponse(BaseModel):
    ticker: str
    underlying_price: float
    risk_free_rate: float
    chain: List[OptionsChainItem]
    total_contracts: int


class IVSurfaceRequest(BaseModel):
    ticker: str
    underlying_price: float
    strike_pcts: Optional[List[float]] = None
    expiry_days_list: Optional[List[int]] = None


class IVSurfaceResponse(BaseModel):
    ticker: str
    underlying_price: float
    strikes: List[float]
    strike_pcts: List[float]
    expiry_days: List[int]
    surface: List[List[float]]
    atm_iv: float


class MaxPainRequest(BaseModel):
    strikes: List[float]
    calls_oi: List[int]
    puts_oi: List[int]


class MaxPainResponse(BaseModel):
    max_pain_strike: Optional[float]
    min_pain_value: Optional[float]
    pain_by_strike: List[Dict[str, float]]


class ExpectedMoveRequest(BaseModel):
    underlying_price: float
    atm_iv: float
    expiry_days: int


class ExpectedMoveResponse(BaseModel):
    underlying_price: float
    atm_iv: float
    expiry_days: int
    expected_move_1sigma: float
    upper_bound_1sigma: float
    lower_bound_1sigma: float
    expected_move_2sigma: float
    upper_bound_2sigma: float
    lower_bound_2sigma: float
    pct_move_1sigma: float


class VolatilitySkewRequest(BaseModel):
    underlying_price: float
    atm_iv: float = 0.25
    expiry_days: int = 30
    r: float = 0.05


class VolatilitySkewResponse(BaseModel):
    atm_iv: float
    put_25d_strike: float
    put_25d_iv: float
    call_25d_strike: float
    call_25d_iv: float
    risk_reversal_25d: float
    skew_slope: float
