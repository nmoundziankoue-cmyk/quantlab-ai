"""M17 — Institutional Trading & Portfolio Management API Router.

Provides 35 endpoints under the /trading prefix covering:
  OMS        — order lifecycle, bracket, OCO, TWAP, VWAP, trailing stop
  Execution  — slippage, market impact, IS, VWAP/TWAP computation, sim fill
  Accounting — deposit, withdraw, book trade, split, dividend, NAV, snapshot
  Positions  — open/close lot, exposure, snapshot
  Risk       — add limit, pre-trade check, list limits
  Analytics  — add trades, statistics, sector attribution, performance
  TCA        — analyse trade, record, report, broker scorecards
  Brokers    — register, commission schedule, routing, rank
  Paper Sim  — market/limit order, price update, account state, reset
  Attribution— Brinson, factor, full report, IR, TE
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from schemas.m17_trading import (
    AddLimitRequest,
    BracketOrderRequest,
    BrinsonRequest,
    BrokerExecutionRequest,
    BrokerRegisterRequest,
    BookTradeRequest,
    CommissionComputeRequest,
    CommissionScheduleRequest,
    ClosePositionRequest,
    DepositRequest,
    DividendRequest,
    ExecQualityRequest,
    ExposureRequest,
    FactorAttributionRequest,
    FillRequest,
    FullAttributionRequest,
    IRRequest,
    ISRequest,
    KellyRequest,
    MarketImpactRequest,
    MarkToMarketRequest,
    NAVRequest,
    OCOOrderRequest,
    OpenPositionRequest,
    OrderAmendRequest,
    OrderQueryRequest,
    OrderSubmitRequest,
    PortfolioPerformanceRequest,
    PositionRequest,
    PreTradeCheckRequest,
    PriceUpdateRequest,
    RecordTCATradeRequest,
    RouteOrderRequest,
    RoutingRuleRequest,
    SimFillRequest,
    SimLimitOrderRequest,
    SimMarketOrderRequest,
    SimResetRequest,
    SlippageRequest,
    SplitRequest,
    TCATradeRequest,
    TWAPComputeRequest,
    TWAPRequest,
    TradeRecordRequest,
    TrailingStopUpdateRequest,
    VWAPComputeRequest,
    VWAPRequest,
    WithdrawRequest,
)
from services.order_management import (
    OMSEngine, OrderType, OrderSide, TimeInForce, get_oms_engine,
)
from services.execution_engine import get_execution_engine
from services.portfolio_accounting import get_portfolio_accounting_engine
from services.position_engine import get_position_engine
from services.risk_limits import (
    get_risk_limits_engine, RiskContext, ProposedOrder, LimitType,
)
from services.trade_analytics import (
    get_trade_analytics_engine, TradeRecord,
)
from services.tca import get_tca_engine
from services.broker_management import (
    get_broker_management_engine, AssetClass, CommissionType, RoutingStrategy,
)
from services.paper_trading_sim import get_paper_trading_simulator
from services.performance_attribution import (
    get_performance_attribution_engine, Holding, FactorExposure, AttributionModel,
)

router = APIRouter(prefix="/trading", tags=["M17 — Institutional Trading"])


# ===========================================================================
# OMS — Order Management
# ===========================================================================

@router.post("/orders/submit")
def submit_order(req: OrderSubmitRequest) -> Dict:
    """Submit a new order to the OMS."""
    oms = get_oms_engine()
    try:
        order = oms.submit_order(
            req.ticker, OrderType(req.order_type), OrderSide(req.side),
            req.quantity,
            time_in_force=TimeInForce(req.time_in_force),
            limit_price=req.limit_price,
            stop_price=req.stop_price,
            trail_amount=req.trail_amount,
            trail_type=__import__("services.order_management", fromlist=["TrailType"]).TrailType(req.trail_type) if req.trail_type else None,
            iceberg_visible_qty=req.iceberg_visible_qty,
            expires_at=req.expires_at,
            broker_id=req.broker_id,
            strategy_tag=req.strategy_tag,
            notes=req.notes,
            client_order_id=req.client_order_id,
            order_params=req.order_params,
        )
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return order.to_dict()


@router.get("/orders")
def list_orders(ticker: Optional[str] = None, status: Optional[str] = None) -> Dict:
    """List all orders with optional filters."""
    oms = get_oms_engine()
    orders = oms.get_orders(ticker=ticker)
    if status:
        from services.order_management import OrderStatus
        try:
            s = OrderStatus(status)
            orders = [o for o in orders if o.status == s]
        except ValueError:
            pass
    return {"orders": [o.to_dict() for o in orders], "count": len(orders)}


@router.get("/orders/open")
def get_open_orders(ticker: Optional[str] = None) -> Dict:
    """Get all open (non-terminal) orders."""
    oms = get_oms_engine()
    orders = oms.get_open_orders(ticker=ticker)
    return {"orders": [o.to_dict() for o in orders], "count": len(orders)}


@router.get("/orders/summary")
def order_summary() -> Dict:
    """Return aggregate order statistics."""
    return get_oms_engine().order_summary()


@router.get("/orders/{order_id}")
def get_order(order_id: str) -> Dict:
    """Retrieve an order by ID."""
    order = get_oms_engine().get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Order {order_id!r} not found")
    return order.to_dict()


@router.patch("/orders/{order_id}/amend")
def amend_order(order_id: str, req: OrderAmendRequest) -> Dict:
    """Amend a working order's price or quantity."""
    try:
        order = get_oms_engine().amend_order(
            order_id,
            quantity=req.quantity,
            limit_price=req.limit_price,
            stop_price=req.stop_price,
            trail_amount=req.trail_amount,
            expires_at=req.expires_at,
        )
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return order.to_dict()


