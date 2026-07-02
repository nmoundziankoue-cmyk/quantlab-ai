"""Tests for M17 Trade Analytics Engine."""
import pytest
from datetime import datetime, timezone, timedelta
from services.trade_analytics import (
    TradeAnalyticsEngine, TradeRecord, TradeStatistics,
    PortfolioPerformanceMetrics, SectorAttribution,
)


def _eng():
    return TradeAnalyticsEngine()


def _trade(trade_id="T001", ticker="AAPL", side="BUY", qty=100,
           entry=170.0, exit_=180.0, pnl=1000.0, commission=2.5,
           sector="TECHNOLOGY", days_held=10):
    now = datetime.now(timezone.utc)
    return TradeRecord(
        trade_id=trade_id,
        ticker=ticker,
        side=side,
        quantity=qty,
        entry_price=entry,
        exit_price=exit_,
        entry_datetime=now - timedelta(days=days_held),
        exit_datetime=now,
        commission=commission,
        pnl=pnl,
        sector=sector,
    )


# ---------------------------------------------------------------------------
# add_trade / compute_statistics
# ---------------------------------------------------------------------------

class TestComputeStatistics:
    def test_add_trade_and_compute(self):
        e = _eng()
        e.add_trade(_trade())
        s = e.compute_statistics()
        assert s.total_trades == 1

    def test_win_rate_all_wins(self):
        e = _eng()
        for i in range(5):
            e.add_trade(_trade(trade_id=f"T{i}", pnl=1000.0))
        s = e.compute_statistics()
        assert s.win_rate == pytest.approx(1.0)

    def test_win_rate_mixed(self):
        e = _eng()
        e.add_trade(_trade(trade_id="T1", pnl=1000.0))
        e.add_trade(_trade(trade_id="T2", pnl=-500.0))
        s = e.compute_statistics()
        assert s.win_rate == pytest.approx(0.5)

    def test_win_rate_all_losses(self):
        e = _eng()
        for i in range(3):
            e.add_trade(_trade(trade_id=f"T{i}", pnl=-500.0))
        s = e.compute_statistics()
        assert s.win_rate == pytest.approx(0.0)

    def test_profit_factor_wins_only(self):
        e = _eng()
        e.add_trade(_trade(trade_id="T1", pnl=1000.0))
        e.add_trade(_trade(trade_id="T2", pnl=500.0))
        s = e.compute_statistics()
        assert s.profit_factor > 1.0

    def test_profit_factor_with_losses(self):
        e = _eng()
        e.add_trade(_trade(trade_id="T1", pnl=1000.0))
        e.add_trade(_trade(trade_id="T2", pnl=-400.0))
        s = e.compute_statistics()
        assert s.profit_factor == pytest.approx(2.5, rel=1e-4)

    def test_total_pnl(self):
        e = _eng()
        e.add_trade(_trade(trade_id="T1", pnl=1000.0))
        e.add_trade(_trade(trade_id="T2", pnl=-300.0))
        s = e.compute_statistics()
        assert s.total_pnl == pytest.approx(700.0)

    def test_expectancy(self):
        e = _eng()
        e.add_trade(_trade(trade_id="T1", pnl=1000.0))
        e.add_trade(_trade(trade_id="T2", pnl=-400.0))
        s = e.compute_statistics()
        assert s.expectancy == pytest.approx(300.0)

    def test_kelly_fraction_positive_edge(self):
        e = _eng()
        for i in range(6):
            e.add_trade(_trade(trade_id=f"W{i}", pnl=500.0))
        for i in range(4):
            e.add_trade(_trade(trade_id=f"L{i}", pnl=-300.0))
        s = e.compute_statistics()
        assert 0.0 < s.kelly_fraction <= 1.0

    def test_kelly_fraction_clamped_zero_one(self):
        e = _eng()
        e.add_trade(_trade(trade_id="T1", pnl=1000000.0))
        s = e.compute_statistics()
        assert 0.0 <= s.kelly_fraction <= 1.0

    def test_avg_holding_days(self):
        e = _eng()
        e.add_trade(_trade(trade_id="T1", days_held=10))
        e.add_trade(_trade(trade_id="T2", days_held=20))
        s = e.compute_statistics()
        assert s.avg_holding_days == pytest.approx(15.0, abs=1.0)

    def test_returns_trade_statistics(self):
        e = _eng()
        e.add_trade(_trade())
        s = e.compute_statistics()
        assert isinstance(s, TradeStatistics)

    def test_empty_engine_raises(self):
        e = _eng()
        with pytest.raises(ValueError):
            e.compute_statistics()


