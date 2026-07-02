"""Tests for M17 Pydantic v2 schema validation (schemas/m17_trading.py)."""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from schemas.m17_trading import (
    OrderSubmitRequest, OrderAmendRequest, BracketOrderRequest, OCOOrderRequest,
    TWAPRequest, FillRequest,
    SlippageRequest, MarketImpactRequest, SimFillRequest, ExecQualityRequest, ISRequest,
    DepositRequest, WithdrawRequest, BookTradeRequest, NAVRequest,
    OpenPositionRequest, ClosePositionRequest, AddLimitRequest, PreTradeCheckRequest,
    TradeRecordRequest, PortfolioPerformanceRequest, KellyRequest,
    TCATradeRequest, BrokerRegisterRequest,
    SimMarketOrderRequest, SimLimitOrderRequest, PriceUpdateRequest,
    HoldingRequest, BrinsonRequest, FactorExposureRequest, FactorAttributionRequest,
)


# ---------------------------------------------------------------------------
# OMS schemas
# ---------------------------------------------------------------------------

class TestOrderSubmitRequest:
    def test_valid_market_order(self):
        r = OrderSubmitRequest(ticker="AAPL", order_type="MARKET", side="BUY", quantity=100)
        assert r.ticker == "AAPL"

    def test_valid_limit_order(self):
        r = OrderSubmitRequest(ticker="MSFT", order_type="LIMIT", side="SELL", quantity=50, limit_price=420.0)
        assert r.limit_price == 420.0

    def test_missing_ticker_raises(self):
        with pytest.raises(ValidationError):
            OrderSubmitRequest(order_type="MARKET", side="BUY", quantity=100)

    def test_quantity_positive(self):
        r = OrderSubmitRequest(ticker="AAPL", order_type="MARKET", side="BUY", quantity=1)
        assert r.quantity == 1

    def test_quantity_zero_raises(self):
        with pytest.raises(ValidationError):
            OrderSubmitRequest(ticker="AAPL", order_type="MARKET", side="BUY", quantity=0)


class TestFillRequest:
    def test_valid(self):
        r = FillRequest(quantity=100, price=175.0)
        assert r.price == 175.0

    def test_negative_quantity_raises(self):
        with pytest.raises(ValidationError):
            FillRequest(quantity=0, price=175.0)


class TestBracketOrderRequest:
    def test_valid(self):
        r = BracketOrderRequest(ticker="AAPL", side="BUY", quantity=100, take_profit_price=185.0, stop_loss_price=165.0)
        assert r.take_profit_price == 185.0


class TestOCOOrderRequest:
    def test_valid(self):
        r = OCOOrderRequest(ticker="AAPL", side="SELL", quantity=100, limit_price=185.0, stop_price=165.0)
        assert r.limit_price == 185.0


class TestTWAPRequest:
    def test_valid(self):
        r = TWAPRequest(ticker="AAPL", side="BUY", total_quantity=1000, n_slices=5)
        assert r.n_slices == 5

    def test_zero_slices_raises(self):
        with pytest.raises(ValidationError):
            TWAPRequest(ticker="AAPL", side="BUY", total_quantity=1000, n_slices=0)


# ---------------------------------------------------------------------------
# Execution schemas
# ---------------------------------------------------------------------------

class TestSlippageRequest:
    def test_valid(self):
        r = SlippageRequest(order_quantity=10000, arrival_price=175.0, adv=500000, volatility=0.02)
        assert r.volatility == pytest.approx(0.02)

    def test_missing_adv_raises(self):
        with pytest.raises(ValidationError):
            SlippageRequest(order_quantity=10000, arrival_price=175.0, volatility=0.02)


class TestMarketImpactRequest:
    def test_valid(self):
        r = MarketImpactRequest(order_quantity=10000, adv=500000, price=175.0, volatility=0.02)
        assert r.price == pytest.approx(175.0)


# ---------------------------------------------------------------------------
# Accounting schemas
# ---------------------------------------------------------------------------

class TestDepositRequest:
    def test_valid(self):
        r = DepositRequest(amount=1000000, description="Init")
        assert r.amount == 1000000

    def test_negative_amount_raises(self):
        with pytest.raises(ValidationError):
            DepositRequest(amount=-1000, description="Bad")


class TestWithdrawRequest:
    def test_valid(self):
        r = WithdrawRequest(amount=50000, description="Test")
        assert r.amount == 50000


class TestBookTradeRequest:
    def test_valid(self):
        r = BookTradeRequest(ticker="AAPL", side="BUY", quantity=100, avg_price=175.0, commission=2.5)
        assert r.commission == 2.5


