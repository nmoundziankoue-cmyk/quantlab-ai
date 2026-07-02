"""Broker adapter registry.

Usage:
    from services.brokers import get_adapter, ADAPTER_REGISTRY
    adapter = get_adapter("PAPER", config={})
"""
from services.brokers.base import BrokerAdapter
from services.brokers.paper import PaperBrokerAdapter
from services.brokers.alpaca import AlpacaAdapter
from services.brokers.ibkr import IBKRAdapter
from services.brokers.binance import BinanceAdapter
from services.brokers.kraken import KrakenAdapter
from services.brokers.oanda import OANDAAdapter

ADAPTER_REGISTRY: dict[str, type[BrokerAdapter]] = {
    "PAPER": PaperBrokerAdapter,
    "ALPACA": AlpacaAdapter,
    "IBKR": IBKRAdapter,
    "BINANCE": BinanceAdapter,
    "KRAKEN": KrakenAdapter,
    "OANDA": OANDAAdapter,
}


def get_adapter(broker_type: str, credentials: dict, config: dict) -> BrokerAdapter:
    cls = ADAPTER_REGISTRY.get(broker_type.upper())
    if cls is None:
        raise ValueError(f"Unknown broker type: {broker_type}")
    return cls(credentials=credentials, config=config)


__all__ = [
    "BrokerAdapter",
    "PaperBrokerAdapter",
    "AlpacaAdapter",
    "IBKRAdapter",
    "BinanceAdapter",
    "KrakenAdapter",
    "OANDAAdapter",
    "ADAPTER_REGISTRY",
    "get_adapter",
]
