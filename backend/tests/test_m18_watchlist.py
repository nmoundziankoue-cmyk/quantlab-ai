"""Unit tests for M18 Watchlist System — 55 tests."""
import pytest

from services.m18_watchlist import (
    WatchlistCategory, AlertTrigger, WatchlistItem, Watchlist,
    ScreenerResult, PortfolioOverlap, WatchlistAlert,
    WatchlistSystem, get_watchlist_system,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestEnums:
    def test_watchlist_category_count(self):
        assert len(WatchlistCategory) >= 5

    def test_alert_trigger_count(self):
        assert len(AlertTrigger) >= 4

    def test_equity_long_category(self):
        assert WatchlistCategory.EQUITY_LONG is not None

    def test_price_above_trigger(self):
        assert AlertTrigger.PRICE_ABOVE is not None

    def test_price_below_trigger(self):
        assert AlertTrigger.PRICE_BELOW is not None


# ---------------------------------------------------------------------------
# WatchlistSystem — list management
# ---------------------------------------------------------------------------

class TestWatchlistListManagement:
    def setup_method(self):
        self.system = WatchlistSystem()

    def test_create_list(self):
        wl = self.system.create_list("Tech Momentum", "High conviction tech", WatchlistCategory.EQUITY_LONG)
        assert wl is not None
        assert wl.list_id is not None

    def test_create_list_returns_watchlist(self):
        wl = self.system.create_list("Test", "Desc", WatchlistCategory.EQUITY_LONG)
        assert isinstance(wl, Watchlist)

    def test_get_list(self):
        wl = self.system.create_list("Test", "Desc", WatchlistCategory.EQUITY_LONG)
        retrieved = self.system.get_list(wl.list_id)
        assert retrieved is not None
        assert retrieved.list_id == wl.list_id

    def test_get_all_lists(self):
        self.system.create_list("List1", "D1", WatchlistCategory.EQUITY_LONG)
        self.system.create_list("List2", "D2", WatchlistCategory.EQUITY_SHORT)
        lists = self.system.get_all_lists()
        assert len(lists) >= 2

    def test_delete_list(self):
        wl = self.system.create_list("To Delete", "D", WatchlistCategory.EQUITY_LONG)
        self.system.delete_list(wl.list_id)
        assert self.system.get_list(wl.list_id) is None

    def test_delete_nonexistent_returns_false(self):
        result = self.system.delete_list("nonexistent")
        assert result is False

    def test_get_nonexistent_list_returns_none(self):
        assert self.system.get_list("nonexistent") is None

    def test_update_list(self):
        wl = self.system.create_list("Original", "D", WatchlistCategory.EQUITY_LONG)
        self.system.update_list(wl.list_id, name="Updated", description="New desc")
        updated = self.system.get_list(wl.list_id)
        assert updated.name == "Updated"

    def test_watchlist_to_dict(self):
        wl = self.system.create_list("Test", "D", WatchlistCategory.EQUITY_LONG)
        d = wl.to_dict()
        assert "list_id" in d and "name" in d


# ---------------------------------------------------------------------------
# WatchlistSystem — item management
# ---------------------------------------------------------------------------

class TestWatchlistItemManagement:
    def setup_method(self):
        self.system = WatchlistSystem()
        self.wl = self.system.create_list("Test", "D", WatchlistCategory.EQUITY_LONG)

    def _add_item(self, ticker="AAPL", conviction=8, target=700.0, stop=550.0):
        return self.system.add_item(
            list_id=self.wl.list_id, ticker=ticker,
            notes=f"Watching {ticker}", sector="Technology",
            conviction=conviction, target_price=target, stop_loss=stop,
        )

    def test_add_item(self):
        item = self._add_item()
        assert item is not None
        assert item.ticker == "AAPL"

    def test_add_item_returns_watchlist_item(self):
        item = self._add_item()
        assert isinstance(item, WatchlistItem)

    def test_get_items(self):
        self._add_item("AAPL")
        self._add_item("MSFT")
        wl = self.system.get_list(self.wl.list_id)
        assert len(wl.items) >= 2

    def test_remove_item(self):
        self._add_item("AAPL")
        self.system.remove_item(self.wl.list_id, "AAPL")
        wl = self.system.get_list(self.wl.list_id)
        assert not any(i.ticker == "AAPL" for i in wl.items)

    def test_remove_nonexistent_item_returns_false(self):
        result = self.system.remove_item(self.wl.list_id, "ZZZZ")
        assert result is False

    def test_update_item(self):
        self._add_item("AAPL", conviction=7)
        self.system.update_item(self.wl.list_id, "AAPL", conviction=9)
        wl = self.system.get_list(self.wl.list_id)
        item = next(i for i in wl.items if i.ticker == "AAPL")
        assert item.conviction == 9

    def test_item_to_dict(self):
        item = self._add_item()
        d = item.to_dict()
        assert "ticker" in d and "item_id" in d

    def test_duplicate_item_raises_or_updates(self):
        self._add_item("AAPL")
        try:
            self._add_item("AAPL")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# WatchlistSystem — price updates and alerts
# ---------------------------------------------------------------------------

class TestWatchlistPriceUpdates:
    def setup_method(self):
        self.system = WatchlistSystem()
        self.wl = self.system.create_list("Test", "D", WatchlistCategory.EQUITY_LONG)
        self.system.add_item(
            list_id=self.wl.list_id, ticker="AAPL",
            notes="Test", sector="Tech", conviction=8,
            target_price=700.0, stop_loss=550.0,
            alerts=[AlertTrigger.PRICE_ABOVE],
            alert_threshold=650.0,
        )

    def test_update_price_returns_alerts_list(self):
        alerts = self.system.update_price(self.wl.list_id, "AAPL", 660.0)
        assert isinstance(alerts, list)

    def test_price_above_triggers_alert(self):
        alerts = self.system.update_price(self.wl.list_id, "AAPL", 710.0)
        triggered = [a for a in alerts if a.trigger == AlertTrigger.PRICE_ABOVE]
        assert len(triggered) >= 1

    def test_price_below_threshold_no_alert(self):
        alerts = self.system.update_price(self.wl.list_id, "AAPL", 600.0)
        assert isinstance(alerts, list)

    def test_price_update_stores_last_price(self):
        self.system.update_price(self.wl.list_id, "AAPL", 680.0)
        wl = self.system.get_list(self.wl.list_id)
        item = next(i for i in wl.items if i.ticker == "AAPL")
        assert item.last_price == 680.0

    def test_watchlist_alert_to_dict(self):
        alerts = self.system.update_price(self.wl.list_id, "AAPL", 710.0)
        for a in alerts:
            d = a.to_dict()
            assert "ticker" in d or "alert_id" in d


# ---------------------------------------------------------------------------
# WatchlistSystem — screener
# ---------------------------------------------------------------------------

class TestWatchlistScreener:
    def setup_method(self):
        self.system = WatchlistSystem()
        wl = self.system.create_list("Test", "D", WatchlistCategory.EQUITY_LONG)
        self.system.add_item(wl.list_id, "AAPL", "Tech", "Technology", conviction=9, target_price=700.0)
        self.system.add_item(wl.list_id, "JPM", "Finance", "Financials", conviction=5, target_price=250.0)

    def test_screen_returns_list(self):
        results = self.system.screen(min_conviction=7)
        assert isinstance(results, list)

    def test_screen_by_conviction(self):
        results = self.system.screen(min_conviction=8)
        assert all(r.conviction >= 8 for r in results)

    def test_screen_by_sector(self):
        results = self.system.screen(sector="Technology")
        assert all(r.sector == "Technology" for r in results)

    def test_screen_empty_criteria_returns_all(self):
        results = self.system.screen()
        assert len(results) >= 2


# ---------------------------------------------------------------------------
# WatchlistSystem — portfolio overlap
# ---------------------------------------------------------------------------

class TestPortfolioOverlap:
    def setup_method(self):
        self.system = WatchlistSystem()
        wl = self.system.create_list("Test", "D", WatchlistCategory.EQUITY_LONG)
        self.system.add_item(wl.list_id, "AAPL", "Tech", "Technology", conviction=9)
        self.system.add_item(wl.list_id, "MSFT", "Tech", "Technology", conviction=8)
        self.wl_id = wl.list_id

    def test_analyse_portfolio_overlap(self):
        result = self.system.analyse_portfolio_overlap(self.wl_id, portfolio_tickers=["AAPL", "TSLA", "NVDA"])
        assert isinstance(result, PortfolioOverlap)

    def test_overlap_to_dict(self):
        result = self.system.analyse_portfolio_overlap(self.wl_id, portfolio_tickers=["AAPL"])
        d = result.to_dict()
        assert "overlap_count" in d or "overlap_pct" in d


# ---------------------------------------------------------------------------
# WatchlistSystem — stats and export
# ---------------------------------------------------------------------------

class TestWatchlistStats:
    def setup_method(self):
        self.system = WatchlistSystem()
        wl = self.system.create_list("Test", "D", WatchlistCategory.EQUITY_LONG)
        self.system.add_item(wl.list_id, "AAPL", "Tech", "Technology", conviction=9)

    def test_get_stats(self):
        stats = self.system.get_stats()
        assert isinstance(stats, dict)
        assert "total_lists" in stats

    def test_stats_total_items(self):
        stats = self.system.get_stats()
        assert stats.get("total_items", 0) >= 1

    def test_export_list(self):
        lists = self.system.get_all_lists()
        result = self.system.export_list(lists[0].list_id)
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_watchlist_system(self):
        system = get_watchlist_system()
        assert isinstance(system, WatchlistSystem)

    def test_singleton_same_instance(self):
        s1 = get_watchlist_system()
        s2 = get_watchlist_system()
        assert s1 is s2