@router.post("/orders/{order_id}/cancel")
def cancel_order(order_id: str) -> Dict:
    """Cancel a working order."""
    try:
        order = get_oms_engine().cancel_order(order_id)
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return order.to_dict()


@router.post("/orders/{order_id}/fill")
def record_fill(order_id: str, req: FillRequest) -> Dict:
    """Record a fill for an order."""
    try:
        fill = get_oms_engine().record_fill(
            order_id, req.quantity, req.price,
            venue=req.venue, commission=req.commission, fees=req.fees,
        )
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return fill.to_dict()


@router.post("/orders/bracket")
def create_bracket(req: BracketOrderRequest) -> Dict:
    """Create a bracket order (entry + take-profit + stop-loss)."""
    try:
        result = get_oms_engine().create_bracket(
            req.ticker, OrderSide(req.side), req.quantity,
            req.entry_price, req.take_profit_price, req.stop_loss_price,
            entry_order_type=OrderType(req.entry_order_type),
            broker_id=req.broker_id,
            strategy_tag=req.strategy_tag,
        )
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result.to_dict()


@router.post("/orders/oco")
def create_oco(req: OCOOrderRequest) -> Dict:
    """Create a One-Cancels-Other order pair."""
    try:
        result = get_oms_engine().create_oco(
            req.ticker, OrderSide(req.side), req.quantity,
            req.limit_price, req.stop_price,
            broker_id=req.broker_id,
            strategy_tag=req.strategy_tag,
        )
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result.to_dict()


@router.post("/orders/twap")
def generate_twap(req: TWAPRequest) -> Dict:
    """Generate TWAP parent + child slice orders."""
    try:
        parent, children = get_oms_engine().generate_twap_children(
            req.ticker, OrderSide(req.side), req.total_quantity, req.n_slices,
            limit_price=req.limit_price,
            broker_id=req.broker_id,
            strategy_tag=req.strategy_tag,
        )
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"parent": parent.to_dict(), "children": [c.to_dict() for c in children]}


@router.post("/orders/vwap")
def generate_vwap(req: VWAPRequest) -> Dict:
    """Generate VWAP parent + volume-weighted child orders."""
    try:
        parent, children = get_oms_engine().generate_vwap_children(
            req.ticker, OrderSide(req.side), req.total_quantity, req.volume_profile,
            limit_price=req.limit_price,
            broker_id=req.broker_id,
            strategy_tag=req.strategy_tag,
        )
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"parent": parent.to_dict(), "children": [c.to_dict() for c in children]}


@router.post("/orders/{order_id}/trailing-stop/update")
def update_trailing_stop(order_id: str, req: TrailingStopUpdateRequest) -> Dict:
    """Update a trailing stop price based on current market price."""
    try:
        order = get_oms_engine().update_trailing_stop(order_id, req.current_price)
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return order.to_dict()


