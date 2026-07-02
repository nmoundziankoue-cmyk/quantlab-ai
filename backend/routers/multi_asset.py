"""M16 — Multi-Asset Analytics Platform router (30+ endpoints).

All endpoints are under the /multi-asset prefix.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from schemas.multi_asset import (
    # Asset Registry
    RegisterAssetRequest, AssetFilterRequest,
    # Cross-Asset
    CorrelationMatrixRequest, RollingCorrelationRequest, DynamicBetaRequest,
    RelativeStrengthRequest, LeadLagRequest, SpilloverRequest, RiskTransmissionRequest,
    # Factor
    FactorExposuresRequest, FactorReturnsRequest, FactorAttributionRequest,
    FactorCorrelationRequest, PortfolioFactorRequest,
    # ETF
    ETFProfileInput, ETFOverlapRequest, MultiETFOverlapRequest,
    TrackingDifferenceRequest, FlowEstimateRequest,
    # Bond
    BondSpecInput, BondAnalyticsRequest, YieldCurveInput, PortfolioBondRequest,
    # Options
    BSPriceRequest, ImpliedVolRequest, OptionAnalyticsRequest,
    MaxPainRequest, GammaExposureRequest, IVRankRequest,
    # Futures
    TermStructureRequest, RollYieldRequest, BasisRequest,
    FairValueRequest, CarryRankingRequest,
    # Crypto
    CryptoAssetInput, MarketBreadthRequest, CycleIndicatorRequest, OnChainProxyRequest,
    # Portfolio Exposure
    PortfolioExposureRequest, DriftRequest, ActiveWeightsRequest, HoldingInput,
)
from services.asset_registry import (
    AssetMetadata, AssetRegistry, get_asset_registry,
    AssetType, Exchange, Currency, Country, Sector, Industry, MarketCapBucket, CreditRating,
)
from services.cross_asset_engine import (
    CrossAssetEngine, CorrelationMethod, get_cross_asset_engine,
)
from services.factor_engine import FactorEngine, FactorType, get_factor_engine
from services.etf_engine import ETFEngine, ETFProfile, ETFHolding, get_etf_engine
from services.bond_engine import BondEngine, BondSpec, BondType, YieldCurve, YieldCurvePoint, get_bond_engine
from services.options_engine import OptionsEngine, OptionSpec, OptionType, OptionStyle, get_options_engine
from services.futures_engine import FuturesEngine, FuturesContract, AssetClass as FuturesAssetClass, get_futures_engine
from services.crypto_engine import CryptoEngine, CryptoAsset, CryptoSector, get_crypto_engine
from services.portfolio_exposure import PortfolioExposureEngine, Holding, get_portfolio_exposure_engine

router = APIRouter(prefix="/multi-asset", tags=["multi_asset"])


# ---------------------------------------------------------------------------
# Helpers — convert schema inputs to service objects
# ---------------------------------------------------------------------------

def _etf_profile(inp: ETFProfileInput) -> ETFProfile:
    return ETFProfile(
        ticker=inp.ticker,
        name=inp.name,
        expense_ratio=inp.expense_ratio,
        aum_usd=inp.aum_usd,
        benchmark=inp.benchmark,
        holdings=[ETFHolding(
            ticker=h.ticker, name=h.name, weight=h.weight,
            sector=h.sector, country=h.country,
            market_cap_bucket=h.market_cap_bucket, asset_type=h.asset_type,
        ) for h in inp.holdings],
        inception_date=inp.inception_date,
        issuer=inp.issuer,
    )


def _bond_spec(inp: BondSpecInput) -> BondSpec:
    return BondSpec(
        isin=inp.isin,
        ticker=inp.ticker,
        face_value=inp.face_value,
        coupon_rate=inp.coupon_rate,
        coupon_frequency=inp.coupon_frequency,
        maturity_years=inp.maturity_years,
        bond_type=BondType(inp.bond_type),
        credit_rating=inp.credit_rating,
        callable=inp.callable,
    )


def _option_spec(inp) -> OptionSpec:
    return OptionSpec(
        ticker=inp.ticker,
        option_type=OptionType(inp.option_type),
        strike=inp.strike,
        expiry_years=inp.expiry_years,
        style=OptionStyle(inp.style),
        multiplier=inp.multiplier,
        open_interest=inp.open_interest,
        volume=inp.volume,
    )


def _futures_contract(inp) -> FuturesContract:
    return FuturesContract(
        ticker=inp.ticker,
        contract_code=inp.contract_code,
        expiry_years=inp.expiry_years,
        price=inp.price,
        open_interest=inp.open_interest,
        volume=inp.volume,
        asset_class=FuturesAssetClass(inp.asset_class),
    )


def _crypto_asset(inp: CryptoAssetInput) -> CryptoAsset:
    sector = CryptoSector(inp.sector) if inp.sector in CryptoSector._value2member_map_ else CryptoSector.OTHER
    return CryptoAsset(
        ticker=inp.ticker,
        name=inp.name,
        sector=sector,
        market_cap_usd=inp.market_cap_usd,
        circulating_supply=inp.circulating_supply,
        total_supply=inp.total_supply,
        is_stablecoin=inp.is_stablecoin,
        chain=inp.chain,
        consensus=inp.consensus,
    )


def _holding(inp: HoldingInput) -> Holding:
    return Holding(
        ticker=inp.ticker,
        weight=inp.weight,
        sector=inp.sector,
        country=inp.country,
        currency=inp.currency,
        asset_class=inp.asset_class,
        market_cap_bucket=inp.market_cap_bucket,
        credit_rating=inp.credit_rating,
        duration=inp.duration,
        beta=inp.beta,
        factor_exposures=inp.factor_exposures,
    )


# ---------------------------------------------------------------------------
# Asset Registry
# ---------------------------------------------------------------------------

@router.post("/assets/register")
def register_asset(req: RegisterAssetRequest) -> Dict[str, Any]:
    """Register a new asset in the multi-asset registry."""
    reg = get_asset_registry()
    try:
        asset_type = AssetType(req.asset_type)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Unknown asset_type: {req.asset_type}")

    def _safe_enum(cls, val, default):
        try:
            return cls(val) if val else default
        except ValueError:
            return default

    asset = reg.register(
        ticker=req.ticker,
        name=req.name,
        asset_type=asset_type,
        exchange=_safe_enum(Exchange, req.exchange, Exchange.UNKNOWN),
        currency=_safe_enum(Currency, req.currency, Currency.USD),
        country=_safe_enum(Country, req.country, Country.US),
        sector=_safe_enum(Sector, req.sector, Sector.UNKNOWN),
        industry=_safe_enum(Industry, req.industry, Industry.UNKNOWN),
        isin=req.isin,
        cusip=req.cusip,
        sedol=req.sedol,
        description=req.description or "",
        metadata=req.metadata or {},
    )
    return {"asset_id": asset.asset_id, "ticker": req.ticker}


@router.get("/assets")
def list_assets() -> List[Dict[str, Any]]:
    """List all registered assets."""
    return [a.to_dict() for a in get_asset_registry().all_assets()]


@router.get("/assets/statistics")
def asset_statistics() -> Dict[str, Any]:
    """Registry statistics."""
    return get_asset_registry().statistics()


@router.get("/assets/search/{query}")
def search_assets(query: str) -> List[Dict[str, Any]]:
    """Full-text search over asset registry."""
    return [a.to_dict() for a in get_asset_registry().search(query)]


@router.post("/assets/filter")
def filter_assets(req: AssetFilterRequest) -> List[Dict[str, Any]]:
    """Filter assets by type, sector, country, or exchange."""
    reg = get_asset_registry()
    def _safe_enum(cls, val):
        try:
            return cls(val) if val else None
        except ValueError:
            return None

    results = reg.filter(
        asset_type=_safe_enum(AssetType, req.asset_type),
        sector=_safe_enum(Sector, req.sector),
        country=_safe_enum(Country, req.country),
        exchange=_safe_enum(Exchange, req.exchange),
        is_active=True if req.active_only else None,
    )
    return [a.to_dict() for a in results]


@router.get("/assets/{ticker}")
def get_asset(ticker: str) -> Dict[str, Any]:
    """Look up an asset by ticker."""
    reg = get_asset_registry()
    asset = reg.get_by_ticker(ticker.upper())
    if asset is None:
        raise HTTPException(status_code=404, detail=f"Asset not found: {ticker}")
    return asset.to_dict()


# ---------------------------------------------------------------------------
# Cross-Asset Engine
# ---------------------------------------------------------------------------

@router.post("/cross-asset/correlation-matrix")
def correlation_matrix(req: CorrelationMatrixRequest) -> Dict[str, Any]:
    """Compute pairwise correlation matrix."""
    method = CorrelationMethod(req.method) if req.method in CorrelationMethod._value2member_map_ else CorrelationMethod.PEARSON
    result = get_cross_asset_engine().correlation_matrix(req.returns_map, method=method, window=req.window)
    return result.to_dict()


@router.post("/cross-asset/rolling-correlation")
def rolling_correlation(req: RollingCorrelationRequest) -> Dict[str, Any]:
    """Rolling Pearson correlation between two assets."""
    result = get_cross_asset_engine().rolling_correlation(
        req.returns_a, req.returns_b, req.ticker_a, req.ticker_b, window=req.window
    )
    return result.to_dict()


@router.post("/cross-asset/dynamic-beta")
def dynamic_beta(req: DynamicBetaRequest) -> Dict[str, Any]:
    """Rolling OLS beta of asset against benchmark."""
    result = get_cross_asset_engine().dynamic_beta(
        req.asset_returns, req.benchmark_returns, req.ticker, req.benchmark, window=req.window
    )
    return result.to_dict()


@router.post("/cross-asset/relative-strength")
def relative_strength(req: RelativeStrengthRequest) -> Dict[str, Any]:
    """Relative strength and information ratio."""
    result = get_cross_asset_engine().relative_strength(
        req.asset_returns, req.benchmark_returns, req.ticker, req.benchmark
    )
    return result.to_dict()


@router.post("/cross-asset/lead-lag")
def lead_lag(req: LeadLagRequest) -> Dict[str, Any]:
    """Lead-lag analysis between two assets."""
    result = get_cross_asset_engine().lead_lag_analysis(
        req.returns_a, req.returns_b, req.ticker_a, req.ticker_b, max_lag=req.max_lag
    )
    return result.to_dict()


@router.post("/cross-asset/spillover")
def spillover(req: SpilloverRequest) -> Dict[str, Any]:
    """Full n×n spillover matrix."""
    return get_cross_asset_engine().spillover_matrix(req.returns_map, lag=req.lag)


@router.post("/cross-asset/risk-transmission")
def risk_transmission(req: RiskTransmissionRequest) -> Dict[str, Any]:
    """Risk transmission matrix."""
    return get_cross_asset_engine().risk_transmission_matrix(req.returns_map).to_dict()


@router.post("/cross-asset/synchronization")
def market_synchronization(req: CorrelationMatrixRequest) -> Dict[str, Any]:
    """Market synchronization score."""
    return get_cross_asset_engine().market_synchronization(req.returns_map)


@router.post("/cross-asset/dependency-graph")
def dependency_graph(req: CorrelationMatrixRequest) -> Dict[str, Any]:
    """Cross-market dependency graph."""
    threshold = 0.3
    return get_cross_asset_engine().dependency_graph(req.returns_map, threshold=threshold)


# ---------------------------------------------------------------------------
# Factor Engine
# ---------------------------------------------------------------------------

@router.post("/factors/exposures")
def factor_exposures(req: FactorExposuresRequest) -> Dict[str, Any]:
    """Compute factor exposure object for an asset."""
    engine = get_factor_engine()
    factor_scores = {}
    for k, v in req.factor_scores.items():
        try:
            factor_scores[FactorType(k)] = v
        except ValueError:
            pass
    result = engine.compute_exposures(req.ticker, factor_scores)
    return result.to_dict()


@router.post("/factors/returns")
def factor_returns(req: FactorReturnsRequest) -> Dict[str, Any]:
    """Compute factor return statistics."""
    try:
        factor_type = FactorType(req.factor)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Unknown factor: {req.factor}")
    result = get_factor_engine().compute_factor_returns(factor_type, req.long_returns, req.short_returns)
    return result.to_dict()


@router.post("/factors/attribution")
def factor_attribution(req: FactorAttributionRequest) -> Dict[str, Any]:
    """Decompose asset returns into factor contributions."""
    engine = get_factor_engine()
    factor_returns_map = {FactorType(k): v for k, v in req.factor_returns_map.items() if k in FactorType._value2member_map_}
    exposures = {FactorType(k): v for k, v in req.exposures.items() if k in FactorType._value2member_map_}
    result = engine.attribute_returns(req.ticker, req.asset_returns, factor_returns_map, exposures)
    return result.to_dict()


@router.post("/factors/correlation")
def factor_correlation(req: FactorCorrelationRequest) -> Dict[str, Any]:
    """Factor correlation matrix + clustering."""
    engine = get_factor_engine()
    factor_returns_map = {FactorType(k): v for k, v in req.factor_returns_map.items() if k in FactorType._value2member_map_}
    corr = engine.factor_correlation(factor_returns_map)
    clusters = engine.cluster_factors(factor_returns_map, n_clusters=req.n_clusters)
    return {
        "correlation": corr,
        "clusters": [c.to_dict() for c in clusters],
    }


@router.post("/factors/portfolio-exposure")
def portfolio_factor_exposure(req: PortfolioFactorRequest) -> Dict[str, Any]:
    """Weighted average factor exposure for a portfolio."""
    engine = get_factor_engine()
    asset_exps = {
        ticker: {FactorType(k): v for k, v in exps.items() if k in FactorType._value2member_map_}
        for ticker, exps in req.asset_exposures.items()
    }
    result = engine.portfolio_factor_exposure(req.holdings, asset_exps)
    return {k.value: v for k, v in result.items()}


# ---------------------------------------------------------------------------
# ETF Engine
# ---------------------------------------------------------------------------

@router.post("/etf/sector-exposure")
def etf_sector_exposure(etf: ETFProfileInput) -> Dict[str, Any]:
    """ETF sector exposure breakdown."""
    return get_etf_engine().sector_exposure(_etf_profile(etf)).to_dict()


@router.post("/etf/country-exposure")
def etf_country_exposure(etf: ETFProfileInput) -> Dict[str, Any]:
    """ETF country exposure breakdown."""
    return get_etf_engine().country_exposure(_etf_profile(etf)).to_dict()


@router.post("/etf/overlap")
def etf_overlap(req: ETFOverlapRequest) -> Dict[str, Any]:
    """Holdings overlap between two ETFs."""
    return get_etf_engine().compute_overlap(_etf_profile(req.etf_a), _etf_profile(req.etf_b)).to_dict()


@router.post("/etf/multi-overlap")
def etf_multi_overlap(req: MultiETFOverlapRequest) -> Dict[str, Any]:
    """Pairwise overlap matrix for multiple ETFs."""
    return get_etf_engine().multi_fund_overlap([_etf_profile(e) for e in req.etfs])


@router.post("/etf/tracking-difference")
def etf_tracking_difference(req: TrackingDifferenceRequest) -> Dict[str, Any]:
    """Tracking difference and error vs benchmark."""
    return get_etf_engine().tracking_difference(_etf_profile(req.etf), req.etf_returns, req.benchmark_returns).to_dict()


@router.post("/etf/flow-estimate")
def etf_flow_estimate(req: FlowEstimateRequest) -> Dict[str, Any]:
    """AUM-based ETF flow estimate."""
    return get_etf_engine().estimate_flows(_etf_profile(req.etf), req.aum_start, req.aum_end, req.period_return).to_dict()


@router.post("/etf/summary")
def etf_summary(etf: ETFProfileInput) -> Dict[str, Any]:
    """Comprehensive ETF fund summary."""
    return get_etf_engine().fund_summary(_etf_profile(etf))


# ---------------------------------------------------------------------------
# Bond Engine
# ---------------------------------------------------------------------------

@router.post("/bonds/analyze")
def bond_analyze(req: BondAnalyticsRequest) -> Dict[str, Any]:
    """Full bond analytics: duration, convexity, YTM, DV01, buckets."""
    try:
        result = get_bond_engine().analyze(
            _bond_spec(req.bond), req.market_price,
            risk_free_rate=req.risk_free_rate,
            accrual_fraction=req.accrual_fraction,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return result.to_dict()


@router.post("/bonds/ytm")
def bond_ytm(req: BondAnalyticsRequest) -> Dict[str, float]:
    """Compute yield-to-maturity only."""
    y = get_bond_engine().ytm(_bond_spec(req.bond), req.market_price)
    return {"ytm": y}


@router.post("/bonds/duration")
def bond_duration(req: BondAnalyticsRequest) -> Dict[str, float]:
    """Macaulay and modified duration."""
    bond = _bond_spec(req.bond)
    y = get_bond_engine().ytm(bond, req.market_price)
    return {
        "macaulay_duration": get_bond_engine().macaulay_duration(bond, y),
        "modified_duration": get_bond_engine().modified_duration(bond, y),
    }


@router.post("/bonds/portfolio-duration")
def portfolio_bond_duration(req: PortfolioBondRequest) -> Dict[str, float]:
    """Weighted portfolio duration."""
    bonds = [_bond_spec(b) for b in req.bonds]
    dur = get_bond_engine().portfolio_duration(bonds, req.prices, req.weights)
    return {"portfolio_modified_duration": dur}


@router.post("/bonds/yield-buckets")
def bond_yield_buckets(req: PortfolioBondRequest) -> Dict[str, Any]:
    """Portfolio weight by yield bucket."""
    bonds = [_bond_spec(b) for b in req.bonds]
    return get_bond_engine().yield_bucket_breakdown(bonds, req.prices, req.weights)


@router.post("/bonds/credit-buckets")
def bond_credit_buckets(req: PortfolioBondRequest) -> Dict[str, Any]:
    """Portfolio weight by credit quality bucket."""
    bonds = [_bond_spec(b) for b in req.bonds]
    return get_bond_engine().credit_bucket_breakdown(bonds, req.weights)


# ---------------------------------------------------------------------------
# Options Engine
# ---------------------------------------------------------------------------

@router.post("/options/price")
def option_price(req: BSPriceRequest) -> Dict[str, float]:
    """Black-Scholes theoretical option price."""
    opt_type = OptionType(req.option_type)
    price = get_options_engine().bs_price(req.S, req.K, req.T, req.r, req.sigma, opt_type)
    return {"price": price}


@router.post("/options/greeks")
def option_greeks(req: BSPriceRequest) -> Dict[str, Any]:
    """Full set of Black-Scholes Greeks."""
    opt_type = OptionType(req.option_type)
    g = get_options_engine().bs_greeks(req.S, req.K, req.T, req.r, req.sigma, opt_type)
    return g.to_dict()


@router.post("/options/implied-vol")
def implied_vol(req: ImpliedVolRequest) -> Dict[str, float]:
    """Implied volatility via bisection."""
    opt_type = OptionType(req.option_type)
    iv = get_options_engine().implied_volatility(req.market_price, req.S, req.K, req.T, req.r, opt_type)
    return {"implied_volatility": iv}


@router.post("/options/analyze")
def option_analyze(req: OptionAnalyticsRequest) -> Dict[str, Any]:
    """Full analytics for a single option contract."""
    spec = _option_spec(req.spec)
    result = get_options_engine().analyze(spec, req.underlying_price, req.iv, req.risk_free_rate)
    return result.to_dict()


@router.post("/options/max-pain")
def max_pain(req: MaxPainRequest) -> Dict[str, Any]:
    """Max pain analysis for a given expiry."""
    calls = [_option_spec(c) for c in req.calls]
    puts = [_option_spec(p) for p in req.puts]
    result = get_options_engine().max_pain(req.ticker, req.expiry_years, calls, puts)
    return result.to_dict()


@router.post("/options/gamma-exposure")
def gamma_exposure(req: GammaExposureRequest) -> Dict[str, Any]:
    """Net dealer gamma exposure (GEX)."""
    calls = [_option_spec(c) for c in req.calls]
    puts = [_option_spec(p) for p in req.puts]
    iv_map = {float(k): v for k, v in req.iv_map.items()}
    result = get_options_engine().gamma_exposure(
        req.ticker, req.underlying_price, calls, puts, iv_map, req.risk_free_rate
    )
    return result.to_dict()


@router.post("/options/iv-rank")
def iv_rank(req: IVRankRequest) -> Dict[str, float]:
    """IV Rank and IV Percentile."""
    engine = get_options_engine()
    return {
        "iv_rank": engine.iv_rank(req.current_iv, req.iv_history),
        "iv_percentile": engine.iv_percentile(req.current_iv, req.iv_history),
    }


# ---------------------------------------------------------------------------
# Futures Engine
# ---------------------------------------------------------------------------

@router.post("/futures/term-structure")
def futures_term_structure(req: TermStructureRequest) -> Dict[str, Any]:
    """Futures term structure with contango/backwardation classification."""
    contracts = [_futures_contract(c) for c in req.contracts]
    return get_futures_engine().term_structure(contracts).to_dict()


@router.post("/futures/roll-yield")
def futures_roll_yield(req: RollYieldRequest) -> Dict[str, Any]:
    """Annualised roll yield between two contracts."""
    return get_futures_engine().roll_yield(_futures_contract(req.near), _futures_contract(req.far)).to_dict()


@router.post("/futures/basis")
def futures_basis(req: BasisRequest) -> Dict[str, Any]:
    """Spot-futures basis and cost-of-carry."""
    return get_futures_engine().basis(req.ticker, req.spot_price, _futures_contract(req.near_contract)).to_dict()


@router.post("/futures/fair-value")
def futures_fair_value(req: FairValueRequest) -> Dict[str, float]:
    """Theoretical futures fair value."""
    fv = get_futures_engine().fair_value(
        req.spot, req.risk_free_rate, req.dividend_yield,
        req.storage_cost, req.convenience_yield, req.expiry_years
    )
    return {"fair_value": fv}


@router.post("/futures/carry-ranking")
def futures_carry_ranking(req: CarryRankingRequest) -> List[Dict[str, Any]]:
    """Cross-sectional carry ranking."""
    return [s.to_dict() for s in get_futures_engine().carry_scores(req.carry_map)]


# ---------------------------------------------------------------------------
# Crypto Engine
# ---------------------------------------------------------------------------

@router.post("/crypto/dominance")
def crypto_dominance(assets: List[CryptoAssetInput]) -> Dict[str, Any]:
    """Crypto market dominance snapshot."""
    return get_crypto_engine().dominance_snapshot([_crypto_asset(a) for a in assets]).to_dict()


@router.post("/crypto/stablecoin-ratio")
def stablecoin_ratio(assets: List[CryptoAssetInput]) -> Dict[str, Any]:
    """Stablecoin ratio and risk signal."""
    return get_crypto_engine().stablecoin_ratio([_crypto_asset(a) for a in assets]).to_dict()


@router.post("/crypto/breadth")
def crypto_breadth(req: MarketBreadthRequest) -> Dict[str, Any]:
    """Crypto market breadth indicators."""
    assets = [_crypto_asset(a) for a in req.assets]
    result = get_crypto_engine().market_breadth(
        assets, req.returns, req.price_series_map, req.prior_ad_line
    )
    return result.to_dict()


@router.post("/crypto/cycle-indicator")
def crypto_cycle(req: CycleIndicatorRequest) -> Dict[str, Any]:
    """Crypto market cycle phase indicator."""
    result = get_crypto_engine().cycle_indicator(
        req.btc_current_price, req.btc_ath,
        req.btc_returns_90d, req.altcoin_dominance, req.stablecoin_ratio
    )
    return result.to_dict()


@router.post("/crypto/on-chain-proxy")
def on_chain_proxy(req: OnChainProxyRequest) -> Dict[str, Any]:
    """On-chain proxy metrics (NVT, MVRV, activity)."""
    result = get_crypto_engine().on_chain_proxy(
        _crypto_asset(req.asset), req.price_series, req.volume_series
    )
    return result.to_dict()


@router.post("/crypto/sector-performance")
def crypto_sector_performance(req: MarketBreadthRequest) -> Dict[str, Any]:
    """Market-cap-weighted performance by crypto sector."""
    return get_crypto_engine().sector_performance(
        [_crypto_asset(a) for a in req.assets], req.returns
    )


# ---------------------------------------------------------------------------
# Portfolio Exposure Engine
# ---------------------------------------------------------------------------

@router.post("/portfolio/exposure")
def portfolio_exposure(req: PortfolioExposureRequest) -> Dict[str, Any]:
    """Full multi-dimensional portfolio exposure report."""
    holdings = [_holding(h) for h in req.holdings]
    return get_portfolio_exposure_engine().full_report(holdings)


@router.post("/portfolio/sector-exposure")
def portfolio_sector(req: PortfolioExposureRequest) -> Dict[str, Any]:
    """Portfolio exposure by sector."""
    return get_portfolio_exposure_engine().sector_exposure([_holding(h) for h in req.holdings]).to_dict()


@router.post("/portfolio/country-exposure")
def portfolio_country(req: PortfolioExposureRequest) -> Dict[str, Any]:
    """Portfolio exposure by country."""
    return get_portfolio_exposure_engine().country_exposure([_holding(h) for h in req.holdings]).to_dict()


@router.post("/portfolio/concentration")
def portfolio_concentration(req: PortfolioExposureRequest) -> Dict[str, Any]:
    """Portfolio concentration metrics (HHI, Gini, top-N)."""
    return get_portfolio_exposure_engine().concentration_metrics([_holding(h) for h in req.holdings]).to_dict()


@router.post("/portfolio/risk-exposure")
def portfolio_risk(req: PortfolioExposureRequest) -> Dict[str, Any]:
    """Portfolio risk metrics (beta, duration, asset class mix)."""
    return get_portfolio_exposure_engine().risk_exposure([_holding(h) for h in req.holdings]).to_dict()


@router.post("/portfolio/drift")
def portfolio_drift(req: DriftRequest) -> Dict[str, Any]:
    """Weight drift from target allocation."""
    return get_portfolio_exposure_engine().drift_from_target(req.current_weights, req.target_weights)


@router.post("/portfolio/active-weights")
def portfolio_active_weights(req: ActiveWeightsRequest) -> Dict[str, float]:
    """Active weights (portfolio minus benchmark)."""
    portfolio = [_holding(h) for h in req.portfolio]
    benchmark = [_holding(h) for h in req.benchmark]
    return get_portfolio_exposure_engine().active_weights(portfolio, benchmark)
