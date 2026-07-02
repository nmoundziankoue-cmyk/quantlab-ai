"""M16 tests — Crypto Intelligence Engine."""
import pytest
from services.crypto_engine import (
    CryptoEngine, CryptoAsset, CryptoSector, CyclePhase, MarketSentiment,
    DominanceSnapshot, OnChainProxy, MarketBreadth, StablecoinRatio,
    CycleIndicator, get_crypto_engine,
)

ENG = CryptoEngine()

BTC  = CryptoAsset("BTC",  "Bitcoin",  CryptoSector.LAYER1,     800000.0, 19.5e6, 21e6,   False, "native", "pow")
ETH  = CryptoAsset("ETH",  "Ethereum", CryptoSector.LAYER1,     380000.0, 120e6,  120e6,  False, "native", "pos")
USDT = CryptoAsset("USDT", "Tether",   CryptoSector.STABLECOIN, 100000.0, 100e9,  100e9,  True,  "ethereum", "")
LINK = CryptoAsset("LINK", "Chainlink",CryptoSector.ORACLE,      8000.0,  500e6,  1e9,    False, "ethereum", "pos")
SOL  = CryptoAsset("SOL",  "Solana",   CryptoSector.LAYER1,      70000.0, 440e6,  600e6,  False, "native", "pos")

UNIVERSE = [BTC, ETH, USDT, LINK, SOL]
TOTAL_MC = sum(a.market_cap_usd for a in UNIVERSE)


class TestDominanceSnapshot:
    def test_returns_dominance_snapshot(self):
        d = ENG.dominance_snapshot(UNIVERSE)
        assert isinstance(d, DominanceSnapshot)

    def test_btc_dominance_correct(self):
        d = ENG.dominance_snapshot(UNIVERSE)
        expected = BTC.market_cap_usd / TOTAL_MC
        assert abs(d.btc_dominance - expected) < 1e-5

    def test_eth_dominance_correct(self):
        d = ENG.dominance_snapshot(UNIVERSE)
        expected = ETH.market_cap_usd / TOTAL_MC
        assert abs(d.eth_dominance - expected) < 1e-5

    def test_stablecoin_dominance_nonneg(self):
        d = ENG.dominance_snapshot(UNIVERSE)
        assert d.stablecoin_dominance >= 0

    def test_altcoin_dominance_nonneg(self):
        d = ENG.dominance_snapshot(UNIVERSE)
        assert d.altcoin_dominance >= 0

    def test_total_market_cap_correct(self):
        d = ENG.dominance_snapshot(UNIVERSE)
        assert abs(d.total_market_cap_usd - TOTAL_MC) < 1.0

    def test_sector_dominance_has_layer1(self):
        d = ENG.dominance_snapshot(UNIVERSE)
        assert "layer1" in d.sector_dominance

    def test_sector_dominance_sums_to_one(self):
        d = ENG.dominance_snapshot(UNIVERSE)
        total = sum(d.sector_dominance.values())
        assert abs(total - 1.0) < 1e-4

    def test_to_dict(self):
        d = ENG.dominance_snapshot(UNIVERSE).to_dict()
        assert "btc_dominance" in d and "sector_dominance" in d

    def test_empty_universe(self):
        d = ENG.dominance_snapshot([])
        assert d.total_market_cap_usd == 0


class TestOnChainProxy:
    def setup_method(self):
        self.prices = [45000.0 + i * 100 for i in range(50)]
        self.volumes = [1000.0 + i * 10 for i in range(50)]

    def test_returns_on_chain_proxy(self):
        proxy = ENG.on_chain_proxy(BTC, self.prices, self.volumes)
        assert isinstance(proxy, OnChainProxy)

    def test_ticker_stored(self):
        proxy = ENG.on_chain_proxy(BTC, self.prices, self.volumes)
        assert proxy.ticker == "BTC"

    def test_nvt_positive(self):
        proxy = ENG.on_chain_proxy(BTC, self.prices, self.volumes)
        assert proxy.nvt_proxy >= 0

    def test_mvrv_positive(self):
        proxy = ENG.on_chain_proxy(BTC, self.prices, self.volumes)
        assert proxy.mvrv_proxy >= 0

    def test_nvt_signal_valid(self):
        proxy = ENG.on_chain_proxy(BTC, self.prices, self.volumes)
        assert proxy.nvt_signal in ("overvalued", "fair", "undervalued")

    def test_high_nvt_overvalued(self):
        # small volume => high NVT
        asset = CryptoAsset("XX", "XX", CryptoSector.LAYER1, 1e9, 1e6, 1e6)
        proxy = ENG.on_chain_proxy(asset, self.prices, [0.001] * 50)
        assert proxy.nvt_signal == "overvalued"

    def test_to_dict(self):
        d = ENG.on_chain_proxy(BTC, self.prices, self.volumes).to_dict()
        assert "nvt_proxy" in d and "mvrv_proxy" in d


