"""M16 API integration tests — FastAPI TestClient for /multi-asset endpoints."""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
BASE = "/multi-asset"


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

ETF_PAYLOAD = {
    "ticker": "SPY",
    "name": "SPDR S&P 500 ETF",
    "expense_ratio": 0.0009,
    "aum_usd": 450000,
    "benchmark": "S&P 500",
    "holdings": [
        {"ticker": "AAPL", "name": "Apple", "weight": 0.15,
         "sector": "Information Technology", "country": "US",
         "market_cap_bucket": "large", "asset_type": "equity"},
        {"ticker": "MSFT", "name": "Microsoft", "weight": 0.12,
         "sector": "Information Technology", "country": "US",
         "market_cap_bucket": "large", "asset_type": "equity"},
    ],
    "inception_date": "1993-01-22",
    "issuer": "SSGA",
}

BOND_SPEC = {
    "isin": "US912828T554", "ticker": "UST10Y",
    "face_value": 1000.0, "coupon_rate": 0.0425,
    "coupon_frequency": 2, "maturity_years": 10.0,
    "bond_type": "government", "credit_rating": "AAA", "callable": False,
}

CALL_SPEC = {
    "ticker": "SPY", "option_type": "call", "strike": 450.0,
    "expiry_years": 0.25, "style": "european",
    "multiplier": 100, "open_interest": 1000, "volume": 500,
}

PUT_SPEC = {
    "ticker": "SPY", "option_type": "put", "strike": 450.0,
    "expiry_years": 0.25, "style": "european",
    "multiplier": 100, "open_interest": 800, "volume": 400,
}

FUTURES_CONTRACT = {
    "ticker": "CL", "contract_code": "CLZ24",
    "expiry_years": 0.0833, "price": 80.0,
    "open_interest": 50000, "volume": 30000, "asset_class": "energy",
}

FUTURES_CONTRACT2 = {
    "ticker": "CL", "contract_code": "CLG25",
    "expiry_years": 0.25, "price": 82.0,
    "open_interest": 20000, "volume": 15000, "asset_class": "energy",
}

CRYPTO_ASSET = {
    "ticker": "BTC", "name": "Bitcoin", "sector": "layer1",
    "market_cap_usd": 800000.0, "circulating_supply": 19500000,
    "total_supply": 21000000, "is_stablecoin": False, "chain": "native", "consensus": "pow",
}

HOLDING = {
    "ticker": "AAPL", "weight": 0.5, "sector": "Information Technology",
    "country": "US", "currency": "USD", "asset_class": "equity",
    "market_cap_bucket": "large", "credit_rating": "", "duration": 0.0,
    "beta": 1.2, "factor_exposures": {"momentum": 0.8},
}

RETURNS = [0.01, -0.02, 0.03, 0.01, -0.01, 0.02, 0.01, -0.01, 0.02, 0.01,
           0.01, -0.01, 0.02, 0.01, -0.01, 0.02, 0.01, -0.01, 0.02, 0.01]

RETURNS2 = [0.02, -0.03, 0.04, 0.01, -0.02, 0.03, 0.02, -0.02, 0.03, 0.02,
            0.02, -0.02, 0.03, 0.02, -0.02, 0.03, 0.02, -0.02, 0.03, 0.02]


