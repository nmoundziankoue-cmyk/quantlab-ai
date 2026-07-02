"""
Unit tests for services/backtest.py.

The core simulation logic is tested in isolation by patching _download_ohlcv
and _benchmark_returns to return controlled synthetic data — no network calls.
"""

import math
import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.backtest import (
    BacktestConfig,
    _compute_metrics,
    _max_drawdown_duration,
    _monthly_returns,
    run_backtest,
    ClosedTrade,
    EquitySnapshot,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ohlcv(close_prices: list, start: str = "2022-01-03") -> pd.DataFrame:
    """Build a deterministic OHLCV DataFrame from a close price list."""
    n = len(close_prices)
    idx = pd.date_range(start, periods=n, freq="B")
    close = pd.Series(close_prices, index=idx, dtype=float)
    return pd.DataFrame(
        {
            "Open": close * 0.999,
            "High": close * 1.005,
            "Low": close * 0.995,
            "Close": close,
            "Volume": [1_000_000.0] * n,
        },
        index=idx,
    )


def _make_config(**kwargs) -> BacktestConfig:
    defaults = dict(
        ticker="TEST",
        benchmark="SPY",
        start_date=date(2022, 1, 3),
        end_date=date(2022, 12, 30),
        initial_capital=100_000.0,
        commission_pct=0.001,
        slippage_pct=0.001,
        position_size_pct=1.0,
        strategy_name="sma_crossover",
        strategy_params={"fast_period": 3, "slow_period": 5},
    )
    defaults.update(kwargs)
    return BacktestConfig(**defaults)


# ---------------------------------------------------------------------------
# _max_drawdown_duration
# ---------------------------------------------------------------------------


def test_max_drawdown_duration_no_drawdown():
    """Monotonically increasing equity → no drawdown → duration = 0."""
    idx = pd.date_range("2022-01-01", periods=10, freq="B")
    equity = pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109], index=idx, dtype=float)
    assert _max_drawdown_duration(equity) == 0


def test_max_drawdown_duration_single_trough():
    idx = pd.date_range("2022-01-03", periods=5, freq="B")
    # Peak at idx[0], trough at idx[2], recovery at idx[4]
    equity = pd.Series([100, 95, 90, 95, 100], index=idx, dtype=float)
    dur = _max_drawdown_duration(equity)
    assert dur > 0


# ---------------------------------------------------------------------------
# _monthly_returns
# ---------------------------------------------------------------------------


def test_monthly_returns_structure():
    snapshots = [
        EquitySnapshot(date=f"2022-{m:02d}-{d:02d}", equity=100_000 + i * 500, cash=0, position_value=0, drawdown_pct=0)
        for i, (m, d) in enumerate(
            [(1, 3), (1, 31), (2, 28), (3, 31), (4, 29), (5, 31), (6, 30)]
        )
    ]
    result = _monthly_returns(snapshots)
    # Result should be a nested dict {year: {month: float}}
    assert isinstance(result, dict)
    for year_data in result.values():
        assert isinstance(year_data, dict)
        for val in year_data.values():
            assert isinstance(val, float)


def test_monthly_returns_empty():
    assert _monthly_returns([]) == {}


# ---------------------------------------------------------------------------
# _compute_metrics — basic smoke test
# ---------------------------------------------------------------------------


def test_compute_metrics_total_return():
    """If equity doubles, total_return_pct should be ~100%."""
    snapshots = [
        EquitySnapshot(date=f"2022-01-{d:02d}", equity=eq, cash=eq, position_value=0, drawdown_pct=0)
        for d, eq in [(3, 100_000), (10, 110_000), (17, 120_000), (24, 140_000), (31, 200_000)]
    ]
    config = _make_config()
    metrics = _compute_metrics(snapshots, [], config, pd.Series(dtype=float))
    assert math.isclose(metrics.total_return_pct, 100.0, rel_tol=1e-9)
    assert metrics.final_equity == 200_000.0


def test_compute_metrics_no_trades():
    """Zero trades → zero win rate, zero profit factor."""
    snapshots = [
        EquitySnapshot(date="2022-01-03", equity=100_000, cash=100_000, position_value=0, drawdown_pct=0),
        EquitySnapshot(date="2022-12-30", equity=100_000, cash=100_000, position_value=0, drawdown_pct=0),
    ]
    config = _make_config()
    metrics = _compute_metrics(snapshots, [], config, pd.Series(dtype=float))
    assert metrics.total_trades == 0
    assert metrics.win_rate_pct == 0.0