class TestNAVRequest:
    def test_valid(self):
        r = NAVRequest(prices={"AAPL": 175.0})
        assert r.prices["AAPL"] == 175.0

    def test_empty_prices(self):
        r = NAVRequest(prices={})
        assert r.prices == {}


# ---------------------------------------------------------------------------
# Position schemas
# ---------------------------------------------------------------------------

class TestOpenPositionRequest:
    def test_valid(self):
        r = OpenPositionRequest(ticker="AAPL", quantity=100, price=175.0)
        assert r.ticker == "AAPL"

    def test_zero_quantity_raises(self):
        with pytest.raises(ValidationError):
            OpenPositionRequest(ticker="AAPL", quantity=0, price=175.0)


class TestClosePositionRequest:
    def test_valid(self):
        r = ClosePositionRequest(ticker="AAPL", quantity=50, price=180.0)
        assert r.price == 180.0


# ---------------------------------------------------------------------------
# Risk schemas
# ---------------------------------------------------------------------------

class TestAddLimitRequest:
    def test_valid(self):
        r = AddLimitRequest(limit_type="MAX_ORDER_SIZE", hard_limit=500000.0)
        assert r.hard_limit == 500000.0


class TestPreTradeCheckRequest:
    def test_valid(self):
        r = PreTradeCheckRequest(ticker="AAPL", side="BUY", quantity=100, price=175.0,
                                  nav=1000000, cash=100000, sector="TECHNOLOGY",
                                  gross_leverage=1.0, sector_weights={"TECHNOLOGY": 0.25})
        assert r.nav == 1000000


# ---------------------------------------------------------------------------
# Trade Analytics schemas
# ---------------------------------------------------------------------------

class TestTradeRecordRequest:
    def test_valid(self):
        now = datetime.now(timezone.utc).isoformat()
        r = TradeRecordRequest(trade_id="T1", ticker="AAPL", side="BUY", quantity=100,
                                entry_price=170.0, exit_price=180.0,
                                entry_datetime=now, exit_datetime=now,
                                commission=2.5, pnl=1000.0, sector="TECHNOLOGY")
        assert r.pnl == 1000.0


class TestPortfolioPerformanceRequest:
    def test_valid(self):
        r = PortfolioPerformanceRequest(returns=[0.01, 0.02, -0.005], periods_per_year=252)
        assert r.periods_per_year == 252

    def test_empty_returns_raises(self):
        with pytest.raises(ValidationError):
            PortfolioPerformanceRequest(returns=[], periods_per_year=252)


class TestKellyRequest:
    def test_valid(self):
        r = KellyRequest(win_rate=0.6, avg_win=500.0, avg_loss=300.0)
        assert r.win_rate == pytest.approx(0.6)

    def test_win_rate_out_of_range_raises(self):
        with pytest.raises(ValidationError):
            KellyRequest(win_rate=1.5, avg_win=500.0, avg_loss=300.0)


# ---------------------------------------------------------------------------
# Attribution schemas
# ---------------------------------------------------------------------------

class TestHoldingRequest:
    def test_valid(self):
        h = HoldingRequest(category="Technology", portfolio_weight=0.25,
                           benchmark_weight=0.20, portfolio_return=0.08, benchmark_return=0.05)
        assert h.category == "Technology"


class TestBrinsonRequest:
    def test_valid(self):
        h = HoldingRequest(category="Tech", portfolio_weight=0.5,
                           benchmark_weight=0.5, portfolio_return=0.08, benchmark_return=0.05)
        r = BrinsonRequest(holdings=[h], benchmark_total_return=0.05)
        assert len(r.holdings) == 1

    def test_empty_holdings_raises(self):
        with pytest.raises(ValidationError):
            BrinsonRequest(holdings=[], benchmark_total_return=0.05)


class TestFactorAttributionRequest:
    def test_valid(self):
        fe = FactorExposureRequest(factor_name="Market", portfolio_exposure=1.05,
                                   benchmark_exposure=1.0, factor_return=0.04)
        r = FactorAttributionRequest(factors=[fe])
        assert len(r.factors) == 1


# ---------------------------------------------------------------------------
# Paper Trading schemas
# ---------------------------------------------------------------------------

class TestSimOrderSchemas:
    def test_market_order_valid(self):
        r = SimMarketOrderRequest(ticker="AAPL", side="BUY", quantity=100)
        assert r.quantity == 100

    def test_limit_order_valid(self):
        r = SimLimitOrderRequest(ticker="AAPL", side="BUY", quantity=100, limit_price=175.0)
        assert r.limit_price == 175.0

    def test_price_update_valid(self):
        r = PriceUpdateRequest(prices={"AAPL": 175.0, "MSFT": 420.0})
        assert r.prices["AAPL"] == 175.0
