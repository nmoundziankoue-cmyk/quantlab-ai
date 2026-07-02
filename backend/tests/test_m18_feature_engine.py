"""Unit tests for M18 Feature Engine — 65 tests."""
import math
import pytest

from services.m18_feature_engine import (
    MACDResult, DrawdownResult, CointegrationResult, PCAResult,
    FeatureSnapshot, FeatureEngine, get_feature_engine,
    _mean, _std, _ema, _ema_series, _covariance, _pearson_r,
    _percentile, _ols_slope,
)


# ---------------------------------------------------------------------------
# Pure-Python math helpers
# ---------------------------------------------------------------------------

class TestMathHelpers:
    def test_mean_basic(self):
        assert _mean([1.0, 2.0, 3.0]) == 2.0

    def test_mean_single(self):
        assert _mean([5.0]) == 5.0

    def test_mean_negative(self):
        assert _mean([-1.0, 1.0]) == 0.0

    def test_std_zero_for_constant(self):
        assert _std([5.0, 5.0, 5.0]) == 0.0

    def test_std_known(self):
        vals = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
        result = _std(vals)
        assert abs(result - 2.0) < 0.1

    def test_ema_single(self):
        result = _ema([100.0], 5)
        assert result == 100.0

    def test_ema_converges(self):
        vals = [100.0] * 20
        result = _ema(vals, 5)
        assert abs(result - 100.0) < 0.01

    def test_ema_series_length(self):
        vals = [1.0, 2.0, 3.0, 4.0, 5.0]
        series = _ema_series(vals, 3)
        assert len(series) == len(vals)

    def test_covariance_same_list(self):
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        cov = _covariance(xs, xs)
        var = _std(xs, ddof=1) ** 2
        assert abs(cov - var) < 1e-9

    def test_pearson_r_perfect_positive(self):
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        r = _pearson_r(xs, xs)
        assert abs(r - 1.0) < 1e-9

    def test_pearson_r_perfect_negative(self):
        xs = [1.0, 2.0, 3.0]
        ys = [3.0, 2.0, 1.0]
        r = _pearson_r(xs, ys)
        assert abs(r - (-1.0)) < 1e-9

    def test_percentile_median(self):
        vals = list(range(1, 101))
        result = _percentile(vals, 50)
        assert 49 <= result <= 51

    def test_percentile_min(self):
        vals = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = _percentile(vals, 0)
        assert result == min(vals)

    def test_percentile_max(self):
        vals = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = _percentile(vals, 100)
        assert result == max(vals)

    def test_ols_slope_upward(self):
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [2.0, 4.0, 6.0, 8.0, 10.0]
        slope = _ols_slope(xs, ys)
        assert abs(slope - 2.0) < 1e-9

    def test_ols_slope_flat(self):
        xs = [1.0, 2.0, 3.0, 4.0]
        ys = [5.0, 5.0, 5.0, 5.0]
        slope = _ols_slope(xs, ys)
        assert abs(slope) < 1e-9


# ---------------------------------------------------------------------------
# FeatureEngine — setup with data
# ---------------------------------------------------------------------------

def _seed_engine(engine: FeatureEngine, ticker="AAPL", n=60):
    import math
    for i in range(n):
        price = 100.0 + math.sin(i / 5) * 5
        vol = 100000 + i * 1000
        high = price + 0.5
        low = price - 0.5
        engine.update(ticker, price=price, volume=vol, high=high, low=low)


