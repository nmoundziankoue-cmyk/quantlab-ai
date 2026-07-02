"""M14 Phase 12 — Tests: alternative feature store (Phase 7)."""
import pytest
from services.alt_feature_store import (
    AltFeatureDefinition,
    ALT_FEATURE_CATALOG,
    ALT_FEATURE_NAMES,
    AltDataBundle,
    AltFeatureStore,
    get_default_alt_feature_store,
    _growth_rate,
    _hhi,
    _tanh_clip,
)


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

def test_catalog_has_15_features():
    assert len(ALT_FEATURE_CATALOG) == 15


def test_catalog_feature_names():
    assert len(ALT_FEATURE_NAMES) == 15
    assert "alt_sentiment" in ALT_FEATURE_NAMES
    assert "alt_insider_buying_ratio" in ALT_FEATURE_NAMES
    assert "alt_patent_growth" in ALT_FEATURE_NAMES
    assert "alt_event_density" in ALT_FEATURE_NAMES


def test_catalog_fields():
    for f in ALT_FEATURE_CATALOG:
        assert isinstance(f, AltFeatureDefinition)
        assert f.name
        assert f.category
        assert f.description


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def test_growth_rate_insufficient_data():
    assert _growth_rate([]) == 0.0
    assert _growth_rate([10.0]) == 0.0


def test_growth_rate_positive():
    r = _growth_rate([10.0, 10.0, 20.0])
    assert r > 0


def test_growth_rate_negative():
    r = _growth_rate([20.0, 20.0, 10.0])
    assert r < 0


def test_growth_rate_clamped():
    r = _growth_rate([1.0, 1.0, 1000.0])
    assert -1.0 <= r <= 1.0


def test_growth_rate_zero_prior():
    r = _growth_rate([0.0, 0.0, 5.0])
    assert r == 0.0


def test_hhi_empty():
    assert _hhi([]) == 0.0


def test_hhi_monopoly():
    h = _hhi([1.0])
    assert abs(h - 1.0) < 1e-6


def test_hhi_equal_shares():
    h = _hhi([0.25, 0.25, 0.25, 0.25])
    assert abs(h - 0.25) < 1e-4


def test_hhi_concentration_increases():
    h_frag = _hhi([0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1])
    h_conc = _hhi([0.8, 0.1, 0.05, 0.05])
    assert h_conc > h_frag


def test_hhi_range():
    assert 0 <= _hhi([0.5, 0.3, 0.2]) <= 1.0


def test_tanh_clip_zero():
    assert _tanh_clip(0) == 0.0


def test_tanh_clip_positive():
    assert _tanh_clip(1.0) > 0


def test_tanh_clip_negative():
    assert _tanh_clip(-1.0) < 0


def test_tanh_clip_bounded():
    assert -1.0 < _tanh_clip(1000.0) <= 1.0
    assert -1.0 <= _tanh_clip(-1000.0) < 0.0


# ---------------------------------------------------------------------------
# AltDataBundle
# ---------------------------------------------------------------------------

def test_bundle_defaults():
    b = AltDataBundle(symbol="AAPL")
    assert b.symbol == "AAPL"
    assert b.insider_buys == 0
    assert b.window_days == 30


# ---------------------------------------------------------------------------
# AltFeatureStore
# ---------------------------------------------------------------------------

@pytest.fixture()
def store():
    return AltFeatureStore()


def make_bundle(**kwargs):
    defaults = dict(
        symbol="AAPL",
        documents=[{"text": "Revenue grew 12%. Strong earnings beat."}],
        insider_buys=10,
        insider_sells=4,
        executive_changes=1,
        total_executives=10,
        earnings_surprises=[0.1, 0.05, 0.08],
        patent_counts_by_period=[45, 52, 61, 74],
        supplier_concentration_shares=[0.35, 0.2, 0.15, 0.1, 0.1, 0.1],
        customer_concentration_shares=[0.4, 0.3, 0.2, 0.1],
        news_mentions_by_period=[10, 12, 15, 20, 18],
        social_mentions_by_period=[100, 120, 150, 200],
        search_trend_values=[60.0, 65.0, 70.0, 72.0],
        transcript_texts=["We are very pleased with the results. Revenue grew significantly."],
        window_days=90,
    )
    defaults.update(kwargs)
    return AltDataBundle(**defaults)


def test_catalog_method(store):
    cat = store.catalog()
    assert len(cat) == 15
    assert all("name" in f and "category" in f for f in cat)


def test_compute_returns_all_features(store):
    bundle = make_bundle()
    features = store.compute(bundle)
    assert set(features.keys()) == set(ALT_FEATURE_NAMES)


def test_compute_feature_ranges(store):
    bundle = make_bundle()
    features = store.compute(bundle)
    # All features should be finite floats
    for name, val in features.items():
        assert isinstance(val, float), f"{name} is not float"
        assert -2.0 <= val <= 2.0, f"{name}={val} out of expected range"


def test_insider_buying_ratio_all_buys(store):
    b = make_bundle(insider_buys=10, insider_sells=0)
    f = store.compute(b, use_cache=False)
    assert f["alt_insider_buying_ratio"] == 1.0


def test_insider_buying_ratio_neutral_no_trades(store):
    b = make_bundle(insider_buys=0, insider_sells=0)
    f = store.compute(b, use_cache=False)
    assert f["alt_insider_buying_ratio"] == 0.5


def test_executive_turnover_none(store):
    b = make_bundle(executive_changes=0, total_executives=10)
    f = store.compute(b, use_cache=False)
    assert f["alt_executive_turnover"] == 0.0


def test_executive_turnover_full(store):
    b = make_bundle(executive_changes=10, total_executives=10)
    f = store.compute(b, use_cache=False)
    assert f["alt_executive_turnover"] == 1.0


def test_esg_placeholder(store):
    b = make_bundle(esg_score=None)
    f = store.compute(b, use_cache=False)
    assert f["alt_esg_score"] == 0.5


def test_esg_provided(store):
    b = make_bundle(esg_score=0.75)
    f = store.compute(b, use_cache=False)
    assert f["alt_esg_score"] == 0.75


def test_search_trend_score_zero_when_empty(store):
    b = make_bundle(search_trend_values=[])
    f = store.compute(b, use_cache=False)
    assert f["alt_search_trend_score"] == 0.0


def test_cache_used(store):
    bundle = make_bundle()
    f1 = store.compute(bundle, use_cache=True)
    f2 = store.compute(bundle, use_cache=True)
    assert f1 == f2


def test_invalidate_clears_cache(store):
    bundle = make_bundle()
    store.compute(bundle, use_cache=True)
    store.invalidate("AAPL")
    # After invalidation, recomputing should still work
    f = store.compute(bundle, use_cache=False)
    assert len(f) == 15


def test_clear_clears_all(store):
    bundle = make_bundle()
    store.compute(bundle, use_cache=True)
    store.clear()
    f = store.compute(bundle, use_cache=False)
    assert len(f) == 15


def test_singleton():
    s1 = get_default_alt_feature_store()
    s2 = get_default_alt_feature_store()
    assert s1 is s2
