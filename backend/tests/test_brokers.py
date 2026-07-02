"""Tests for broker adapter registry and implementations.

Tests for the paper broker are separate (it delegates to paper_trading service).
Stubs are validated to raise NotImplementedError for all unimplemented methods.
"""
from __future__ import annotations

import pytest

from services.brokers import ADAPTER_REGISTRY, get_adapter
from services.brokers.base import BrokerAdapter
from services.brokers.paper import PaperBrokerAdapter
from services.brokers.alpaca import AlpacaAdapter
from services.brokers.ibkr import IBKRAdapter
from services.brokers.binance import BinanceAdapter
from services.brokers.kraken import KrakenAdapter
from services.brokers.oanda import OANDAAdapter


# ---------------------------------------------------------------------------
# TestRegistry
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_registry_contains_all_brokers(self):
        expected = {"PAPER", "ALPACA", "IBKR", "BINANCE", "KRAKEN", "OANDA"}
        assert expected == set(ADAPTER_REGISTRY.keys())

    def test_get_adapter_paper(self):
        adapter = get_adapter("PAPER", {}, {})
        assert isinstance(adapter, PaperBrokerAdapter)

    def test_get_adapter_alpaca(self):
        adapter = get_adapter("ALPACA", {}, {})
        assert isinstance(adapter, AlpacaAdapter)

    def test_get_adapter_ibkr(self):
        adapter = get_adapter("IBKR", {}, {})
        assert isinstance(adapter, IBKRAdapter)

    def test_get_adapter_binance(self):
        adapter = get_adapter("BINANCE", {}, {})
        assert isinstance(adapter, BinanceAdapter)

    def test_get_adapter_kraken(self):
        adapter = get_adapter("KRAKEN", {}, {})
        assert isinstance(adapter, KrakenAdapter)

    def test_get_adapter_oanda(self):
        adapter = get_adapter("OANDA", {}, {})
        assert isinstance(adapter, OANDAAdapter)

    def test_get_adapter_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown broker"):
            get_adapter("UNKNOWN", {}, {})

    def test_get_adapter_case_insensitive(self):
        adapter = get_adapter("paper", {}, {})
        assert isinstance(adapter, PaperBrokerAdapter)


# ---------------------------------------------------------------------------
# TestBrokerAdapterInterface
# ---------------------------------------------------------------------------


class TestBrokerAdapterInterface:
    def test_paper_is_broker_adapter(self):
        adapter = PaperBrokerAdapter({}, {})
        assert isinstance(adapter, BrokerAdapter)

    def test_all_adapters_are_broker_adapter(self):
        for cls in ADAPTER_REGISTRY.values():
            assert issubclass(cls, BrokerAdapter)


# ---------------------------------------------------------------------------
# TestPaperBrokerAdapter
# ---------------------------------------------------------------------------


class TestPaperBrokerAdapter:
    def test_connect_returns_true(self):
        adapter = PaperBrokerAdapter({}, {})
        assert adapter.connect() is True

    def test_is_connected_after_connect(self):
        adapter = PaperBrokerAdapter({}, {})
        adapter.connect()
        assert adapter.is_connected() is True

    def test_disconnect(self):
        adapter = PaperBrokerAdapter({}, {})
        adapter.connect()
        adapter.disconnect()
        assert adapter.is_connected() is False

    def test_ping_when_connected(self):
        adapter = PaperBrokerAdapter({}, {})
        adapter.connect()
        assert adapter.ping() is True

    def test_ping_when_disconnected(self):
        adapter = PaperBrokerAdapter({}, {})
        assert adapter.ping() is False

    def test_broker_type(self):
        adapter = PaperBrokerAdapter({}, {})
        assert adapter.broker_type == "PAPER"

    def test_supports_fractional_shares(self):
        adapter = PaperBrokerAdapter({}, {})
        assert adapter.supports_fractional_shares is True

    def test_submit_order_returns_accepted(self):
        adapter = PaperBrokerAdapter({}, {})
        result = adapter.submit_order({"client_order_id": "test-123"})
        assert result["status"] == "ACCEPTED"

    def test_cancel_order_returns_true(self):
        adapter = PaperBrokerAdapter({}, {})
        assert adapter.cancel_order("any-id") is True

    def test_get_open_orders_returns_empty(self):
        adapter = PaperBrokerAdapter({}, {})
        assert adapter.get_open_orders() == []

    def test_get_positions_returns_empty(self):
        adapter = PaperBrokerAdapter({}, {})
        assert adapter.get_positions() == []

    def test_get_executions_returns_empty(self):
        adapter = PaperBrokerAdapter({}, {})
        assert adapter.get_executions() == []


# ---------------------------------------------------------------------------
# TestStubAdaptersRaiseNotImplemented
# ---------------------------------------------------------------------------


STUB_ADAPTERS = [AlpacaAdapter, IBKRAdapter, BinanceAdapter, KrakenAdapter, OANDAAdapter]


class TestStubAdaptersRaiseNotImplemented:
    @pytest.mark.parametrize("cls", STUB_ADAPTERS)
    def test_connect_raises(self, cls):
        adapter = cls({}, {})
        with pytest.raises(NotImplementedError):
            adapter.connect()

    @pytest.mark.parametrize("cls", STUB_ADAPTERS)
    def test_is_connected_returns_false(self, cls):
        adapter = cls({}, {})
        assert adapter.is_connected() is False

    @pytest.mark.parametrize("cls", STUB_ADAPTERS)
    def test_get_quote_raises(self, cls):
        adapter = cls({}, {})
        with pytest.raises(NotImplementedError):
            adapter.get_quote("AAPL")

    @pytest.mark.parametrize("cls", STUB_ADAPTERS)
    def test_submit_order_raises(self, cls):
        adapter = cls({}, {})
        with pytest.raises(NotImplementedError):
            adapter.submit_order({})

    @pytest.mark.parametrize("cls", STUB_ADAPTERS)
    def test_get_positions_raises(self, cls):
        adapter = cls({}, {})
        with pytest.raises(NotImplementedError):
            adapter.get_positions()

    @pytest.mark.parametrize("cls", STUB_ADAPTERS)
    def test_get_account_raises(self, cls):
        adapter = cls({}, {})
        with pytest.raises(NotImplementedError):
            adapter.get_account()

    @pytest.mark.parametrize("cls", STUB_ADAPTERS)
    def test_broker_type_defined(self, cls):
        adapter = cls({}, {})
        assert isinstance(adapter.broker_type, str)
        assert len(adapter.broker_type) > 0
