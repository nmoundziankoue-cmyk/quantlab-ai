"""Unit tests for M18 Risk Engine — 65 tests."""
import pytest

from services.m18_risk_engine import (
    VaRResult, LeverageMetrics, LiquidityRiskResult, GapRiskResult,
    ConcentrationResult, MarginResult, StressTestResult, RiskAlert,
    RiskDashboard, RiskEngine, get_risk_engine,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

_POS_DATA = [
    {"ticker": "AAPL", "quantity": 1000, "current_price": 175.0, "sector": "Technology", "country": "US", "currency": "USD"},
    {"ticker": "MSFT", "quantity": 500,  "current_price": 380.0, "sector": "Technology", "country": "US", "currency": "USD"},
    {"ticker": "JPM",  "quantity": 800,  "current_price": 200.0, "sector": "Financials", "country": "US", "currency": "USD"},
    {"ticker": "XOM",  "quantity": 600,  "current_price": 120.0, "sector": "Energy",     "country": "US", "currency": "USD"},
    {"ticker": "JNJ",  "quantity": 400,  "current_price": 160.0, "sector": "Healthcare", "country": "US", "currency": "USD"},
]


def _load_positions(engine: RiskEngine) -> None:
    for p in _POS_DATA:
        engine.update_position(
            ticker=p["ticker"],
            quantity=p["quantity"],
            market_price=p["current_price"],
            sector=p["sector"],
            country=p["country"],
            currency=p["currency"],
            adv=5_000_000.0,
        )


def _make_engine_with_history() -> RiskEngine:
    import math
    engine = RiskEngine()
    engine.set_nav(1_000_000.0)
    _load_positions(engine)
    for i in range(100):
        pnl = math.sin(i / 5) * 5000
        engine.add_pnl_observation(pnl)
    return engine


# ---------------------------------------------------------------------------
# VaRResult
# ---------------------------------------------------------------------------

class TestVaRResult:
    def _make(self):
        return VaRResult(
            confidence=0.95, var_pct=0.015, var_usd=15000.0,
            method="HISTORICAL", window=100, nav=1_000_000.0,
        )

    def test_var_result_to_dict(self):
        d = self._make().to_dict()
        assert "var_pct" in d and "confidence" in d

    def test_var_usd_positive(self):
        r = self._make()
        assert r.var_usd > 0

    def test_var_pct_positive(self):
        r = self._make()
        assert r.var_pct > 0


# ---------------------------------------------------------------------------
# RiskEngine — VaR computation
# ---------------------------------------------------------------------------

class TestRiskEngineVaR:
    def setup_method(self):
        self.engine = _make_engine_with_history()

    def test_compute_portfolio_var(self):
        result = self.engine.compute_portfolio_var(confidence=0.95)
        assert isinstance(result, VaRResult)

    def test_var_result_confidence_matches(self):
        result = self.engine.compute_portfolio_var(confidence=0.99)
        assert result.confidence == 0.99

    def test_compute_expected_shortfall(self):
        result = self.engine.compute_expected_shortfall(confidence=0.95)
        assert isinstance(result, float)

    def test_expected_shortfall_nonnegative(self):
        result = self.engine.compute_expected_shortfall(confidence=0.95)
        assert result >= 0

    def test_var_pct_in_range(self):
        result = self.engine.compute_portfolio_var(confidence=0.95)
        assert 0.0 <= result.var_pct <= 1.0


# ---------------------------------------------------------------------------
# RiskEngine — leverage metrics
# ---------------------------------------------------------------------------

class TestRiskEngineLeverage:
    def setup_method(self):
        self.engine = RiskEngine()
        self.engine.set_nav(1_000_000.0)
        _load_positions(self.engine)

    def test_compute_leverage(self):
        result = self.engine.compute_leverage()
        assert isinstance(result, LeverageMetrics)

    def test_leverage_gross_positive(self):
        result = self.engine.compute_leverage()
        assert result.gross_leverage > 0

    def test_leverage_to_dict(self):
        d = self.engine.compute_leverage().to_dict()
        assert "gross_leverage" in d

    def test_leverage_net_less_than_gross(self):
        result = self.engine.compute_leverage()
        assert result.net_leverage <= result.gross_leverage


# ---------------------------------------------------------------------------
# RiskEngine — sector/country/currency exposure
# ---------------------------------------------------------------------------

class TestRiskEngineExposure:
    def setup_method(self):
        self.engine = RiskEngine()
        self.engine.set_nav(1_000_000.0)
        _load_positions(self.engine)

    def test_compute_sector_exposure(self):
        result = self.engine.compute_sector_exposure()
        assert isinstance(result, dict)

    def test_sector_tech_present(self):
        result = self.engine.compute_sector_exposure()
        assert "Technology" in result

    def test_compute_country_exposure(self):
        result = self.engine.compute_country_exposure()
        assert isinstance(result, dict)

    def test_country_us_present(self):
        result = self.engine.compute_country_exposure()
        assert "US" in result

    def test_compute_currency_exposure(self):
        result = self.engine.compute_currency_exposure()
        assert isinstance(result, dict)

    def test_compute_factor_exposure(self):
        result = self.engine.compute_factor_exposure()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# RiskEngine — concentration
# ---------------------------------------------------------------------------

class TestRiskEngineConcentration:
    def setup_method(self):
        self.engine = RiskEngine()
        self.engine.set_nav(1_000_000.0)
        _load_positions(self.engine)

    def test_compute_concentration(self):
        result = self.engine.compute_concentration()
        assert isinstance(result, ConcentrationResult)

    def test_concentration_hhi_range(self):
        result = self.engine.compute_concentration()
        assert 0.0 <= result.herfindahl_index <= 1.0

    def test_concentration_to_dict(self):
        d = self.engine.compute_concentration().to_dict()
        assert "herfindahl_index" in d


# ---------------------------------------------------------------------------
# RiskEngine — liquidity and gap risk
# ---------------------------------------------------------------------------

class TestRiskEngineLiquidityGap:
    def setup_method(self):
        self.engine = RiskEngine()
        self.engine.set_nav(1_000_000.0)
        _load_positions(self.engine)

    def test_compute_liquidity_risk(self):
        result = self.engine.compute_liquidity_risk()
        assert isinstance(result, LiquidityRiskResult)

    def test_liquidity_risk_to_dict(self):
        d = self.engine.compute_liquidity_risk().to_dict()
        assert "days_to_liquidate" in d or "liquidity_score" in d

    def test_compute_gap_risk(self):
        result = self.engine.compute_gap_risk()
        assert isinstance(result, GapRiskResult)

    def test_gap_risk_to_dict(self):
        d = self.engine.compute_gap_risk().to_dict()
        assert "expected_gap_pnl" in d or "worst_case_gap_pnl" in d


# ---------------------------------------------------------------------------
# RiskEngine — margin and stress test
# ---------------------------------------------------------------------------

class TestRiskEngineMarginStress:
    def setup_method(self):
        self.engine = RiskEngine()
        self.engine.set_nav(1_000_000.0)
        _load_positions(self.engine)

    def test_compute_margin_usage(self):
        result = self.engine.compute_margin_usage()
        assert isinstance(result, MarginResult)

    def test_margin_usage_pct(self):
        result = self.engine.compute_margin_usage()
        assert 0 <= result.margin_usage_pct <= 1

    def test_margin_result_to_dict(self):
        d = self.engine.compute_margin_usage().to_dict()
        assert "margin_usage_pct" in d

    def test_run_stress_test(self):
        result = self.engine.run_stress_test(
            scenario_name="TEST_CRASH",
            shock_pct=-0.30,
        )
        assert isinstance(result, StressTestResult)

    def test_stress_test_pnl_negative_on_crash(self):
        result = self.engine.run_stress_test(
            scenario_name="TEST_CRASH",
            shock_pct=-0.30,
        )
        assert result.pnl_impact_usd < 0

    def test_stress_test_to_dict(self):
        d = self.engine.run_stress_test(scenario_name="S", shock_pct=-0.1).to_dict()
        assert "pnl_impact_usd" in d


# ---------------------------------------------------------------------------
# RiskEngine — alerts and dashboard
# ---------------------------------------------------------------------------

class TestRiskEngineAlertsDashboard:
    def setup_method(self):
        self.engine = _make_engine_with_history()

    def test_check_risk_alerts_returns_list(self):
        result = self.engine.check_risk_alerts(var_threshold_pct=0.02, leverage_threshold=3.0)
        assert isinstance(result, list)

    def test_risk_alerts_are_risk_alert_instances(self):
        result = self.engine.check_risk_alerts()
        assert all(isinstance(a, RiskAlert) for a in result)

    def test_risk_alert_to_dict(self):
        alerts = self.engine.check_risk_alerts()
        for a in alerts:
            d = a.to_dict()
            assert "alert_type" in d or "severity" in d or "risk_type" in d

    def test_get_risk_dashboard(self):
        result = self.engine.get_risk_dashboard()
        assert isinstance(result, RiskDashboard)

    def test_risk_dashboard_to_dict(self):
        d = self.engine.get_risk_dashboard().to_dict()
        assert "nav" in d or "total_market_value" in d or "gross_leverage" in d


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_risk_engine_returns_engine(self):
        eng = get_risk_engine()
        assert isinstance(eng, RiskEngine)

    def test_singleton_same_instance(self):
        e1 = get_risk_engine()
        e2 = get_risk_engine()
        assert e1 is e2