@router.post("/orders/expire-day")
def expire_day_orders() -> Dict:
    """Expire all DAY / IOC / FOK orders."""
    expired = get_oms_engine().expire_day_orders()
    return {"expired_count": len(expired), "orders": [o.to_dict() for o in expired]}


# ===========================================================================
# Execution Engine
# ===========================================================================

@router.post("/execution/slippage")
def estimate_slippage(req: SlippageRequest) -> Dict:
    """Estimate execution slippage for an order."""
    from services.execution_engine import SlippageModel
    try:
        result = get_execution_engine().estimate_slippage(
            req.order_quantity, req.arrival_price, req.adv, req.volatility,
            model=SlippageModel(req.model),
            fixed_bps=req.fixed_bps,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result.to_dict()


@router.post("/execution/market-impact")
def estimate_market_impact(req: MarketImpactRequest) -> Dict:
    """Estimate market impact (permanent + temporary components)."""
    from services.execution_engine import MarketImpactModel
    try:
        result = get_execution_engine().estimate_market_impact(
            req.order_quantity, req.adv, req.price, req.volatility,
            model=MarketImpactModel(req.model),
            sigma_perm=req.sigma_perm,
            sigma_temp=req.sigma_temp,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result.to_dict()


@router.post("/execution/implementation-shortfall")
def implementation_shortfall(req: ISRequest) -> Dict:
    """Compute implementation shortfall decomposition."""
    try:
        result = get_execution_engine().implementation_shortfall(
            req.decision_price, req.arrival_price, req.avg_fill_price,
            req.total_quantity, req.filled_quantity,
            req.spread_bps, req.is_buy,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result.to_dict()


@router.post("/execution/vwap")
def compute_vwap(req: VWAPComputeRequest) -> Dict:
    """Compute VWAP from a price/volume series."""
    try:
        result = get_execution_engine().compute_vwap(req.prices, req.volumes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result.to_dict()


@router.post("/execution/twap")
def compute_twap(req: TWAPComputeRequest) -> Dict:
    """Compute TWAP from a price series."""
    try:
        result = get_execution_engine().compute_twap(req.prices)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result.to_dict()


@router.post("/execution/simulate-fill")
def simulate_fill(req: SimFillRequest) -> Dict:
    """Simulate a deterministic order fill with spread and slippage."""
    try:
        result = get_execution_engine().simulate_fill(
            req.ticker, req.side, req.quantity, req.arrival_price,
            req.adv, req.volatility,
            spread_bps=req.spread_bps,
            fill_rate=req.fill_rate,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result.to_dict()


@router.post("/execution/quality")
def execution_quality(req: ExecQualityRequest) -> Dict:
    """Score execution quality against a benchmark."""
    from services.execution_engine import ExecutionBenchmark
    try:
        result = get_execution_engine().execution_quality(
            req.ticker, req.side, req.avg_fill_price, req.benchmark_price,
            req.quantity, req.commission_usd,
            benchmark_type=ExecutionBenchmark(req.benchmark_type),
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result.to_dict()


# ===========================================================================
# Portfolio Accounting
# ===========================================================================

@router.post("/accounting/deposit")
def deposit(req: DepositRequest) -> Dict:
    """Credit cash to the portfolio."""
    try:
        entry = get_portfolio_accounting_engine().deposit(req.amount, req.description)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return entry.to_dict()


@router.post("/accounting/withdraw")
def withdraw(req: WithdrawRequest) -> Dict:
    """Debit cash from the portfolio."""
    try:
        entry = get_portfolio_accounting_engine().withdraw(req.amount, req.description)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return entry.to_dict()


@router.post("/accounting/book-trade")
def book_trade(req: BookTradeRequest) -> Dict:
    """Book a completed trade (updates cash, cost basis, realised P&L)."""
    try:
        entry = get_portfolio_accounting_engine().book_trade(
            req.ticker, req.side, req.quantity, req.avg_price,
            commission=req.commission, fees=req.fees,
            reference_id=req.reference_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return entry.to_dict()


@router.post("/accounting/split")
def apply_split(req: SplitRequest) -> Dict:
    """Apply a stock split or reverse split."""
    try:
        ca = get_portfolio_accounting_engine().apply_split(req.ticker, req.ratio)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return ca.to_dict()


@router.post("/accounting/dividend")
def apply_dividend(req: DividendRequest) -> Dict:
    """Credit a cash dividend."""
    try:
        ca = get_portfolio_accounting_engine().apply_cash_dividend(
            req.ticker, req.per_share_amount
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return ca.to_dict()


@router.post("/accounting/mark-to-market")
def mark_to_market(req: MarkToMarketRequest) -> Dict:
    """Compute unrealised P&L for all open positions."""
    result = get_portfolio_accounting_engine().mark_to_market(req.prices)
    return {"unrealised_pnl": {t: round(v, 4) for t, v in result.items()}}


@router.post("/accounting/nav")
def compute_nav(req: NAVRequest) -> Dict:
    """Compute Net Asset Value."""
    nav = get_portfolio_accounting_engine().nav(req.prices)
    return {"nav": round(nav, 4)}


@router.post("/accounting/snapshot")
def accounting_snapshot(req: MarkToMarketRequest) -> Dict:
    """Generate a full P&L snapshot."""
    snap = get_portfolio_accounting_engine().snapshot(req.prices)
    return snap.to_dict()


@router.get("/accounting/ledger")
def get_ledger(ticker: Optional[str] = None) -> Dict:
    """Return the cash ledger entries."""
    entries = get_portfolio_accounting_engine().get_ledger(ticker=ticker)
    return {"entries": [e.to_dict() for e in entries], "count": len(entries)}


# ===========================================================================
# Position Engine
# ===========================================================================

@router.post("/positions/open")
def open_position(req: OpenPositionRequest) -> Dict:
    """Open a new lot (BUY trade)."""
    try:
        lot = get_position_engine().open_position(req.ticker, req.quantity, req.price)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return lot.to_dict()


@router.post("/positions/close")
def close_position(req: ClosePositionRequest) -> Dict:
    """Close (SELL) a position using the configured cost basis method."""
    try:
        closed_lots, realised_pnl = get_position_engine().close_position(
            req.ticker, req.quantity, req.price, lot_id=req.lot_id
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {
        "closed_lots": [c.to_dict() for c in closed_lots],
        "realised_pnl": round(realised_pnl, 4),
    }


@router.post("/positions/position")
def get_position(req: PositionRequest) -> Dict:
    """Return the current position view for a ticker."""
    pos = get_position_engine().get_position(req.ticker, req.market_price)
    return pos.to_dict()


@router.post("/positions/all")
def all_positions(req: MarkToMarketRequest) -> Dict:
    """Return all open positions."""
    positions = get_position_engine().all_positions(req.prices)
    return {
        "positions": [p.to_dict() for p in positions],
        "count": len(positions),
    }


@router.post("/positions/exposure")
def exposure_report(req: ExposureRequest) -> Dict:
    """Compute portfolio exposure and leverage."""
    try:
        report = get_position_engine().exposure_report(req.prices, req.nav)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return report.to_dict()


@router.post("/positions/snapshot")
def position_snapshot(req: MarkToMarketRequest) -> Dict:
    """Return full portfolio snapshot."""
    return get_position_engine().snapshot(req.prices)


# ===========================================================================
# Risk Limits
# ===========================================================================

@router.post("/risk/limits/add")
def add_limit(req: AddLimitRequest) -> Dict:
    """Add a new risk limit."""
    lim = get_risk_limits_engine().add_limit(
        LimitType(req.limit_type),
        req.hard_limit,
        req.soft_limit,
        description=req.description,
        asset_filter=req.asset_filter,
    )
    return lim.to_dict()


@router.get("/risk/limits")
def list_limits() -> Dict:
    """Return all configured risk limits."""
    limits = get_risk_limits_engine().get_all_limits()
    return {"limits": [l.to_dict() for l in limits], "count": len(limits)}


@router.post("/risk/check")
def pre_trade_check(req: PreTradeCheckRequest) -> Dict:
    """Run pre-trade risk checks for a proposed order."""
    from services.risk_limits import RiskContext, ProposedOrder
    ctx = RiskContext(
        nav=req.nav,
        cash=req.cash,
        current_positions=req.current_positions,
        current_market_values=req.current_market_values,
        sector_weights=req.sector_weights,
        country_weights=req.country_weights,
        gross_leverage=req.gross_leverage,
        net_leverage=req.net_leverage,
        portfolio_beta=req.portfolio_beta,
        portfolio_var_pct=req.portfolio_var_pct,
        current_drawdown=req.current_drawdown,
        daily_turnover=req.daily_turnover,
        top_position_weight=req.top_position_weight,
    )
    order = ProposedOrder(
        ticker=req.ticker,
        side=req.side,
        quantity=req.quantity,
        price=req.price,
        sector=req.sector,
        country=req.country,
        asset_beta=req.asset_beta,
    )
    result = get_risk_limits_engine().check_order(order, ctx)
    return result.to_dict()


@router.delete("/risk/limits/{limit_id}")
def remove_limit(limit_id: str) -> Dict:
    """Remove a risk limit by ID."""
    try:
        get_risk_limits_engine().remove_limit(limit_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"removed": limit_id}


# ===========================================================================
# Trade Analytics
# ===========================================================================

@router.post("/analytics/trades/add")
def add_trade(req: TradeRecordRequest) -> Dict:
    """Add a completed trade record to the analytics engine."""
    trade = TradeRecord(
        trade_id=req.trade_id,
        ticker=req.ticker,
        side=req.side,
        quantity=req.quantity,
        entry_price=req.entry_price,
        exit_price=req.exit_price,
        entry_datetime=req.entry_datetime,
        exit_datetime=req.exit_datetime,
        commission=req.commission,
        pnl=req.pnl,
        sector=req.sector,
        strategy_tag=req.strategy_tag,
    )
    get_trade_analytics_engine().add_trade(trade)
    return {"added": req.trade_id}


@router.get("/analytics/trades/statistics")
def trade_statistics() -> Dict:
    """Compute aggregate statistics over all stored trades."""
    eng = get_trade_analytics_engine()
    try:
        stats = eng.compute_statistics()
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return stats.to_dict()


@router.get("/analytics/trades/sector-attribution")
def sector_attribution() -> Dict:
    """Compute P&L attribution by sector."""
    eng = get_trade_analytics_engine()
    try:
        attrs = eng.sector_attribution()
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"sectors": [a.to_dict() for a in attrs]}


@router.post("/analytics/portfolio-performance")
def portfolio_performance(req: PortfolioPerformanceRequest) -> Dict:
    """Compute portfolio performance metrics from a return series."""
    try:
        metrics = get_trade_analytics_engine().portfolio_performance(
            req.returns,
            benchmark_returns=req.benchmark_returns,
            risk_free=req.risk_free,
            periods_per_year=req.periods_per_year,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return metrics.to_dict()


@router.post("/analytics/kelly")
def kelly_fraction(req: KellyRequest) -> Dict:
    """Compute Kelly optimal bet fraction."""
    k = get_trade_analytics_engine().kelly_fraction(
        req.win_rate, req.avg_win, req.avg_loss
    )
    return {"kelly_fraction": round(k, 6)}


# ===========================================================================
# TCA
# ===========================================================================

@router.post("/tca/analyse")
def tca_analyse(req: TCATradeRequest) -> Dict:
    """Compute full transaction cost breakdown for a trade."""
    from services.tca import TCABenchmark
    try:
        result = get_tca_engine().analyse_trade(
            req.trade_id, req.ticker, req.side, req.quantity,
            req.decision_price, req.arrival_price, req.avg_fill_price,
            req.commission_usd, req.spread_bps,
            req.benchmark_price, TCABenchmark(req.benchmark_type),
            fill_rate=req.fill_rate,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result.to_dict()


@router.post("/tca/record")
def record_tca_trade(req: RecordTCATradeRequest) -> Dict:
    """Record a trade for aggregate TCA analysis."""
    get_tca_engine().record_trade(
        req.trade_id, req.ticker, req.side, req.quantity,
        req.arrival_price, req.avg_fill_price,
        decision_price=req.decision_price,
        commission_usd=req.commission_usd,
        spread_bps=req.spread_bps,
        broker_id=req.broker_id,
        broker_name=req.broker_name,
        fill_rate=req.fill_rate,
    )
    return {"recorded": req.trade_id}


@router.get("/tca/report")
def tca_report() -> Dict:
    """Generate aggregate TCA report from stored records."""
    try:
        report = get_tca_engine().generate_report()
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return report.to_dict()


# ===========================================================================
# Broker Management
# ===========================================================================

@router.post("/brokers/register")
def register_broker(req: BrokerRegisterRequest) -> Dict:
    """Register a new broker."""
    from services.broker_management import AssetClass as AC
    try:
        asset_classes = [AC(a) for a in req.supported_asset_classes]
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    broker = get_broker_management_engine().register_broker(
        req.name,
        supported_asset_classes=asset_classes,
        supported_exchanges=req.supported_exchanges,
        notes=req.notes,
    )
    return broker.to_dict()


@router.get("/brokers")
def list_brokers() -> Dict:
    """List all registered brokers."""
    brokers = get_broker_management_engine().all_brokers()
    return {"brokers": [b.to_dict() for b in brokers], "count": len(brokers)}


@router.get("/brokers/statistics")
def broker_statistics() -> Dict:
    """Return aggregate broker statistics."""
    return get_broker_management_engine().statistics()


@router.get("/brokers/rank")
def rank_brokers() -> Dict:
    """Return brokers ranked by quality score."""
    ranked = get_broker_management_engine().rank_brokers()
    return {"ranked_brokers": [{"rank": r, "broker": b.to_dict()} for r, b in ranked]}


@router.get("/brokers/{broker_id}")
def get_broker(broker_id: str) -> Dict:
    """Retrieve a broker by ID."""
    broker = get_broker_management_engine().get_broker(broker_id)
    if broker is None:
        raise HTTPException(status_code=404, detail=f"Broker {broker_id!r} not found")
    return broker.to_dict()


@router.post("/brokers/commission/add")
def add_commission_schedule(req: CommissionScheduleRequest) -> Dict:
    """Add a commission schedule to a broker."""
    from services.broker_management import CommissionType as CT
    try:
        sched = get_broker_management_engine().add_commission_schedule(
            req.broker_id, AssetClass(req.asset_class),
            CT(req.commission_type), req.base_rate,
            minimum_per_trade=req.minimum_per_trade,
            maximum_pct_of_trade=req.maximum_pct_of_trade,
        )
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return sched.to_dict()


@router.post("/brokers/commission/compute")
def compute_broker_commission(req: CommissionComputeRequest) -> Dict:
    """Compute commission for a trade using a broker's schedule."""
    try:
        commission = get_broker_management_engine().compute_commission(
            req.broker_id, AssetClass(req.asset_class), req.quantity, req.price
        )
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"commission_usd": round(commission, 4)}


@router.post("/brokers/route")
def route_order(req: RouteOrderRequest) -> Dict:
    """Find the best broker for an order based on routing rules."""
    broker = get_broker_management_engine().route_order(
        AssetClass(req.asset_class), req.exchange, req.order_value
    )
    if broker is None:
        return {"broker": None, "message": "No matching broker found"}
    return {"broker": broker.to_dict()}


@router.post("/brokers/{broker_id}/execution")
def record_broker_execution(broker_id: str, req: BrokerExecutionRequest) -> Dict:
    """Record an execution for broker quality tracking."""
    try:
        rec = get_broker_management_engine().record_execution(
            broker_id, req.ticker, req.quantity,
            req.arrival_price, req.avg_fill_price,
            fill_rate=req.fill_rate, latency_ms=req.latency_ms,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return rec.to_dict()


# ===========================================================================
# Paper Trading Simulator
# ===========================================================================

@router.post("/paper/prices")
def update_prices(req: PriceUpdateRequest) -> Dict:
    """Update market prices in the simulator."""
    sim = get_paper_trading_simulator()
    for ticker, price in req.prices.items():
        sim.update_price(ticker, price)
    return {"updated": list(req.prices.keys())}


@router.post("/paper/market-order")
def paper_market_order(req: SimMarketOrderRequest) -> Dict:
    """Submit a market order in the paper trading simulator."""
    sim = get_paper_trading_simulator()
    try:
        result = sim.submit_market_order(
            req.ticker, OrderSide(req.side), req.quantity,
            strategy_tag=req.strategy_tag,
        )
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result.to_dict()


@router.post("/paper/limit-order")
def paper_limit_order(req: SimLimitOrderRequest) -> Dict:
    """Submit a limit order in the paper trading simulator."""
    sim = get_paper_trading_simulator()
    order = sim.submit_limit_order(
        req.ticker, OrderSide(req.side), req.quantity, req.limit_price,
        strategy_tag=req.strategy_tag,
    )
    return order.to_dict()


@router.get("/paper/account")
def paper_account_state() -> Dict:
    """Return the current paper trading account state."""
    return get_paper_trading_simulator().account_state().to_dict()


@router.get("/paper/positions")
def paper_positions() -> Dict:
    """Return all open positions in the paper trading account."""
    positions = get_paper_trading_simulator().open_positions()
    return {"positions": positions, "count": len(positions)}


@router.get("/paper/fills")
def paper_fills() -> Dict:
    """Return all fill results from the paper trading simulator."""
    fills = get_paper_trading_simulator().get_fills()
    return {"fills": [f.to_dict() for f in fills], "count": len(fills)}


@router.get("/paper/trades")
def paper_closed_trades() -> Dict:
    """Return all closed paper trades."""
    trades = get_paper_trading_simulator().get_closed_trades()
    return {"trades": [t.to_dict() for t in trades], "count": len(trades)}


@router.post("/paper/reset")
def paper_reset(req: SimResetRequest) -> Dict:
    """Reset the paper trading simulator to a clean state."""
    get_paper_trading_simulator().reset(initial_cash=req.initial_cash)
    return {"reset": True}


# ===========================================================================
# Performance Attribution
# ===========================================================================

@router.post("/attribution/brinson")
def brinson_attribution(req: BrinsonRequest) -> Dict:
    """Compute Brinson attribution (allocation, selection, interaction)."""
    holdings = [
        Holding(
            category=h.category,
            portfolio_weight=h.portfolio_weight,
            benchmark_weight=h.benchmark_weight,
            portfolio_return=h.portfolio_return,
            benchmark_return=h.benchmark_return,
        )
        for h in req.holdings
    ]
    try:
        result = get_performance_attribution_engine().brinson_attribution(
            holdings, req.benchmark_total_return,
            model=AttributionModel(req.model),
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result.to_dict()


@router.post("/attribution/factor")
def factor_attribution(req: FactorAttributionRequest) -> Dict:
    """Compute factor-based return attribution."""
    factors = [
        FactorExposure(
            factor_name=f.factor_name,
            portfolio_exposure=f.portfolio_exposure,
            benchmark_exposure=f.benchmark_exposure,
            factor_return=f.factor_return,
        )
        for f in req.factors
    ]
    try:
        results = get_performance_attribution_engine().factor_attribution(factors)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"factor_attribution": [r.to_dict() for r in results]}


@router.post("/attribution/full")
def full_attribution(req: FullAttributionRequest) -> Dict:
    """Generate a full attribution report (Brinson + factor + currency)."""
    from services.performance_attribution import FactorExposure as FE

    sector_holdings = [
        Holding(h.category, h.portfolio_weight, h.benchmark_weight,
                h.portfolio_return, h.benchmark_return)
        for h in req.sector_holdings
    ]
    country_holdings = None
    if req.country_holdings:
        country_holdings = [
            Holding(h.category, h.portfolio_weight, h.benchmark_weight,
                    h.portfolio_return, h.benchmark_return)
            for h in req.country_holdings
        ]
    ccy = None
    if req.currency_holdings:
        ccy = [
            (h.currency, h.portfolio_weight, h.benchmark_weight, h.currency_return)
            for h in req.currency_holdings
        ]
    factors = None
    if req.factor_exposures:
        factors = [
            FE(f.factor_name, f.portfolio_exposure, f.benchmark_exposure, f.factor_return)
            for f in req.factor_exposures
        ]
    try:
        report = get_performance_attribution_engine().full_report(
            sector_holdings, req.benchmark_total_return,
            country_holdings=country_holdings,
            currency_holdings=ccy,
            factor_exposures=factors,
            active_return_series=req.active_return_series,
            periods_per_year=req.periods_per_year,
            model=AttributionModel(req.model),
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return report.to_dict()


@router.post("/attribution/information-ratio")
def information_ratio(req: IRRequest) -> Dict:
    """Compute annualised Information Ratio."""
    try:
        ir = get_performance_attribution_engine().information_ratio(
            req.active_returns, req.periods_per_year
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"information_ratio": round(ir, 6)}


@router.post("/attribution/tracking-error")
def tracking_error(req: IRRequest) -> Dict:
    """Compute annualised Tracking Error."""
    try:
        te = get_performance_attribution_engine().tracking_error(
            req.active_returns, req.periods_per_year
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"tracking_error": round(te, 6)}