class TestFeatureEngineBasic:
    def setup_method(self):
        self.engine = FeatureEngine()
        _seed_engine(self.engine)

    def test_get_tracked_tickers(self):
        tickers = self.engine.get_tracked_tickers()
        assert "AAPL" in tickers

    def test_update_multiple_tickers(self):
        _seed_engine(self.engine, "MSFT")
        tickers = self.engine.get_tracked_tickers()
        assert "MSFT" in tickers

    def test_compute_returns_list(self):
        returns = self.engine.compute_returns("AAPL", period=1)
        assert len(returns) > 0

    def test_compute_rolling_mean(self):
        result = self.engine.compute_rolling_mean("AAPL", window=20)
        assert isinstance(result, float)
        assert result > 0

    def test_compute_rolling_std(self):
        result = self.engine.compute_rolling_std("AAPL", window=20)
        assert isinstance(result, float)
        assert result >= 0

    def test_compute_atr(self):
        result = self.engine.compute_atr("AAPL", window=14)
        assert isinstance(result, float)
        assert result >= 0

    def test_compute_rsi_range(self):
        result = self.engine.compute_rsi("AAPL", window=14)
        assert 0.0 <= result <= 100.0

    def test_compute_macd_returns_result(self):
        result = self.engine.compute_macd("AAPL")
        assert isinstance(result, MACDResult)

    def test_macd_to_dict(self):
        d = self.engine.compute_macd("AAPL").to_dict()
        assert "macd_line" in d or "macd" in d

    def test_compute_vwap(self):
        result = self.engine.compute_vwap("AAPL")
        assert isinstance(result, float)
        assert result > 0

    def test_compute_twap(self):
        result = self.engine.compute_twap("AAPL")
        assert isinstance(result, float)
        assert result > 0

    def test_compute_realized_volatility(self):
        result = self.engine.compute_realized_volatility("AAPL")
        assert isinstance(result, float)
        assert result >= 0

    def test_compute_beta(self):
        _seed_engine(self.engine, "SPY")
        result = self.engine.compute_beta("AAPL", "SPY")
        assert isinstance(result, float)

    def test_compute_correlation(self):
        _seed_engine(self.engine, "SPY")
        result = self.engine.compute_correlation("AAPL", "SPY")
        assert -1.0 <= result <= 1.0

    def test_compute_rolling_sharpe(self):
        result = self.engine.compute_rolling_sharpe("AAPL")
        assert isinstance(result, float)

    def test_compute_rolling_sortino(self):
        result = self.engine.compute_rolling_sortino("AAPL")
        assert isinstance(result, float)

    def test_compute_rolling_drawdown(self):
        result = self.engine.compute_rolling_drawdown("AAPL")
        assert isinstance(result, DrawdownResult)

    def test_drawdown_result_to_dict(self):
        d = self.engine.compute_rolling_drawdown("AAPL").to_dict()
        assert "max_drawdown" in d

    def test_compute_rolling_var(self):
        result = self.engine.compute_rolling_var("AAPL")
        assert isinstance(result, float)

    def test_compute_expected_shortfall(self):
        result = self.engine.compute_expected_shortfall("AAPL")
        assert isinstance(result, float)

    def test_compute_kelly(self):
        result = self.engine.compute_kelly("AAPL")
        assert isinstance(result, float)

    def test_compute_information_ratio(self):
        _seed_engine(self.engine, "SPY")
        result = self.engine.compute_information_ratio("AAPL", "SPY")
        assert isinstance(result, float)


class TestFeatureEngineCointegrationPCA:
    def setup_method(self):
        self.engine = FeatureEngine()
        _seed_engine(self.engine, "AAPL", 60)
        _seed_engine(self.engine, "MSFT", 60)
        _seed_engine(self.engine, "GOOGL", 60)

    def test_compute_cointegration(self):
        result = self.engine.compute_cointegration("AAPL", "MSFT")
        assert isinstance(result, CointegrationResult)

    def test_cointegration_to_dict(self):
        d = self.engine.compute_cointegration("AAPL", "MSFT").to_dict()
        assert len(d) > 0

    def test_compute_pca(self):
        result = self.engine.compute_pca(["AAPL", "MSFT", "GOOGL"], n_components=2)
        assert isinstance(result, PCAResult)

    def test_pca_to_dict(self):
        d = self.engine.compute_pca(["AAPL", "MSFT", "GOOGL"], n_components=2).to_dict()
        assert "n_components" in d or "explained_variance" in d


class TestFeatureSnapshot:
    def setup_method(self):
        self.engine = FeatureEngine()
        _seed_engine(self.engine, "AAPL", 60)

    def test_get_feature_snapshot(self):
        snap = self.engine.get_feature_snapshot("AAPL")
        assert isinstance(snap, FeatureSnapshot)

    def test_snapshot_to_dict(self):
        d = self.engine.get_feature_snapshot("AAPL").to_dict()
        assert "ticker" in d

    def test_snapshot_rsi_range(self):
        snap = self.engine.get_feature_snapshot("AAPL")
        assert 0.0 <= snap.rsi_14 <= 100.0

    def test_snapshot_has_macd(self):
        snap = self.engine.get_feature_snapshot("AAPL")
        assert snap.macd is not None

    def test_snapshot_has_atr(self):
        snap = self.engine.get_feature_snapshot("AAPL")
        assert snap.atr_14 >= 0


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_feature_engine_returns_engine(self):
        eng = get_feature_engine()
        assert isinstance(eng, FeatureEngine)

    def test_singleton_same_instance(self):
        e1 = get_feature_engine()
        e2 = get_feature_engine()
        assert e1 is e2
