"""Interactive Brokers TWS adapter (architecture stub).

Production implementation requires:
  - ib_insync or ibapi SDK
  - IB Gateway / TWS running locally or via IBC
  - host/port/client_id in config

All methods raise NotImplementedError; satisfies BrokerAdapter interface.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.brokers.base import BrokerAdapter


class IBKRAdapter(BrokerAdapter):

    def connect(self) -> bool:
        raise NotImplementedError("IBKR adapter: install ib_insync and implement")

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
        return "IBKR"

    @property
    def supports_streaming(self) -> bool:
        return True

    @property
    def supports_extended_hours(self) -> bool:
        return True
