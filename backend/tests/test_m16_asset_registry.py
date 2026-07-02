"""M16 tests — Asset Registry."""
import pytest
from services.asset_registry import (
    AssetRegistry, AssetMetadata, AssetType, Exchange, Currency,
    Country, Sector, Industry, MarketCapBucket, CreditRating,
    get_asset_registry,
)


def _reg_asset(reg, ticker, atype=AssetType.EQUITY, **kw):
    """Helper to register an asset with minimal required args."""
    return reg.register(ticker, f"{ticker} Inc.", atype, **kw)


class TestAssetRegistryRegister:
    def setup_method(self):
        self.reg = AssetRegistry()

    def test_register_returns_asset_metadata(self):
        a = _reg_asset(self.reg, "AAPL")
        assert isinstance(a, AssetMetadata)

    def test_register_has_asset_id(self):
        a = _reg_asset(self.reg, "AAPL")
        assert isinstance(a.asset_id, str) and len(a.asset_id) > 0

    def test_register_ticker_uppercased(self):
        a = _reg_asset(self.reg, "aapl")
        assert a.ticker == "AAPL"

    def test_register_same_ticker_latest_lookup(self):
        a1 = _reg_asset(self.reg, "MSFT")
        a2 = _reg_asset(self.reg, "MSFT")
        # ticker lookup always returns the latest registration
        found = self.reg.get_by_ticker("MSFT")
        assert found.asset_id == a2.asset_id

    def test_register_multiple_distinct(self):
        _reg_asset(self.reg, "AAPL")
        _reg_asset(self.reg, "MSFT")
        assert len(self.reg.all_assets()) == 2

    def test_register_with_isin_indexed(self):
        isin = "US0231351067"
        _reg_asset(self.reg, "AMZN", isin=isin)
        a = self.reg.get_by_isin(isin)
        assert a is not None and a.ticker == "AMZN"

    def test_register_with_cusip_indexed(self):
        _reg_asset(self.reg, "JPM", cusip="46625H100")
        a = self.reg.get_by_cusip("46625H100")
        assert a is not None and a.ticker == "JPM"

    def test_register_with_sedol_indexed(self):
        _reg_asset(self.reg, "HSBA", sedol="0540528")
        a = self.reg.get_by_sedol("0540528")
        assert a is not None and a.ticker == "HSBA"

    def test_register_with_exchange(self):
        a = _reg_asset(self.reg, "IBM", exchange=Exchange.NYSE)
        assert a.exchange == Exchange.NYSE

    def test_register_with_sector(self):
        a = _reg_asset(self.reg, "NVDA", sector=Sector.TECHNOLOGY)
        assert a.sector == Sector.TECHNOLOGY


class TestAssetRegistryLookup:
    def setup_method(self):
        self.reg = AssetRegistry()
        _reg_asset(self.reg, "NVDA", sector=Sector.TECHNOLOGY)
        _reg_asset(self.reg, "AMD", sector=Sector.TECHNOLOGY)
        _reg_asset(self.reg, "SPY", AssetType.ETF)

    def test_get_by_ticker_found(self):
        a = self.reg.get_by_ticker("NVDA")
        assert a is not None and a.ticker == "NVDA"

    def test_get_by_ticker_case_insensitive(self):
        a = self.reg.get_by_ticker("nvda")
        assert a is not None

    def test_get_by_ticker_not_found(self):
        a = self.reg.get_by_ticker("ZZZZ")
        assert a is None

    def test_all_assets_count(self):
        assert len(self.reg.all_assets()) == 3

    def test_all_assets_returns_list(self):
        assert isinstance(self.reg.all_assets(), list)


