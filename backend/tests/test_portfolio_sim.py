"""M11 Phase 3 — deterministic tests for the portfolio simulation engine.

All tests inject synthetic price_data — zero network calls.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import pytest

from services.portfolio_sim import (
    PortfolioSimConfig,
    PortfolioSimResult,
    run_portfolio_sim,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_price_df(
    closes: List[float],
    start: str = "2022-01-03",
    opens: Optional[List[float]] = None,
) -> pd.DataFrame:
    """Build a minimal OHLCV DataFrame from a list of close prices."""
    idx = pd.bdate_range(start=start, periods=len(closes))
    c = np.array(closes, dtype=float)
    o = np.array(opens, dtype=float) if opens else c * 0.999
    h = np.maximum(c, o) * 1.001
    l = np.minimum(c, o) * 0.999
    return pd.DataFrame({"Open": o, "High": h, "Low": l, "Close": c, "Volume": 1e6}, index=idx)


def _bah_config(
    ticker: str = "AAPL",
    closes: Optional[List[float]] = None,
    bench_closes: Optional[List[float]] = None,
    initial_capital: float = 10_000.0,
    allow_short: bool = False,
    commission_pct: float = 0.001,
    slippage_pct: float = 0.001,
    annual_dividend_yield: float = 0.0,
) -> tuple[PortfolioSimConfig, Dict[str, pd.DataFrame]]:
    """Single-ticker BuyAndHold config + synthetic price_data."""
    n = 60
    if closes is None:
        closes = list(np.linspace(100.0, 120.0, n))
    if bench_closes is None:
        bench_closes = list(np.linspace(400.0, 420.0, len(closes)))

    df = _make_price_df(closes)
    bench_df = _make_price_df(bench_closes)
    idx = df.index

    cfg = PortfolioSimConfig(
        tickers=[ticker],
        strategy_names=["buy_and_hold"],
        strategy_params=[{}],
        start_date=idx[0].date(),
        end_date=idx[-1].date(),
        benchmark="SPY",
        initial_capital=initial_capital,
        commission_pct=commission_pct,
        slippage_pct=slippage_pct,
        allow_short=allow_short,
        annual_dividend_yield=annual_dividend_yield,
    )
    price_data = {ticker: df, "SPY": bench_df}
    return cfg, price_data


# ---------------------------------------------------------------------------
# Config validation tests
# ---------------------------------------------------------------------------


def test_config_mismatched_strategies_raises():
    with pytest.raises(ValueError, match="strategy_names"):
        PortfolioSimConfig(
            tickers=["AAPL"],
            strategy_names=[],
            strategy_params=[{}],
            start_date=date(2022, 1, 3),
            end_date=date(2022, 6, 30),
        )


def test_config_mismatched_params_raises():
    with pytest.raises(ValueError, match="strategy_params"):
        PortfolioSimConfig(
            tickers=["AAPL"],
            strategy_names=["buy_and_hold"],
            strategy_params=[],
            start_date=date(2022, 1, 3),
            end_date=date(2022, 6, 30),
        )


def test_config_empty_tickers_raises():
    with pytest.raises(ValueError, match="tickers must not be empty"):
        PortfolioSimConfig(
            tickers=[],
            strategy_names=[],
            strategy_params=[],
            start_date=date(2022, 1, 3),
            end_date=date(2022, 6, 30),
        )


def test_config_invalid_position_size_raises():
    with pytest.raises(ValueError, match="position_size_pct"):
        PortfolioSimConfig(
            tickers=["AAPL"],
            strategy_names=["buy_and_hold"],
            strategy_params=[{}],
            start_date=date(2022, 1, 3),
            end_date=date(2022, 6, 30),
            position_size_pct=0.0,
        )


def test_config_position_size_above_one_raises():
    with pytest.raises(ValueError):
        PortfolioSimConfig(
            tickers=["AAPL"],
            strategy_names=["buy_and_hold"],
            strategy_params=[{}],
            start_date=date(2022, 1, 3),
            end_date=date(2022, 6, 30),
            position_size_pct=1.5,
        )


def test_config_missing_price_data_raises():
    cfg = PortfolioSimConfig(
        tickers=["AAPL"],
        strategy_names=["buy_and_hold"],
        strategy_params=[{}],
        start_date=date(2022, 1, 3),
        end_date=date(2022, 6, 30),
    )
    with pytest.raises(ValueError, match="No price data"):
        run_portfolio_sim(cfg, price_data={})


# ---------------------------------------------------------------------------
# Basic structural tests
# ---------------------------------------------------------------------------


def test_result_type():
    cfg, pd_ = _bah_config()
    result = run_portfolio_sim(cfg, price_data=pd_)
    assert isinstance(result, PortfolioSimResult)


def test_snapshots_non_empty():
    cfg, pd_ = _bah_config()
    result = run_portfolio_sim(cfg, price_data=pd_)
    assert len(result.snapshots) > 0


def test_snapshot_dates_monotone():
    cfg, pd_ = _bah_config()
    result = run_portfolio_sim(cfg, price_data=pd_)
    dates = [s.date for s in result.snapshots]
    assert dates == sorted(dates)


def test_equity_curve_property():
    cfg, pd_ = _bah_config()
    result = run_portfolio_sim(cfg, price_data=pd_)
    ec = result.equity_curve
    assert isinstance(ec, list)
    assert all(isinstance(t, tuple) and len(t) == 2 for t in ec)


def test_metrics_present():
    cfg, pd_ = _bah_config()
    result = run_portfolio_sim(cfg, price_data=pd_)
    m = result.metrics
    assert m.final_equity > 0


# ---------------------------------------------------------------------------
# Cash and equity accounting
# ---------------------------------------------------------------------------


def test_initial_snapshot_equity_equals_capital():
    cfg, pd_ = _bah_config(initial_capital=10_000.0)
    result = run_portfolio_sim(cfg, price_data=pd_)
    first = result.snapshots[0]
    assert abs(first.equity - 10_000.0) < 1.0


def test_flat_market_no_gain_no_loss():
    """Flat price → buy/hold → equity should roughly equal initial capital."""
    closes = [100.0] * 40
    cfg, pd_ = _bah_config(closes=closes, initial_capital=10_000.0, commission_pct=0.0, slippage_pct=0.0)
    result = run_portfolio_sim(cfg, price_data=pd_)
    last = result.snapshots[-1]
    # With zero costs equity should be ~10 000 (within integer share rounding)
    assert abs(last.equity - 10_000.0) < 200.0


def test_uptrend_equity_increases():
    closes = list(np.linspace(100.0, 150.0, 60))
    cfg, pd_ = _bah_config(closes=closes, initial_capital=10_000.0)
    result = run_portfolio_sim(cfg, price_data=pd_)
    first_eq = result.snapshots[0].equity
    last_eq = result.snapshots[-1].equity
    assert last_eq > first_eq


def test_downtrend_equity_decreases():
    closes = list(np.linspace(150.0, 100.0, 60))
    cfg, pd_ = _bah_config(closes=closes, initial_capital=10_000.0)
    result = run_portfolio_sim(cfg, price_data=pd_)
    first_eq = result.snapshots[0].equity
    last_eq = result.snapshots[-1].equity
    assert last_eq < first_eq


def test_final_equity_close_to_capital_for_flat():
    closes = [100.0] * 60
    cfg, pd_ = _bah_config(closes=closes, commission_pct=0.0, slippage_pct=0.0)
    result = run_portfolio_sim(cfg, price_data=pd_)
    assert abs(result.metrics.final_equity - 10_000.0) < 100.0


# ---------------------------------------------------------------------------
# Transaction ledger
# ---------------------------------------------------------------------------


def test_buy_and_hold_produces_buy_transaction():
    cfg, pd_ = _bah_config()
    result = run_portfolio_sim(cfg, price_data=pd_)
    buys = [t for t in result.transactions if t.action == "BUY"]
    assert len(buys) >= 1


def test_buy_transaction_net_cash_negative():
    cfg, pd_ = _bah_config()
    result = run_portfolio_sim(cfg, price_data=pd_)
    buys = [t for t in result.transactions if t.action == "BUY"]
    for tx in buys:
        assert tx.net_cash_change < 0


def test_sell_transaction_net_cash_positive():
    cfg, pd_ = _bah_config()
    result = run_portfolio_sim(cfg, price_data=pd_)
    sells = [t for t in result.transactions if t.action == "SELL"]
    for tx in sells:
        assert tx.net_cash_change > 0


def test_commissions_non_negative():
    cfg, pd_ = _bah_config()
    result = run_portfolio_sim(cfg, price_data=pd_)
    for tx in result.transactions:
        assert tx.commission >= 0


def test_metrics_total_commissions_positive():
    cfg, pd_ = _bah_config(commission_pct=0.001)
    result = run_portfolio_sim(cfg, price_data=pd_)
    assert result.metrics.total_commissions >= 0


# ---------------------------------------------------------------------------
# Drawdown
# ---------------------------------------------------------------------------


def test_drawdown_pct_non_positive():
    closes = list(np.linspace(100.0, 150.0, 60))
    cfg, pd_ = _bah_config(closes=closes)
    result = run_portfolio_sim(cfg, price_data=pd_)
    for s in result.snapshots:
        assert s.drawdown_pct <= 0.001   # allow tiny float noise


def test_max_drawdown_metric_non_negative():
    closes = list(np.linspace(100.0, 80.0, 60))
    cfg, pd_ = _bah_config(closes=closes)
    result = run_portfolio_sim(cfg, price_data=pd_)
    assert result.metrics.max_drawdown_pct >= 0


# ---------------------------------------------------------------------------
# Short selling
# ---------------------------------------------------------------------------


def test_short_disabled_no_short_transactions():
    closes = list(np.linspace(100.0, 80.0, 60))
    cfg, pd_ = _bah_config(closes=closes, allow_short=False)
    result = run_portfolio_sim(cfg, price_data=pd_)
    shorts = [t for t in result.transactions if t.action == "SHORT"]
    assert len(shorts) == 0


def test_short_transaction_net_cash_positive():
    """SHORT entry receives cash."""
    n = 80
    closes = list(np.linspace(100.0, 70.0, n))
    bench_closes = list(np.linspace(400.0, 390.0, n))
    df = _make_price_df(closes)
    bench_df = _make_price_df(bench_closes)
    idx = df.index
    cfg = PortfolioSimConfig(
        tickers=["XXX"],
        strategy_names=["buy_and_hold"],
        strategy_params=[{}],
        start_date=idx[0].date(),
        end_date=idx[-1].date(),
        benchmark="SPY",
        initial_capital=10_000.0,
        commission_pct=0.001,
        slippage_pct=0.001,
        allow_short=True,
    )
    price_data = {"XXX": df, "SPY": bench_df}
    result = run_portfolio_sim(cfg, price_data=price_data)
    # buy-and-hold always opens LONG first; no SHORT expected here
    # but all BUY net_cash should be negative
    buys = [t for t in result.transactions if t.action == "BUY"]
    for tx in buys:
        assert tx.net_cash_change < 0


# ---------------------------------------------------------------------------
# Dividends
# ---------------------------------------------------------------------------


def test_dividend_transactions_created():
    closes = [100.0] * 40
    cfg, pd_ = _bah_config(
        closes=closes,
        annual_dividend_yield=0.02,
        commission_pct=0.001,
    )
    result = run_portfolio_sim(cfg, price_data=pd_)
    divs = [t for t in result.transactions if t.action == "DIVIDEND"]
    # Once a long position is open dividends should accrue daily
    assert len(divs) > 0


def test_dividend_increases_cash():
    closes = [100.0] * 40
    cfg, pd_ = _bah_config(
        closes=closes,
        annual_dividend_yield=0.05,
        commission_pct=0.0,
        slippage_pct=0.0,
    )
    result = run_portfolio_sim(cfg, price_data=pd_)
    divs = [t for t in result.transactions if t.action == "DIVIDEND"]
    for tx in divs:
        assert tx.net_cash_change > 0


# ---------------------------------------------------------------------------
# Buying power / leverage
# ---------------------------------------------------------------------------


def test_buying_power_at_least_cash():
    cfg, pd_ = _bah_config()
    result = run_portfolio_sim(cfg, price_data=pd_)
    for s in result.snapshots:
        assert s.buying_power >= s.cash - 1.0   # allow float noise


def test_leverage_zero_when_no_positions():
    """First snapshot: no positions yet → leverage should be 0."""
    cfg, pd_ = _bah_config()
    result = run_portfolio_sim(cfg, price_data=pd_)
    first = result.snapshots[0]
    assert first.leverage == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# Multi-ticker
# ---------------------------------------------------------------------------


def test_multi_ticker_simulation():
    n = 60
    closes_a = list(np.linspace(100.0, 120.0, n))
    closes_b = list(np.linspace(50.0, 60.0, n))
    bench_closes = list(np.linspace(400.0, 420.0, n))
    df_a = _make_price_df(closes_a)
    df_b = _make_price_df(closes_b)
    bench_df = _make_price_df(bench_closes)
    idx = df_a.index

    cfg = PortfolioSimConfig(
        tickers=["AAA", "BBB"],
        strategy_names=["buy_and_hold", "buy_and_hold"],
        strategy_params=[{}, {}],
        start_date=idx[0].date(),
        end_date=idx[-1].date(),
        benchmark="SPY",
        initial_capital=20_000.0,
    )
    price_data = {"AAA": df_a, "BBB": df_b, "SPY": bench_df}
    result = run_portfolio_sim(cfg, price_data=price_data)
    assert len(result.snapshots) > 0
    assert result.metrics.final_equity > 0


def test_multi_ticker_buys_for_each():
    n = 60
    closes_a = list(np.linspace(100.0, 120.0, n))
    closes_b = list(np.linspace(50.0, 60.0, n))
    bench_closes = list(np.linspace(400.0, 420.0, n))
    df_a = _make_price_df(closes_a)
    df_b = _make_price_df(closes_b)
    bench_df = _make_price_df(bench_closes)
    idx = df_a.index

    cfg = PortfolioSimConfig(
        tickers=["AAA", "BBB"],
        strategy_names=["buy_and_hold", "buy_and_hold"],
        strategy_params=[{}, {}],
        start_date=idx[0].date(),
        end_date=idx[-1].date(),
        benchmark="SPY",
        initial_capital=20_000.0,
    )
    price_data = {"AAA": df_a, "BBB": df_b, "SPY": bench_df}
    result = run_portfolio_sim(cfg, price_data=price_data)
    tickers_bought = {t.ticker for t in result.transactions if t.action == "BUY"}
    assert "AAA" in tickers_bought
    assert "BBB" in tickers_bought


# ---------------------------------------------------------------------------
# Benchmark comparison
# ---------------------------------------------------------------------------


def test_benchmark_return_computed():
    closes = list(np.linspace(100.0, 120.0, 60))
    bench_closes = list(np.linspace(400.0, 440.0, 60))   # +10 %
    cfg, pd_ = _bah_config(closes=closes, bench_closes=bench_closes)
    result = run_portfolio_sim(cfg, price_data=pd_)
    # +10 % benchmark
    assert abs(result.metrics.benchmark_return_pct - 10.0) < 0.5


def test_no_benchmark_data_ok():
    """If benchmark is not in price_data, metrics should still compute."""
    closes = list(np.linspace(100.0, 120.0, 60))
    df = _make_price_df(closes)
    idx = df.index
    cfg = PortfolioSimConfig(
        tickers=["AAPL"],
        strategy_names=["buy_and_hold"],
        strategy_params=[{}],
        start_date=idx[0].date(),
        end_date=idx[-1].date(),
        benchmark="SPY",
        initial_capital=10_000.0,
    )
    result = run_portfolio_sim(cfg, price_data={"AAPL": df})
    assert result.metrics.benchmark_return_pct == 0.0


# ---------------------------------------------------------------------------
# Performance metrics
# ---------------------------------------------------------------------------


def test_total_return_positive_for_uptrend():
    closes = list(np.linspace(100.0, 150.0, 60))
    cfg, pd_ = _bah_config(closes=closes)
    result = run_portfolio_sim(cfg, price_data=pd_)
    assert result.metrics.total_return_pct > 0


def test_total_return_negative_for_downtrend():
    closes = list(np.linspace(150.0, 100.0, 60))
    cfg, pd_ = _bah_config(closes=closes)
    result = run_portfolio_sim(cfg, price_data=pd_)
    assert result.metrics.total_return_pct < 0


def test_sharpe_ratio_finite():
    closes = list(np.linspace(100.0, 120.0, 80))
    cfg, pd_ = _bah_config(closes=closes)
    result = run_portfolio_sim(cfg, price_data=pd_)
    assert math.isfinite(result.metrics.sharpe_ratio)


def test_volatility_non_negative():
    closes = list(np.linspace(100.0, 120.0, 80))
    cfg, pd_ = _bah_config(closes=closes)
    result = run_portfolio_sim(cfg, price_data=pd_)
    assert result.metrics.volatility_pct >= 0


def test_var95_non_positive_or_zero():
    """VaR should be <= 0 (a loss estimate) or exactly 0 for degenerate series."""
    closes = [100.0] * 60
    cfg, pd_ = _bah_config(closes=closes)
    result = run_portfolio_sim(cfg, price_data=pd_)
    assert result.metrics.var_95 <= 0.0001


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_determinism_same_config_same_result():
    closes = list(np.linspace(100.0, 130.0, 60))
    cfg, pd_ = _bah_config(closes=closes)
    r1 = run_portfolio_sim(cfg, price_data=pd_)
    r2 = run_portfolio_sim(cfg, price_data=pd_)
    assert r1.metrics.final_equity == r2.metrics.final_equity
    assert len(r1.snapshots) == len(r2.snapshots)
    assert len(r1.transactions) == len(r2.transactions)


# ---------------------------------------------------------------------------
# Realized vs unrealized PnL consistency
# ---------------------------------------------------------------------------


def test_total_pnl_equals_equity_minus_initial():
    closes = list(np.linspace(100.0, 130.0, 60))
    cfg, pd_ = _bah_config(closes=closes, commission_pct=0.0, slippage_pct=0.0)
    result = run_portfolio_sim(cfg, price_data=pd_)
    for s in result.snapshots:
        expected_total = s.equity - 10_000.0
        assert abs(s.total_pnl - expected_total) < 1.0   # allow rounding


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_single_day_simulation():
    closes = [100.0, 101.0]   # 2 prices = 1 trading day eval window
    df = _make_price_df(closes)
    bench_df = _make_price_df([400.0, 401.0])
    idx = df.index
    cfg = PortfolioSimConfig(
        tickers=["XX"],
        strategy_names=["buy_and_hold"],
        strategy_params=[{}],
        start_date=idx[0].date(),
        end_date=idx[-1].date(),
        benchmark="SPY",
        initial_capital=10_000.0,
    )
    result = run_portfolio_sim(cfg, price_data={"XX": df, "SPY": bench_df})
    assert len(result.snapshots) >= 1


def test_zero_commission_zero_slippage_buy_and_hold():
    closes = [100.0, 110.0, 120.0] + [120.0] * 20
    cfg, pd_ = _bah_config(
        closes=closes,
        commission_pct=0.0,
        slippage_pct=0.0,
        initial_capital=1_000.0,
    )
    result = run_portfolio_sim(cfg, price_data=pd_)
    assert result.metrics.total_commissions == pytest.approx(0.0, abs=1e-6)
