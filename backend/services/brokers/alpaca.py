"""Alpaca Markets broker adapter (architecture stub).

Production implementation requires:
  - alpaca-trade-api or alpaca-py SDK
  - ALPACA_API_KEY, ALPACA_SECRET_KEY in credentials
  - base_url in config ('https://paper-api.alpaca.markets' or live)

All methods raise NotImplementedError for now; the adapter satisfies the
BrokerAdapter interface so the rest of the system can reference ALPACA
connections without import errors.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.brokers.base import BrokerAdapter


class AlpacaAdapter(BrokerAdapter):

    def connect(self) -> bool:
        raise NotImplementedError("Alpaca adapter: install alpaca-py and implement")

    def disconnect(self) -> None:
        pass

    def is_connected(self) -> bool:
        return False

    def ping(self) -> bool:
        return False

    def get_quote(self, ticker: str) -> Dict[str, Any]:
        raise NotImplementedError

    def get_quotes(self, tickers: List[str]) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def submit_order(self, order_params: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def cancel_order(self, broker_order_id: str) -> bool:
        raise NotImplementedError

    def modify_order(self, broker_order_id: str, modifications: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def get_order(self, broker_order_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    def get_open_orders(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def get_positions(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def get_account(self) -> Dict[str, Any]:
        raise NotImplementedError

    def get_executions(self, since_timestamp: Optional[str] = None) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def subscribe_quotes(self, tickers: List[str], callback: Any) -> None:
        raise NotImplementedError

    def subscribe_orders(self, callback: Any) -> None:
        raise NotImplementedError

    @property
    def broker_type(self) -> str:
        return "ALPACA"

    @property
    def supports_streaming(self) -> bool:
        return True

    @property
    def supports_fractional_shares(self) -> bool:
        return True