class TestMarketBreadth:
    def setup_method(self):
        self.returns = {"BTC": 0.02, "ETH": 0.01, "USDT": 0.0, "LINK": -0.01, "SOL": -0.02}
        series = [100.0 + i for i in range(60)]
        self.psmap = {a.ticker: series for a in UNIVERSE}

    def test_returns_market_breadth(self):
        mb = ENG.market_breadth(UNIVERSE, self.returns, self.psmap)
        assert isinstance(mb, MarketBreadth)

    def test_n_assets(self):
        mb = ENG.market_breadth(UNIVERSE, self.returns, self.psmap)
        assert mb.n_assets == len(UNIVERSE)

    def test_advancing_count(self):
        mb = ENG.market_breadth(UNIVERSE, self.returns, self.psmap)
        assert mb.n_advancing == 2  # BTC and ETH positive

    def test_declining_count(self):
        mb = ENG.market_breadth(UNIVERSE, self.returns, self.psmap)
        assert mb.n_declining == 2  # LINK and SOL negative

    def test_ad_ratio_positive(self):
        mb = ENG.market_breadth(UNIVERSE, self.returns, self.psmap)
        assert mb.advance_decline_ratio > 0

    def test_pct_above_sma20_in_range(self):
        mb = ENG.market_breadth(UNIVERSE, self.returns, self.psmap)
        assert 0.0 <= mb.pct_above_sma20 <= 1.0

    def test_to_dict(self):
        mb = ENG.market_breadth(UNIVERSE, self.returns, self.psmap)
        d = mb.to_dict()
        assert "n_advancing" in d and "advance_decline_ratio" in d


class TestStablecoinRatio:
    def test_returns_stablecoin_ratio(self):
        sr = ENG.stablecoin_ratio(UNIVERSE)
        assert isinstance(sr, StablecoinRatio)

    def test_ratio_in_range(self):
        sr = ENG.stablecoin_ratio(UNIVERSE)
        assert 0.0 <= sr.ratio <= 1.0

    def test_signal_risk_off_when_high(self):
        stablecoins = [CryptoAsset("USDT", "T", CryptoSector.STABLECOIN, 80.0, 1e9, 1e9, True)]
        others = [CryptoAsset("BTC", "B", CryptoSector.LAYER1, 20.0, 1e6, 1e6, False)]
        sr = ENG.stablecoin_ratio(stablecoins + others, risk_off_threshold=0.5)
        assert sr.signal == "risk_off"

    def test_signal_risk_on_when_low(self):
        sr = ENG.stablecoin_ratio(UNIVERSE, risk_off_threshold=0.50)
        assert sr.signal == "risk_on"

    def test_to_dict(self):
        d = ENG.stablecoin_ratio(UNIVERSE).to_dict()
        assert "ratio" in d and "signal" in d


class TestCycleIndicator:
    def test_returns_cycle_indicator(self):
        ci = ENG.cycle_indicator(80000.0, 100000.0, [0.01] * 90, 0.3, 0.08)
        assert isinstance(ci, CycleIndicator)

    def test_extreme_drawdown_is_markdown(self):
        ci = ENG.cycle_indicator(20000.0, 100000.0, [-0.01] * 90, 0.2, 0.20)
        assert ci.cycle_phase == CyclePhase.MARKDOWN

    def test_low_drawdown_positive_momentum_is_markup(self):
        ci = ENG.cycle_indicator(96000.0, 100000.0, [0.002] * 90, 0.3, 0.05)
        assert ci.cycle_phase == CyclePhase.MARKUP

    def test_fear_greed_in_range(self):
        ci = ENG.cycle_indicator(80000.0, 100000.0, [0.0] * 90, 0.25, 0.10)
        assert 0.0 <= ci.fear_greed_score <= 100.0

    def test_sentiment_valid(self):
        ci = ENG.cycle_indicator(80000.0, 100000.0, [0.0] * 90, 0.25, 0.10)
        assert ci.sentiment in list(MarketSentiment)

    def test_risk_level_valid(self):
        ci = ENG.cycle_indicator(80000.0, 100000.0, [0.0] * 90, 0.25, 0.10)
        assert ci.risk_level in ("low", "medium", "high")

    def test_to_dict(self):
        ci = ENG.cycle_indicator(80000.0, 100000.0, [0.0] * 30, 0.3, 0.08)
        d = ci.to_dict()
        assert "cycle_phase" in d and "fear_greed_score" in d


class TestSectorPerformance:
    def test_returns_dict(self):
        rets = {"BTC": 0.05, "ETH": 0.03, "USDT": 0.0, "LINK": -0.01, "SOL": 0.02}
        perf = ENG.sector_performance(UNIVERSE, rets)
        assert isinstance(perf, dict)

    def test_has_layer1(self):
        rets = {"BTC": 0.05, "ETH": 0.03, "SOL": 0.02}
        perf = ENG.sector_performance(UNIVERSE, rets)
        assert "layer1" in perf

    def test_sector_return_float(self):
        rets = {"BTC": 0.05}
        perf = ENG.sector_performance(UNIVERSE, rets)
        for sec, data in perf.items():
            assert isinstance(data["return"], float)
            assert isinstance(data["weight"], float)


class TestClassifyAsset:
    def test_stablecoin(self):
        assert ENG.classify_asset("USDT", "Tether USD Stablecoin") == CryptoSector.STABLECOIN

    def test_defi(self):
        assert ENG.classify_asset("UNI", "Uniswap DEX AMM Swap") == CryptoSector.DEFI

    def test_oracle(self):
        assert ENG.classify_asset("LINK", "Chainlink Oracle") == CryptoSector.ORACLE

    def test_layer1_bitcoin(self):
        assert ENG.classify_asset("BTC", "Bitcoin") == CryptoSector.LAYER1

    def test_gaming(self):
        assert ENG.classify_asset("AXS", "Axie Infinity Gaming") == CryptoSector.GAMING

    def test_other_fallback(self):
        assert ENG.classify_asset("RAND", "Random Token XYZ") == CryptoSector.OTHER


class TestSingleton:
    def test_singleton(self):
        a = get_crypto_engine()
        b = get_crypto_engine()
        assert a is b
