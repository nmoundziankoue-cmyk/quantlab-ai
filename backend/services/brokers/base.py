"""Abstract broker adapter interface.

Every concrete broker must implement this interface.  The OMS/EMS layers
interact exclusively with BrokerAdapter — they never call broker-specific
APIs directly.
"""
from __future__ import annotations

import abc
from decimal import Decimal
from typing import Any, Dict, List, Optional


class BrokerAdapter(abc.ABC):
    """Unified broker interface.

    All monetary values use Decimal.  All IDs are strings (broker-native).
    """

    def __init__(self, credentials: Dict[str, Any], config: Dict[str, Any]) -> None:
        self.credentials = credentials
        self.config = config

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def connect(self) -> bool:
        """Establish connection / authenticate.  Returns True on success."""

    @abc.abstractmethod
    def disconnect(self) -> None:
        """Gracefully close connection."""

    @abc.abstractmethod
    def is_connected(self) -> bool:
        """Return True if the broker session is currently active."""

    @abc.abstractmethod
    def ping(self) -> bool:
        """Send a heartbeat / health check.  Returns True if broker responds."""

    # ------------------------------------------------------------------
    # Market data
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def get_quote(self, ticker: str) -> Dict[str, Any]:
        """Return current bid/ask/last price for ticker.

        Required keys: ticker, bid, ask, last, volume, timestamp
        """

    @abc.abstractmethod
    def get_quotes(self, tickers: List[str]) -> List[Dict[str, Any]]:
        """Batch quote retrieval."""

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def submit_order(self, order_params: Dict[str, Any]) -> Dict[str, Any]:
        """Submit an order to the broker.

        order_params keys: ticker, side, quantity, order_type, limit_price?,
        stop_price?, time_in_force, client_order_id

        Returns dict with: broker_order_id, status, submitted_at
        """

    @abc.abstractmethod
    def cancel_order(self, broker_order_id: str) -> bool:
        """Request cancellation.  Returns True if successfully cancelled."""

    @abc.abstractmethod
    def modify_order(self, broker_order_id: str, modifications: Dict[str, Any]) -> Dict[str, Any]:
        """Modify a live order.  Returns updated order dict."""

    @abc.abstractmethod
    def get_order(self, broker_order_id: str) -> Dict[str, Any]:
        """Fetch single order status from broker."""

    @abc.abstractmethod
    def get_open_orders(self) -> List[Dict[str, Any]]:
        """Return all open/pending orders."""

    # ------------------------------------------------------------------
    # Positions & Account
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """Return all current positions.

        Each position dict: ticker, quantity, average_cost, market_value,
        unrealized_pnl, side
        """

    @abc.abstractmethod
    def get_account(self) -> Dict[str, Any]:
        """Return account summary.

        Required keys: cash, buying_power, total_equity, currency
        """

    # ------------------------------------------------------------------
    # Executions
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def get_executions(self, since_timestamp: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return fills.  Each dict: broker_order_id, ticker, side, quantity,
        fill_price, commission, venue, execution_time
        """

    # ------------------------------------------------------------------
    # Streaming (optional — adapters that don't support streaming raise
    # NotImplementedError which the OMS handles gracefully)
    # ------------------------------------------------------------------

    def subscribe_quotes(self, tickers: List[str], callback: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} does not support streaming quotes")

    def subscribe_orders(self, callback: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} does not support order streaming")

    def unsubscribe_all(self) -> None:
        pass  # no-op for non-streaming adapters

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @property
    @abc.abstractmethod
    def broker_type(self) -> str:
        """Return canonical broker type string (e.g. 'ALPACA', 'IBKR')."""

    @property
    def supports_streaming(self) -> bool:
        return False

    @property
    def supports_fractional_shares(self) -> bool:
        return False

    @property
    def supports_extended_hours(self) -> bool:
        return False