class TestAssetRegistryFilter:
    def setup_method(self):
        self.reg = AssetRegistry()
        _reg_asset(self.reg, "AAPL", AssetType.EQUITY, sector=Sector.TECHNOLOGY)
        _reg_asset(self.reg, "GS", AssetType.EQUITY, sector=Sector.FINANCIALS)
        _reg_asset(self.reg, "SPY", AssetType.ETF)

    def test_filter_by_asset_type_equity(self):
        results = self.reg.filter(asset_type=AssetType.EQUITY)
        assert all(a.asset_type == AssetType.EQUITY for a in results)

    def test_filter_by_asset_type_etf(self):
        results = self.reg.filter(asset_type=AssetType.ETF)
        assert any(a.ticker == "SPY" for a in results)

    def test_filter_no_filter_returns_all(self):
        results = self.reg.filter()
        assert len(results) == 3

    def test_filter_by_sector(self):
        results = self.reg.filter(sector=Sector.TECHNOLOGY)
        assert all(a.sector == Sector.TECHNOLOGY for a in results)

    def test_filter_active_by_default_includes_all_active(self):
        results = self.reg.filter(is_active=True)
        assert len(results) == 3

    def test_filter_after_deactivate(self):
        self.reg.deactivate("GS")
        active = self.reg.filter(is_active=True)
        tickers = [a.ticker for a in active]
        assert "GS" not in tickers

    def test_filter_is_active_false_includes_inactive(self):
        self.reg.deactivate("GS")
        inactive = self.reg.filter(is_active=False)
        assert any(a.ticker == "GS" for a in inactive)


class TestAssetRegistrySearch:
    def setup_method(self):
        self.reg = AssetRegistry()
        _reg_asset(self.reg, "NVDA", description="NVIDIA Corporation GPU chipmaker")
        _reg_asset(self.reg, "AMD", description="Advanced Micro Devices chipmaker")

    def test_search_by_ticker(self):
        results = self.reg.search("NVDA")
        assert any(a.ticker == "NVDA" for a in results)

    def test_search_by_name(self):
        results = self.reg.search("NVIDIA")
        assert any(a.ticker == "NVDA" for a in results)

    def test_search_by_description(self):
        results = self.reg.search("chipmaker")
        assert len(results) == 2

    def test_search_empty_returns_all(self):
        results = self.reg.search("")
        assert len(results) >= 2

    def test_search_no_match(self):
        results = self.reg.search("ZZZNOMATCH999")
        assert results == []

    def test_search_case_insensitive(self):
        results = self.reg.search("nvda")
        assert any(a.ticker == "NVDA" for a in results)


class TestAssetRegistryStatistics:
    def setup_method(self):
        self.reg = AssetRegistry()
        _reg_asset(self.reg, "AAPL", AssetType.EQUITY)
        _reg_asset(self.reg, "BTC", AssetType.CRYPTO)

    def test_statistics_returns_dict(self):
        s = self.reg.statistics()
        assert isinstance(s, dict)

    def test_statistics_total(self):
        s = self.reg.statistics()
        assert s["total"] == 2

    def test_statistics_active(self):
        s = self.reg.statistics()
        assert s["active"] == 2

    def test_statistics_by_type(self):
        s = self.reg.statistics()
        assert "by_type" in s

    def test_statistics_inactive_after_deactivate(self):
        self.reg.deactivate("BTC")
        s = self.reg.statistics()
        assert s["inactive"] == 1

    def test_statistics_by_sector(self):
        s = self.reg.statistics()
        assert "by_sector" in s


class TestAssetMetadataToDict:
    def test_to_dict_has_ticker(self):
        reg = AssetRegistry()
        a = _reg_asset(reg, "TSLA")
        d = a.to_dict()
        assert d["ticker"] == "TSLA"

    def test_to_dict_has_asset_type(self):
        reg = AssetRegistry()
        a = _reg_asset(reg, "TSLA", AssetType.EQUITY)
        d = a.to_dict()
        assert d["asset_type"] == "equity"

    def test_to_dict_has_market_cap_bucket(self):
        reg = AssetRegistry()
        a = _reg_asset(reg, "TSLA")
        d = a.to_dict()
        assert "market_cap_bucket" in d

    def test_to_dict_has_is_active(self):
        reg = AssetRegistry()
        a = _reg_asset(reg, "X")
        d = a.to_dict()
        assert d["is_active"] is True


class TestAssetRegistrySingleton:
    def test_singleton_returns_same(self):
        a = get_asset_registry()
        b = get_asset_registry()
        assert a is b

    def test_singleton_is_asset_registry(self):
        a = get_asset_registry()
        assert isinstance(a, AssetRegistry)