class TestAssetRegistryAPI:
    def test_register_asset_201(self):
        r = client.post(f"{BASE}/assets/register", json={
            "ticker": "TESTAPI", "name": "Test API Asset",
            "asset_type": "equity", "exchange": "NYSE",
            "currency": "USD", "country": "US",
            "sector": "Technology", "industry": "Software",
            "market_cap_usd": 1000.0,
        })
        assert r.status_code == 200
        assert "asset_id" in r.json()

    def test_register_and_get(self):
        client.post(f"{BASE}/assets/register", json={
            "ticker": "GETME", "name": "Get Me", "asset_type": "equity",
            "exchange": "NASDAQ", "currency": "USD", "country": "US",
        })
        r = client.get(f"{BASE}/assets/GETME")
        assert r.status_code == 200
        assert r.json()["ticker"] == "GETME"

    def test_get_nonexistent_404(self):
        r = client.get(f"{BASE}/assets/ZZZNOPE")
        assert r.status_code == 404

    def test_list_assets(self):
        r = client.get(f"{BASE}/assets")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_filter_assets(self):
        r = client.post(f"{BASE}/assets/filter", json={"asset_type": "equity"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_search_assets(self):
        r = client.get(f"{BASE}/assets/search/TESTAPI")
        assert r.status_code == 200

    def test_statistics(self):
        r = client.get(f"{BASE}/assets/statistics")
        assert r.status_code == 200
        assert "total" in r.json()


class TestCrossAssetAPI:
    def test_correlation_matrix(self):
        r = client.post(f"{BASE}/cross-asset/correlation-matrix", json={
            "returns_map": {"A": RETURNS, "B": RETURNS2},
            "method": "pearson",
        })
        assert r.status_code == 200
        data = r.json()
        assert "matrix" in data and "tickers" in data

    def test_rolling_correlation(self):
        r = client.post(f"{BASE}/cross-asset/rolling-correlation", json={
            "returns_a": RETURNS, "returns_b": RETURNS2,
            "ticker_a": "A", "ticker_b": "B", "window": 10,
        })
        assert r.status_code == 200
        assert "correlations" in r.json()

    def test_dynamic_beta(self):
        r = client.post(f"{BASE}/cross-asset/dynamic-beta", json={
            "asset_returns": RETURNS, "benchmark_returns": RETURNS2,
            "ticker": "A", "benchmark": "B", "window": 10,
        })
        assert r.status_code == 200
        assert "betas" in r.json()

    def test_relative_strength(self):
        r = client.post(f"{BASE}/cross-asset/relative-strength", json={
            "asset_returns": RETURNS, "benchmark_returns": RETURNS2,
            "ticker": "A", "benchmark": "B",
        })
        assert r.status_code == 200
        assert "rs_ratio" in r.json()

    def test_lead_lag(self):
        r = client.post(f"{BASE}/cross-asset/lead-lag", json={
            "returns_a": RETURNS, "returns_b": RETURNS2,
            "ticker_a": "A", "ticker_b": "B", "max_lag": 3,
        })
        assert r.status_code == 200
        assert "optimal_lag" in r.json()

    def test_spillover(self):
        r = client.post(f"{BASE}/cross-asset/spillover", json={
            "returns_map": {"A": RETURNS, "B": RETURNS2},
        })
        assert r.status_code == 200
        assert "matrix" in r.json()

    def test_risk_transmission(self):
        r = client.post(f"{BASE}/cross-asset/risk-transmission", json={
            "returns_map": {"A": RETURNS, "B": RETURNS2},
        })
        assert r.status_code == 200
        assert "net_transmitters" in r.json()

    def test_synchronization(self):
        r = client.post(f"{BASE}/cross-asset/synchronization", json={
            "returns_map": {"A": RETURNS, "B": RETURNS2},
        })
        assert r.status_code == 200
        assert "synchronization_score" in r.json()

    def test_dependency_graph(self):
        r = client.post(f"{BASE}/cross-asset/dependency-graph", json={
            "returns_map": {"A": RETURNS, "B": RETURNS2},
        })
        assert r.status_code == 200
        assert "nodes" in r.json() and "edges" in r.json()


class TestFactorsAPI:
    def test_factor_exposures(self):
        r = client.post(f"{BASE}/factors/exposures", json={
            "ticker": "AAPL",
            "factor_scores": {"market": 1.2, "momentum": 0.8},
        })
        assert r.status_code == 200
        assert "ticker" in r.json()

    def test_factor_returns(self):
        r = client.post(f"{BASE}/factors/returns", json={
            "factor": "momentum",
            "long_returns": RETURNS,
            "short_returns": RETURNS2,
        })
        assert r.status_code == 200
        assert "factor" in r.json()

    def test_factor_attribution(self):
        r = client.post(f"{BASE}/factors/attribution", json={
            "ticker": "AAPL",
            "asset_returns": RETURNS,
            "factor_returns_map": {"market": RETURNS2},
            "exposures": {"market": 1.0},
        })
        assert r.status_code == 200
        assert "total_return" in r.json()

    def test_factor_correlation(self):
        r = client.post(f"{BASE}/factors/correlation", json={
            "factor_returns_map": {"market": RETURNS, "momentum": RETURNS2},
            "n_clusters": 2,
        })
        assert r.status_code == 200
        assert "correlation" in r.json()

    def test_portfolio_factor_exposure(self):
        r = client.post(f"{BASE}/factors/portfolio-exposure", json={
            "holdings": {"AAPL": 0.6, "MSFT": 0.4},
            "asset_exposures": {
                "AAPL": {"market": 1.2},
                "MSFT": {"market": 0.9},
            },
        })
        assert r.status_code == 200


class TestETFAPI:
    def test_sector_exposure(self):
        r = client.post(f"{BASE}/etf/sector-exposure", json=ETF_PAYLOAD)
        assert r.status_code == 200
        assert "sectors" in r.json()

    def test_country_exposure(self):
        r = client.post(f"{BASE}/etf/country-exposure", json=ETF_PAYLOAD)
        assert r.status_code == 200
        assert "countries" in r.json()

    def test_overlap(self):
        qqq = {**ETF_PAYLOAD, "ticker": "QQQ", "name": "Invesco QQQ"}
        r = client.post(f"{BASE}/etf/overlap", json={"etf_a": ETF_PAYLOAD, "etf_b": qqq})
        assert r.status_code == 200
        assert "common_tickers" in r.json()

    def test_multi_overlap(self):
        qqq = {**ETF_PAYLOAD, "ticker": "QQQ", "name": "Invesco QQQ"}
        r = client.post(f"{BASE}/etf/multi-overlap", json={"etfs": [ETF_PAYLOAD, qqq]})
        assert r.status_code == 200
        assert "matrix" in r.json()

    def test_tracking_difference(self):
        r = client.post(f"{BASE}/etf/tracking-difference", json={
            "etf": ETF_PAYLOAD,
            "etf_returns": RETURNS,
            "benchmark_returns": RETURNS2,
        })
        assert r.status_code == 200
        assert "tracking_difference" in r.json()

    def test_flow_estimate(self):
        r = client.post(f"{BASE}/etf/flow-estimate", json={
            "etf": ETF_PAYLOAD,
            "aum_start": 100000,
            "aum_end": 102000,
            "period_return": 0.01,
        })
        assert r.status_code == 200
        assert "net_flow_usd" in r.json()

    def test_etf_summary(self):
        r = client.post(f"{BASE}/etf/summary", json=ETF_PAYLOAD)
        assert r.status_code == 200
        data = r.json()
        assert data["ticker"] == "SPY"


class TestBondsAPI:
    def test_bond_analyze(self):
        r = client.post(f"{BASE}/bonds/analyze", json={
            "bond": BOND_SPEC, "market_price": 985.0,
            "risk_free_rate": 0.042, "accrual_fraction": 0.0,
        })
        assert r.status_code == 200
        data = r.json()
        assert "ytm" in data and "duration" in data

    def test_bond_ytm(self):
        r = client.post(f"{BASE}/bonds/ytm", json={
            "bond": BOND_SPEC, "market_price": 985.0,
        })
        assert r.status_code == 200
        assert "ytm" in r.json()
        assert r.json()["ytm"] > 0

    def test_bond_duration(self):
        r = client.post(f"{BASE}/bonds/duration", json={
            "bond": BOND_SPEC, "market_price": 985.0,
        })
        assert r.status_code == 200
        assert "macaulay_duration" in r.json()

    def test_portfolio_duration(self):
        r = client.post(f"{BASE}/bonds/portfolio-duration", json={
            "bonds": [BOND_SPEC],
            "prices": [985.0],
            "weights": [1.0],
        })
        assert r.status_code == 200
        assert "portfolio_modified_duration" in r.json()

    def test_yield_buckets(self):
        r = client.post(f"{BASE}/bonds/yield-buckets", json={
            "bonds": [BOND_SPEC], "prices": [985.0], "weights": [1.0],
        })
        assert r.status_code == 200
        assert isinstance(r.json(), dict)

    def test_credit_buckets(self):
        r = client.post(f"{BASE}/bonds/credit-buckets", json={
            "bonds": [BOND_SPEC], "prices": [985.0], "weights": [1.0],
        })
        assert r.status_code == 200


class TestOptionsAPI:
    def test_option_price(self):
        r = client.post(f"{BASE}/options/price", json={
            "S": 450.0, "K": 450.0, "T": 0.25,
            "r": 0.05, "sigma": 0.20, "option_type": "call",
        })
        assert r.status_code == 200
        assert "price" in r.json()
        assert r.json()["price"] > 0

    def test_option_greeks(self):
        r = client.post(f"{BASE}/options/greeks", json={
            "S": 450.0, "K": 450.0, "T": 0.25,
            "r": 0.05, "sigma": 0.20, "option_type": "call",
        })
        assert r.status_code == 200
        d = r.json()
        assert "delta" in d and "gamma" in d and "vega" in d

    def test_implied_vol(self):
        r = client.post(f"{BASE}/options/implied-vol", json={
            "market_price": 20.0, "S": 450.0, "K": 450.0,
            "T": 0.25, "r": 0.05, "option_type": "call",
        })
        assert r.status_code == 200
        assert "implied_volatility" in r.json()

    def test_option_analyze(self):
        r = client.post(f"{BASE}/options/analyze", json={
            "spec": CALL_SPEC,
            "underlying_price": 450.0,
            "iv": 0.20,
            "risk_free_rate": 0.05,
        })
        assert r.status_code == 200
        assert "greeks" in r.json()

    def test_max_pain(self):
        r = client.post(f"{BASE}/options/max-pain", json={
            "ticker": "SPY",
            "expiry_years": 0.25,
            "calls": [CALL_SPEC],
            "puts": [PUT_SPEC],
        })
        assert r.status_code == 200
        assert "max_pain_strike" in r.json()

    def test_gamma_exposure(self):
        r = client.post(f"{BASE}/options/gamma-exposure", json={
            "ticker": "SPY",
            "underlying_price": 450.0,
            "calls": [CALL_SPEC],
            "puts": [PUT_SPEC],
            "iv_map": {"450.0": 0.20},
            "risk_free_rate": 0.05,
        })
        assert r.status_code == 200
        assert "net_gamma_exposure" in r.json()

    def test_iv_rank(self):
        r = client.post(f"{BASE}/options/iv-rank", json={
            "current_iv": 0.25,
            "iv_history": [0.10, 0.15, 0.20, 0.25, 0.30],
        })
        assert r.status_code == 200
        d = r.json()
        assert "iv_rank" in d and "iv_percentile" in d


class TestFuturesAPI:
    def test_term_structure(self):
        r = client.post(f"{BASE}/futures/term-structure", json={
            "contracts": [FUTURES_CONTRACT, FUTURES_CONTRACT2],
        })
        assert r.status_code == 200
        d = r.json()
        assert "structure" in d

    def test_roll_yield(self):
        r = client.post(f"{BASE}/futures/roll-yield", json={
            "near": FUTURES_CONTRACT, "far": FUTURES_CONTRACT2,
        })
        assert r.status_code == 200
        assert "roll_yield_annualised" in r.json()

    def test_basis(self):
        r = client.post(f"{BASE}/futures/basis", json={
            "ticker": "CL",
            "spot_price": 79.5,
            "near_contract": FUTURES_CONTRACT,
        })
        assert r.status_code == 200
        assert "basis" in r.json()

    def test_fair_value(self):
        r = client.post(f"{BASE}/futures/fair-value", json={
            "spot": 100.0, "risk_free_rate": 0.05,
            "dividend_yield": 0.02, "storage_cost": 0.0,
            "convenience_yield": 0.0, "expiry_years": 0.25,
        })
        assert r.status_code == 200
        assert "fair_value" in r.json()

    def test_carry_ranking(self):
        r = client.post(f"{BASE}/futures/carry-ranking", json={
            "carry_map": {"CL": 0.08, "GC": -0.02, "ES": 0.03},
        })
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert data[0]["rank"] == 1


class TestCryptoAPI:
    def test_dominance(self):
        r = client.post(f"{BASE}/crypto/dominance", json=[CRYPTO_ASSET])
        assert r.status_code == 200
        assert "btc_dominance" in r.json()

    def test_stablecoin_ratio(self):
        r = client.post(f"{BASE}/crypto/stablecoin-ratio", json=[CRYPTO_ASSET])
        assert r.status_code == 200
        assert "ratio" in r.json()

    def test_breadth(self):
        prices = [100.0 + i for i in range(30)]
        r = client.post(f"{BASE}/crypto/breadth", json={
            "assets": [CRYPTO_ASSET],
            "returns": {"BTC": 0.02},
            "price_series_map": {"BTC": prices},
            "prior_ad_line": 0.0,
        })
        assert r.status_code == 200
        assert "n_advancing" in r.json()

    def test_cycle_indicator(self):
        r = client.post(f"{BASE}/crypto/cycle-indicator", json={
            "btc_current_price": 80000.0,
            "btc_ath": 100000.0,
            "btc_returns_90d": [0.002] * 90,
            "altcoin_dominance": 0.30,
            "stablecoin_ratio": 0.08,
        })
        assert r.status_code == 200
        assert "cycle_phase" in r.json()

    def test_on_chain_proxy(self):
        r = client.post(f"{BASE}/crypto/on-chain-proxy", json={
            "asset": CRYPTO_ASSET,
            "price_series": [45000.0 + i * 100 for i in range(50)],
            "volume_series": [1000.0 + i for i in range(50)],
        })
        assert r.status_code == 200
        assert "nvt_proxy" in r.json()

    def test_sector_performance(self):
        r = client.post(f"{BASE}/crypto/sector-performance", json={
            "assets": [CRYPTO_ASSET],
            "returns": {"BTC": 0.05},
            "price_series_map": {},
        })
        assert r.status_code == 200


class TestPortfolioAPI:
    HOLDINGS = [
        {**HOLDING, "ticker": "AAPL", "weight": 0.5},
        {**HOLDING, "ticker": "MSFT", "weight": 0.5, "sector": "IT"},
    ]

    def test_portfolio_exposure(self):
        r = client.post(f"{BASE}/portfolio/exposure", json={"holdings": self.HOLDINGS})
        assert r.status_code == 200
        d = r.json()
        assert "sector" in d and "concentration" in d

    def test_sector_exposure(self):
        r = client.post(f"{BASE}/portfolio/sector-exposure", json={"holdings": self.HOLDINGS})
        assert r.status_code == 200
        assert "breakdown" in r.json()

    def test_country_exposure(self):
        r = client.post(f"{BASE}/portfolio/country-exposure", json={"holdings": self.HOLDINGS})
        assert r.status_code == 200
        assert "breakdown" in r.json()

    def test_concentration(self):
        r = client.post(f"{BASE}/portfolio/concentration", json={"holdings": self.HOLDINGS})
        assert r.status_code == 200
        d = r.json()
        assert "hhi" in d and "gini_coefficient" in d

    def test_risk_exposure(self):
        r = client.post(f"{BASE}/portfolio/risk-exposure", json={"holdings": self.HOLDINGS})
        assert r.status_code == 200
        assert "portfolio_beta" in r.json()

    def test_drift(self):
        r = client.post(f"{BASE}/portfolio/drift", json={
            "current_weights": {"AAPL": 0.6, "MSFT": 0.4},
            "target_weights": {"AAPL": 0.5, "MSFT": 0.5},
        })
        assert r.status_code == 200
        assert "total_absolute_drift" in r.json()

    def test_active_weights(self):
        r = client.post(f"{BASE}/portfolio/active-weights", json={
            "portfolio": [{**HOLDING, "ticker": "AAPL", "weight": 0.6}],
            "benchmark": [{**HOLDING, "ticker": "AAPL", "weight": 0.5}],
        })
        assert r.status_code == 200
        d = r.json()
        assert abs(d["AAPL"] - 0.1) < 1e-4
