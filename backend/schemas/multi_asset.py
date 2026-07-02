"""M16 — Pydantic v2 schemas for the Multi-Asset Analytics Platform."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Asset Registry
# ---------------------------------------------------------------------------

class RegisterAssetRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1)
    asset_type: str = Field(..., description="AssetType enum value")
    exchange: str = ""
    currency: str = "USD"
    country: str = ""
    sector: str = ""
    industry: str = ""
    market_cap_usd: Optional[float] = None
    isin: Optional[str] = None
    cusip: Optional[str] = None
    sedol: Optional[str] = None
    description: str = ""
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class AssetFilterRequest(BaseModel):
    asset_type: Optional[str] = None
    sector: Optional[str] = None
    country: Optional[str] = None
    exchange: Optional[str] = None
    active_only: bool = True


# ---------------------------------------------------------------------------
# Cross-Asset Engine
# ---------------------------------------------------------------------------

class CorrelationMatrixRequest(BaseModel):
    returns_map: Dict[str, List[float]] = Field(..., description="ticker -> return series")
    method: str = "pearson"
    window: Optional[int] = None


class RollingCorrelationRequest(BaseModel):
    returns_a: List[float]
    returns_b: List[float]
    ticker_a: str
    ticker_b: str
    window: int = Field(20, ge=2)


class DynamicBetaRequest(BaseModel):
    asset_returns: List[float]
    benchmark_returns: List[float]
    ticker: str
    benchmark: str
    window: int = Field(20, ge=2)


class RelativeStrengthRequest(BaseModel):
    asset_returns: List[float]
    benchmark_returns: List[float]
    ticker: str
    benchmark: str


class LeadLagRequest(BaseModel):
    returns_a: List[float]
    returns_b: List[float]
    ticker_a: str
    ticker_b: str
    max_lag: int = Field(5, ge=1, le=20)


class SpilloverRequest(BaseModel):
    returns_map: Dict[str, List[float]]
    lag: int = Field(1, ge=1)


class RiskTransmissionRequest(BaseModel):
    returns_map: Dict[str, List[float]]


# ---------------------------------------------------------------------------
# Factor Engine
# ---------------------------------------------------------------------------

class FactorExposuresRequest(BaseModel):
    ticker: str
    factor_scores: Dict[str, float] = Field(..., description="factor_type -> score")


class FactorReturnsRequest(BaseModel):
    factor: str
    long_returns: List[float]
    short_returns: List[float]


class FactorAttributionRequest(BaseModel):
    ticker: str
    asset_returns: List[float]
    factor_returns_map: Dict[str, List[float]]
    exposures: Dict[str, float]


class FactorCorrelationRequest(BaseModel):
    factor_returns_map: Dict[str, List[float]]
    n_clusters: int = Field(3, ge=2)


class PortfolioFactorRequest(BaseModel):
    holdings: Dict[str, float] = Field(..., description="ticker -> weight")
    asset_exposures: Dict[str, Dict[str, float]]


# ---------------------------------------------------------------------------
# ETF Engine
# ---------------------------------------------------------------------------

class ETFHoldingInput(BaseModel):
    ticker: str
    name: str
    weight: float = Field(..., ge=0, le=1)
    sector: str = ""
    country: str = ""
    market_cap_bucket: str = "large"
    asset_type: str = "equity"


class ETFProfileInput(BaseModel):
    ticker: str
    name: str
    expense_ratio: float = Field(0.0, ge=0)
    aum_usd: float = Field(0.0, ge=0)
    benchmark: str = ""
    holdings: List[ETFHoldingInput] = Field(default_factory=list)
    inception_date: str = ""
    issuer: str = ""


class ETFOverlapRequest(BaseModel):
    etf_a: ETFProfileInput
    etf_b: ETFProfileInput


class MultiETFOverlapRequest(BaseModel):
    etfs: List[ETFProfileInput]


class TrackingDifferenceRequest(BaseModel):
    etf: ETFProfileInput
    etf_returns: List[float]
    benchmark_returns: List[float]


class FlowEstimateRequest(BaseModel):
    etf: ETFProfileInput
    aum_start: float
    aum_end: float
    period_return: float


# ---------------------------------------------------------------------------
# Bond Engine
# ---------------------------------------------------------------------------

class BondSpecInput(BaseModel):
    isin: str = ""
    ticker: str = ""
    face_value: float = Field(1000.0, gt=0)
    coupon_rate: float = Field(..., ge=0, le=1)
    coupon_frequency: int = Field(2, ge=1)
    maturity_years: float = Field(..., gt=0)
    bond_type: str = "corporate"
    credit_rating: str = "BBB"
    callable: bool = False


class BondAnalyticsRequest(BaseModel):
    bond: BondSpecInput
    market_price: float = Field(..., gt=0)
    risk_free_rate: float = 0.0
    accrual_fraction: float = Field(0.0, ge=0, le=1)


class YieldCurveInput(BaseModel):
    name: str
    points: List[Dict[str, Any]]
    as_of: str = ""


class PortfolioBondRequest(BaseModel):
    bonds: List[BondSpecInput]
    prices: List[float]
    weights: List[float]


# ---------------------------------------------------------------------------
# Options Engine
# ---------------------------------------------------------------------------

class OptionSpecInput(BaseModel):
    ticker: str
    option_type: str = Field(..., description="'call' or 'put'")
    strike: float = Field(..., gt=0)
    expiry_years: float = Field(..., gt=0)
    style: str = "european"
    multiplier: int = 100
    open_interest: int = 0
    volume: int = 0


class BSPriceRequest(BaseModel):
    S: float = Field(..., gt=0)
    K: float = Field(..., gt=0)
    T: float = Field(..., gt=0)
    r: float = 0.0
    sigma: float = Field(..., gt=0)
    option_type: str = Field(..., description="'call' or 'put'")


class ImpliedVolRequest(BaseModel):
    market_price: float = Field(..., gt=0)
    S: float = Field(..., gt=0)
    K: float = Field(..., gt=0)
    T: float = Field(..., gt=0)
    r: float = 0.0
    option_type: str


class OptionAnalyticsRequest(BaseModel):
    spec: OptionSpecInput
    underlying_price: float = Field(..., gt=0)
    iv: float = Field(..., gt=0)
    risk_free_rate: float = 0.0


class MaxPainRequest(BaseModel):
    ticker: str
    expiry_years: float
    calls: List[OptionSpecInput]
    puts: List[OptionSpecInput]


class GammaExposureRequest(BaseModel):
    ticker: str
    underlying_price: float
    calls: List[OptionSpecInput]
    puts: List[OptionSpecInput]
    iv_map: Dict[str, float] = Field(default_factory=dict)
    risk_free_rate: float = 0.0


class IVRankRequest(BaseModel):
    current_iv: float
    iv_history: List[float]


# ---------------------------------------------------------------------------
# Futures Engine
# ---------------------------------------------------------------------------

class FuturesContractInput(BaseModel):
    ticker: str
    contract_code: str
    expiry_years: float = Field(..., gt=0)
    price: float = Field(..., gt=0)
    open_interest: int = 0
    volume: int = 0
    asset_class: str = "commodity"


class TermStructureRequest(BaseModel):
    contracts: List[FuturesContractInput]


class RollYieldRequest(BaseModel):
    near: FuturesContractInput
    far: FuturesContractInput


class BasisRequest(BaseModel):
    ticker: str
    spot_price: float
    near_contract: FuturesContractInput


class FairValueRequest(BaseModel):
    spot: float
    risk_free_rate: float = 0.0
    dividend_yield: float = 0.0
    storage_cost: float = 0.0
    convenience_yield: float = 0.0
    expiry_years: float = Field(..., gt=0)


class CarryRankingRequest(BaseModel):
    carry_map: Dict[str, float]


# ---------------------------------------------------------------------------
# Crypto Engine
# ---------------------------------------------------------------------------

class CryptoAssetInput(BaseModel):
    ticker: str
    name: str
    sector: str = "other"
    market_cap_usd: float = Field(0.0, ge=0)
    circulating_supply: float = Field(0.0, ge=0)
    total_supply: float = Field(0.0, ge=0)
    is_stablecoin: bool = False
    chain: str = "native"
    consensus: str = "pos"


class MarketBreadthRequest(BaseModel):
    assets: List[CryptoAssetInput]
    returns: Dict[str, float]
    price_series_map: Dict[str, List[float]] = Field(default_factory=dict)
    prior_ad_line: float = 0.0


class CycleIndicatorRequest(BaseModel):
    btc_current_price: float
    btc_ath: float
    btc_returns_90d: List[float] = Field(default_factory=list)
    altcoin_dominance: float = Field(0.3, ge=0, le=1)
    stablecoin_ratio: float = Field(0.1, ge=0, le=1)


class OnChainProxyRequest(BaseModel):
    asset: CryptoAssetInput
    price_series: List[float]
    volume_series: List[float]


# ---------------------------------------------------------------------------
# Portfolio Exposure
# ---------------------------------------------------------------------------

class HoldingInput(BaseModel):
    ticker: str
    weight: float = Field(..., ge=0, le=1)
    sector: str = ""
    country: str = ""
    currency: str = "USD"
    asset_class: str = "equity"
    market_cap_bucket: str = "large"
    credit_rating: str = ""
    duration: float = 0.0
    beta: float = 1.0
    factor_exposures: Dict[str, float] = Field(default_factory=dict)


class PortfolioExposureRequest(BaseModel):
    holdings: List[HoldingInput]


class DriftRequest(BaseModel):
    current_weights: Dict[str, float]
    target_weights: Dict[str, float]


class ActiveWeightsRequest(BaseModel):
    portfolio: List[HoldingInput]
    benchmark: List[HoldingInput]
