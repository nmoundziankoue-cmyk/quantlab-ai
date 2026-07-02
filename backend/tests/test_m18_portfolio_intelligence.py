"""Unit tests for M18 Portfolio Intelligence Engine — 65 tests."""
import pytest
import math

from services.m18_portfolio_intelligence import (
    BrinsonAttribution, FactorAttribution, RebalanceTrade,
    EfficientFrontierPoint, PortfolioScore, TailRiskMetrics,
    HoldingRecord, PortfolioSummary,
    PortfolioIntelligenceEngine, get_portfolio_intelligence_engine,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_engine() -> PortfolioIntelligenceEngine:
    engine = PortfolioIntelligenceEngine()
    engine.set_nav(5_000_000.0)
    return engine


def _add_holdings(engine: PortfolioIntelligenceEngine):
    holdings = [
        ("AAPL", 0.20, "Technology", 0.18, 0.25, 150.0, 175.0, 1000),
        ("MSFT", 0.18, "Technology", 0.16, 0.22, 300.0, 380.0, 500),
        ("JPM",  0.12, "Financials", 0.10, 0.20, 180.0, 200.0, 800),
        ("XOM",  0.10, "Energy",     0.09, 0.25, 100.0, 120.0, 600),
        ("JNJ",  0.08, "Healthcare", 0.07, 0.18, 155.0, 160.0, 400),
    ]
    for ticker, weight, sector, er, vol, cb, cp, qty in holdings:
        engine.update_holding(ticker, weight=weight, sector=sector,
                              expected_return=er, volatility=vol,
                              cost_basis=cb, current_price=cp, quantity=qty)


def _add_return_history(engine: PortfolioIntelligenceEngine, n: int = 100):
    for i in range(n):
        pnl = math.sin(i / 5) * 0.01
        engine.add_return_observation(pnl, 0.0003)


# ---------------------------------------------------------------------------
# Holding management
# ---------------------------------------------------------------------------

class TestHoldingManagement:
    def setup_method(self):
        self.engine = _make_engine()

    def test_add_holding(self):
        self.engine.update_holding("AAPL", weight=0.20, sector="Technology")
        holdings = self.engine.get_all_holdings()
        assert any(h.ticker == "AAPL" for h in holdings)

    def test_get_all_holdings_empty(self):
        holdings = self.engine.get_all_holdings()
        assert isinstance(holdings, list)

    def test_remove_holding(self):
        self.engine.update_holding("AAPL", weight=0.20)
        self.engine.remove_holding("AAPL")
        holdings = self.engine.get_all_holdings()
        assert all(h.ticker != "AAPL" for h in holdings)

    def test_update_holding(self):
        self.engine.update_holding("AAPL", weight=0.20, current_price=175.0)
        self.engine.update_holding("AAPL", weight=0.22, current_price=185.0)
        holdings = self.engine.get_all_holdings()
        aapl = next(h for h in holdings if h.ticker == "AAPL")
        assert aapl.weight == 0.22

    def test_holding_record_to_dict(self):
        self.engine.update_holding("AAPL", weight=0.20)
        h = self.engine.get_all_holdings()[0]
        assert isinstance(h, HoldingRecord)
        d = h.to_dict()
        assert "ticker" in d and "weight" in d


# ---------------------------------------------------------------------------
# Portfolio summary
# ---------------------------------------------------------------------------

class TestPortfolioSummary:
    def setup_method(self):
        self.engine = _make_engine()
        _add_holdings(self.engine)

    def test_get_portfolio_summary(self):
        summary = self.engine.get_portfolio_summary()
        assert isinstance(summary, PortfolioSummary)

    def test_summary_total_holdings(self):
        summary = self.engine.get_portfolio_summary()
        assert summary.num_positions == 5

    def test_summary_to_dict(self):
        d = self.engine.get_portfolio_summary().to_dict()
        assert "num_positions" in d or "nav" in d

    def test_summary_nav(self):
        summary = self.engine.get_portfolio_summary()
        assert summary.nav == 5_000_000.0


# ---------------------------------------------------------------------------
# Brinson attribution
# ---------------------------------------------------------------------------

class TestBrinsonAttribution:
    def setup_method(self):
        self.engine = _make_engine()

    def test_compute_brinson_attribution(self):
        result = self.engine.compute_brinson_attribution(
            portfolio_sector_weights={"Technology": 0.38, "Financials": 0.12},
            benchmark_sector_weights={"Technology": 0.28, "Financials": 0.15},
            portfolio_sector_returns={"Technology": 0.15, "Financials": 0.08},
            benchmark_sector_returns={"Technology": 0.12, "Financials": 0.07},
            benchmark_total_return=0.08,
        )
        assert isinstance(result, BrinsonAttribution)

    def test_brinson_total_active_return(self):
        result = self.engine.compute_brinson_attribution(
            portfolio_sector_weights={"Tech": 0.4},
            benchmark_sector_weights={"Tech": 0.3},
            portfolio_sector_returns={"Tech": 0.15},
            benchmark_sector_returns={"Tech": 0.10},
            benchmark_total_return=0.10,
        )
        assert isinstance(result.total_active_return, float)

    def test_brinson_to_dict(self):
        d = self.engine.compute_brinson_attribution(
            portfolio_sector_weights={"Tech": 0.4},
            benchmark_sector_weights={"Tech": 0.3},
            portfolio_sector_returns={"Tech": 0.15},
            benchmark_sector_returns={"Tech": 0.10},
            benchmark_total_return=0.10,
        ).to_dict()
        assert "allocation_effect" in d or "total_active_return" in d

    def test_brinson_allocation_plus_selection_plus_interaction(self):
        r = self.engine.compute_brinson_attribution(
            portfolio_sector_weights={"Tech": 0.4},
            benchmark_sector_weights={"Tech": 0.3},
            portfolio_sector_returns={"Tech": 0.15},
            benchmark_sector_returns={"Tech": 0.10},
            benchmark_total_return=0.10,
        )
        total = r.allocation_effect + r.selection_effect + r.interaction_effect
        assert abs(total - r.total_active_return) < 0.01


# ---------------------------------------------------------------------------
# Factor attribution
# ---------------------------------------------------------------------------

class TestFactorAttribution:
    def setup_method(self):
        self.engine = _make_engine()

    def test_compute_factor_attribution(self):
        result = self.engine.compute_factor_attribution(
            portfolio_return=0.09,
            factor_exposures={"Market Beta": 1.05, "Value": 0.3, "Momentum": 0.5},
            factor_returns={"Market Beta": 0.063, "Value": 0.02, "Momentum": 0.03},
        )
        assert isinstance(result, FactorAttribution)

    def test_factor_attribution_to_dict(self):
        d = self.engine.compute_factor_attribution(
            portfolio_return=0.09,
            factor_exposures={"Market Beta": 1.05},
            factor_returns={"Market Beta": 0.063},
        ).to_dict()
        assert "specific_return" in d or "total_return" in d


# ---------------------------------------------------------------------------
# Rebalancing
# ---------------------------------------------------------------------------

class TestRebalancing:
    def setup_method(self):
        self.engine = _make_engine()
        _add_holdings(self.engine)

    def test_compute_rebalancing_trades(self):
        target_weights = {"AAPL": 0.15, "MSFT": 0.15, "JPM": 0.15, "XOM": 0.15, "JNJ": 0.15}
        result = self.engine.compute_rebalancing_trades(target_weights=target_weights)
        assert isinstance(result, list)

    def test_rebalance_trade_to_dict(self):
        target_weights = {"AAPL": 0.15, "MSFT": 0.15}
        trades = self.engine.compute_rebalancing_trades(target_weights=target_weights)
        for trade in trades:
            assert isinstance(trade, RebalanceTrade)
            d = trade.to_dict()
            assert "ticker" in d


# ---------------------------------------------------------------------------
# Efficient frontier
# ---------------------------------------------------------------------------

class TestEfficientFrontier:
    def setup_method(self):
        self.engine = _make_engine()

    def test_compute_efficient_frontier(self):
        result = self.engine.compute_efficient_frontier(
            tickers=["AAPL", "MSFT", "JPM"],
            expected_returns={"AAPL": 0.18, "MSFT": 0.16, "JPM": 0.10},
            covariance_matrix={},
            n_points=10,
            risk_free=0.05,
        )
        assert isinstance(result, list)

    def test_efficient_frontier_has_points(self):
        result = self.engine.compute_efficient_frontier(
            tickers=["A", "B"],
            expected_returns={"A": 0.12, "B": 0.08},
            covariance_matrix={},
            n_points=5,
        )
        assert len(result) > 0

    def test_frontier_points_are_efficient_frontier_point(self):
        result = self.engine.compute_efficient_frontier(
            tickers=["A", "B"],
            expected_returns={"A": 0.12, "B": 0.08},
            covariance_matrix={},
            n_points=3,
        )
        for pt in result:
            assert isinstance(pt, EfficientFrontierPoint)


# ---------------------------------------------------------------------------
# Portfolio score
# ---------------------------------------------------------------------------

class TestPortfolioScore:
    def setup_method(self):
        self.engine = _make_engine()
        _add_holdings(self.engine)

    def test_compute_portfolio_score(self):
        result = self.engine.compute_portfolio_score()
        assert isinstance(result, PortfolioScore)

    def test_score_overall_in_range(self):
        result = self.engine.compute_portfolio_score()
        assert 0 <= result.overall <= 100

    def test_score_to_dict(self):
        d = self.engine.compute_portfolio_score().to_dict()
        assert "overall" in d


# ---------------------------------------------------------------------------
# Tail risk
# ---------------------------------------------------------------------------

class TestTailRisk:
    def setup_method(self):
        self.engine = _make_engine()
        _add_return_history(self.engine)

    def test_compute_tail_risk(self):
        result = self.engine.compute_tail_risk()
        assert isinstance(result, TailRiskMetrics)

    def test_tail_risk_to_dict(self):
        d = self.engine.compute_tail_risk().to_dict()
        assert "var_95" in d or "es_95" in d


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_portfolio_intelligence_engine(self):
        eng = get_portfolio_intelligence_engine()
        assert isinstance(eng, PortfolioIntelligenceEngine)

    def test_singleton_same_instance(self):
        e1 = get_portfolio_intelligence_engine()
        e2 = get_portfolio_intelligence_engine()
        assert e1 is e2