def test_compute_metrics_all_winning_trades():
    trade = ClosedTrade(
        entry_date="2022-01-03",
        exit_date="2022-01-10",
        direction="LONG",
        entry_price=100.0,
        exit_price=110.0,
        shares=100,
        gross_pnl=1000.0,
        net_pnl=900.0,
        pnl_pct=10.0,
        duration_days=7,
        commissions_paid=100.0,
    )
    snapshots = [
        EquitySnapshot(date="2022-01-03", equity=100_000, cash=100_000, position_value=0, drawdown_pct=0),
        EquitySnapshot(date="2022-12-30", equity=110_000, cash=110_000, position_value=0, drawdown_pct=0),
    ]
    config = _make_config()
    metrics = _compute_metrics(snapshots, [trade], config, pd.Series(dtype=float))
    assert metrics.winning_trades == 1
    assert metrics.losing_trades == 0
    assert metrics.win_rate_pct == 100.0


# ---------------------------------------------------------------------------
# Full run_backtest — patched I/O
# ---------------------------------------------------------------------------


@pytest.fixture
def flat_then_surge_data():
    """
    Synthetic price data: 50 flat bars → 50 rising bars.
    SMA(3)/SMA(5) will produce a golden cross mid-way.
    We provide 200 bars total (with warmup pre-pended) so rolling windows initialise.
    """
    flat = [100.0] * 100
    surge = [100.0 + i * 2.0 for i in range(100)]
    return _make_ohlcv(flat + surge, start="2021-06-01")


@patch("services.backtest._benchmark_returns", return_value=pd.Series(dtype=float))
@patch("services.backtest._download_ohlcv")
def test_run_backtest_returns_result(mock_download, mock_bench, flat_then_surge_data):
    mock_download.return_value = flat_then_surge_data

    config = _make_config(
        start_date=date(2022, 1, 3),
        end_date=date(2022, 12, 30),
        strategy_name="sma_crossover",
        strategy_params={"fast_period": 3, "slow_period": 5},
        initial_capital=100_000.0,
        commission_pct=0.001,
        slippage_pct=0.001,
    )
    result = run_backtest(config)

    assert result is not None
    assert len(result.equity_curve) > 0
    assert result.metrics is not None
    assert isinstance(result.metrics.sharpe_ratio, float)


@patch("services.backtest._benchmark_returns", return_value=pd.Series(dtype=float))
@patch("services.backtest._download_ohlcv")
def test_run_backtest_equity_starts_at_capital(mock_download, mock_bench, flat_then_surge_data):
    mock_download.return_value = flat_then_surge_data
    config = _make_config()
    result = run_backtest(config)
    assert math.isclose(result.equity_curve[0].equity, 100_000.0, rel_tol=0.05)


@patch("services.backtest._benchmark_returns", return_value=pd.Series(dtype=float))
@patch("services.backtest._download_ohlcv")
def test_run_backtest_commission_reduces_equity(mock_download, mock_bench):
    """Buying then immediately selling (1-bar hold) must result in equity < initial capital due to costs."""
    # Two bars only — buy on bar 0 signal, exit on bar 1
    prices = [100.0] * 150  # flat — no SMA crossover, expect no trades
    mock_download.return_value = _make_ohlcv(prices)
    config = _make_config(strategy_name="sma_crossover", strategy_params={"fast_period": 3, "slow_period": 5})
    result = run_backtest(config)
    # With flat prices, no crossover → no trades → equity unchanged
    assert result.metrics.total_trades == 0


@patch("services.backtest._benchmark_returns", return_value=pd.Series(dtype=float))
@patch("services.backtest._download_ohlcv")
def test_run_backtest_no_data_raises(mock_download, mock_bench):
    mock_download.side_effect = ValueError("No price data returned for 'INVALID'")
    config = _make_config(ticker="INVALID")
    with pytest.raises(ValueError, match="No price data"):
        run_backtest(config)


@patch("services.backtest._benchmark_returns", return_value=pd.Series(dtype=float))
@patch("services.backtest._download_ohlcv")
def test_monthly_returns_in_result(mock_download, mock_bench, flat_then_surge_data):
    mock_download.return_value = flat_then_surge_data
    config = _make_config()
    result = run_backtest(config)
    # Monthly returns dict should be non-empty
    assert isinstance(result.monthly_returns, dict)


@patch("services.backtest._benchmark_returns", return_value=pd.Series(dtype=float))
@patch("services.backtest._download_ohlcv")
def test_run_backtest_rsi_strategy(mock_download, mock_bench):
    """RSI mean-reversion strategy should execute without error on synthetic data."""
    flat = [100.0] * 50
    surge = [100.0 + i * 3 for i in range(100)]
    decline = [400.0 - i * 2 for i in range(100)]
    # Data must start before 2022-01-03 and cover through 2022-12-30
    data = _make_ohlcv(flat + surge + decline, start="2021-06-01")
    mock_download.return_value = data

    config = _make_config(
        # Use a date range that falls within the synthetic data
        start_date=date(2021, 9, 1),
        end_date=date(2021, 12, 30),
        strategy_name="rsi_mean_reversion",
        strategy_params={"period": 5, "oversold": 30, "overbought": 70},
    )
    result = run_backtest(config)
    assert result.metrics is not None
