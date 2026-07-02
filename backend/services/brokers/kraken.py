"""Kraken crypto exchange adapter (architecture stub).

Production implementation requires:
  - krakenex or pykrakenapi SDK
  - api_key, api_secret in credentials

All methods raise NotImplementedError; satisfies BrokerAdapter interface.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.brokers.base import BrokerAdapter


class KrakenAdapter(BrokerAdapter):

    def connect(self) -> bool:
        raise NotImplementedError("Kraken adapter: install krakenex and implement")

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

    @property
    def broker_type(self) -> str:
        return "KRAKEN"

    @property
    def supports_fractional_shares(self) -> bool:
        return True