# ---------------------------------------------------------------------------
# portfolio_performance
# ---------------------------------------------------------------------------

class TestPortfolioPerformance:
    def test_returns_metrics(self):
        e = _eng()
        returns = [0.01, 0.02, -0.005, 0.015, 0.008, -0.01, 0.02, 0.005, 0.012, -0.003]
        m = e.portfolio_performance(returns, periods_per_year=252)
        assert isinstance(m, PortfolioPerformanceMetrics)

    def test_sharpe_positive_varying_returns(self):
        e = _eng()
        returns = [0.01, 0.02, -0.005, 0.015, 0.008, -0.002, 0.018, 0.007, 0.012, 0.004]
        m = e.portfolio_performance(returns, periods_per_year=252)
        assert m.sharpe_ratio > 0

    def test_annualised_return_positive(self):
        e = _eng()
        returns = [0.001] * 252
        m = e.portfolio_performance(returns, periods_per_year=252)
        assert m.annualised_return > 0

    def test_max_drawdown_zero_for_monotone_rising(self):
        e = _eng()
        returns = [0.001] * 50
        m = e.portfolio_performance(returns, periods_per_year=252)
        assert m.max_drawdown == pytest.approx(0.0, abs=1e-10)

    def test_max_drawdown_negative_for_declining(self):
        e = _eng()
        returns = [-0.01] * 20
        m = e.portfolio_performance(returns, periods_per_year=252)
        assert m.max_drawdown < 0

    def test_volatility_positive(self):
        e = _eng()
        returns = [0.01, -0.01, 0.02, -0.02, 0.015]
        m = e.portfolio_performance(returns, periods_per_year=252)
        assert m.annualised_volatility > 0

    def test_calmar_ratio_positive(self):
        e = _eng()
        returns = [0.005] * 50 + [-0.001] * 5 + [0.005] * 50
        m = e.portfolio_performance(returns, periods_per_year=252)
        assert m.calmar_ratio is not None


# ---------------------------------------------------------------------------
# kelly_fraction
# ---------------------------------------------------------------------------

class TestKellyFraction:
    def test_kelly_positive_edge(self):
        e = _eng()
        k = e.kelly_fraction(win_rate=0.6, avg_win=500.0, avg_loss=300.0)
        assert k > 0.0

    def test_kelly_formula(self):
        e = _eng()
        wr, lr = 0.6, 0.4
        w, l = 500.0, 300.0
        expected = wr - lr * (l / w)
        k = e.kelly_fraction(win_rate=wr, avg_win=w, avg_loss=l)
        assert k == pytest.approx(min(max(expected, 0.0), 1.0), rel=1e-4)

    def test_kelly_clamped_negative_edge(self):
        e = _eng()
        k = e.kelly_fraction(win_rate=0.2, avg_win=100.0, avg_loss=500.0)
        assert k == pytest.approx(0.0)

    def test_kelly_clamped_max_one(self):
        e = _eng()
        k = e.kelly_fraction(win_rate=1.0, avg_win=1000.0, avg_loss=1.0)
        assert k <= 1.0


# ---------------------------------------------------------------------------
# sector_attribution / symbol_attribution
# ---------------------------------------------------------------------------

class TestAttributions:
    def test_sector_attribution(self):
        e = _eng()
        e.add_trade(_trade(trade_id="T1", ticker="AAPL", sector="TECHNOLOGY", pnl=1000.0))
        e.add_trade(_trade(trade_id="T2", ticker="JPM", sector="FINANCIALS", pnl=-200.0))
        attrs = e.sector_attribution()
        sectors = [a.sector for a in attrs]
        assert "TECHNOLOGY" in sectors
        assert "FINANCIALS" in sectors

    def test_symbol_attribution(self):
        e = _eng()
        e.add_trade(_trade(trade_id="T1", ticker="AAPL", pnl=800.0))
        e.add_trade(_trade(trade_id="T2", ticker="AAPL", pnl=200.0))
        attrs = e.symbol_attribution()
        aapl = next((a for a in attrs if a["ticker"] == "AAPL"), None)
        assert aapl is not None
        assert aapl["total_pnl"] == pytest.approx(1000.0)
