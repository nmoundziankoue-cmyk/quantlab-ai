"""Paper broker adapter.

Wraps the paper_trading service to satisfy the BrokerAdapter interface.
All operations are in-memory / database-backed (no network I/O).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from services.brokers.base import BrokerAdapter


class PaperBrokerAdapter(BrokerAdapter):
    """Paper (simulated) broker backed by the paper_trading service.

    quote data is fetched via the market_data / quotes service to provide
    realistic fill prices.
    """

    def __init__(self, credentials: Dict[str, Any], config: Dict[str, Any]) -> None:
        super().__init__(credentials, config)
        self._connected = False

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def ping(self) -> bool:
        return self._connected

    # ------------------------------------------------------------------
    # Market data (delegated to quotes service at call time)
    # ------------------------------------------------------------------

    def get_quote(self, ticker: str) -> Dict[str, Any]:
        from services.quotes import get_current_prices
        prices = get_current_prices([ticker])
        price = prices.get(ticker)
        if price is None:
            raise ValueError(f"No quote available for {ticker}")
        return {
            "ticker": ticker,
            "bid": float(price) * 0.9999,
            "ask": float(price) * 1.0001,
            "last": float(price),
            "volume": 0,
            "timestamp": None,
        }

    def get_quotes(self, tickers: List[str]) -> List[Dict[str, Any]]:
        from services.quotes import get_current_prices
        prices = get_current_prices(tickers)
        result = []
        for ticker in tickers:
            price = prices.get(ticker)
            if price is not None:
                result.append({
                    "ticker": ticker,
                    "bid": float(price) * 0.9999,
                    "ask": float(price) * 1.0001,
                    "last": float(price),
                    "volume": 0,
                    "timestamp": None,
                })
        return result

    # ------------------------------------------------------------------
    # Orders — paper engine handles everything; these are stubs that the
    # OMS service will call after it processes the order internally.
    # ------------------------------------------------------------------

    def submit_order(self, order_params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "broker_order_id": order_params.get("client_order_id", "PAPER"),
            "status": "ACCEPTED",
            "submitted_at": None,
        }

    def cancel_order(self, broker_order_id: str) -> bool:
        return True

    def modify_order(self, broker_order_id: str, modifications: Dict[str, Any]) -> Dict[str, Any]:
        return {"broker_order_id": broker_order_id, "status": "MODIFIED"}

    def get_order(self, broker_order_id: str) -> Dict[str, Any]:
        return {"broker_order_id": broker_order_id, "status": "FILLED"}

    def get_open_orders(self) -> List[Dict[str, Any]]:
        return []

    # ------------------------------------------------------------------
    # Positions & Account — delegated to paper_trading service
    # ------------------------------------------------------------------

    def get_positions(self) -> List[Dict[str, Any]]:
        return []

    def get_account(self) -> Dict[str, Any]:
        return {
            "cash": Decimal("0"),
            "buying_power": Decimal("0"),
            "total_equity": Decimal("0"),
            "currency": "USD",
        }

    def get_executions(self, since_timestamp: Optional[str] = None) -> List[Dict[str, Any]]:
        return []

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @property
    def broker_type(self) -> str:
        return "PAPER"

    @property
    def supports_fractional_shares(self) -> bool:
        return True
