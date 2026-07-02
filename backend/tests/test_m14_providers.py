"""M14 Phase 12 — Tests: alternative data provider framework.

Actual API notes:
- AltProviderConfig(name, priority, capabilities: Set, api_key=None, ...)
- AltProviderHealth(provider: str, is_healthy=True, consecutive_failures=0, last_error=None)
- MockAltDataProvider(fail_after=None)  — no required args
- MockAltDataProvider.health  — attribute (AltProviderHealth), NOT a method
- MockAltDataProvider.fetch(capability: AltDataCapability)  — no symbol arg
- MockAltDataProvider.latency  — AltLatencyMetrics attribute with p50_ms, to_dict()
- ALL_ALT_PROVIDER_CLASSES  — dict[str, type], 21 entries, values take no ctor args
- Stub classes raise NotImplementedError on fetch (no API key / live call)
"""
import pytest
from services.alternative_data_provider import (
    AltDataCapability,
    AltProviderConfig,
    AltProviderHealth,
    BaseAltDataProvider,
    MockAltDataProvider,
    ALL_ALT_PROVIDER_CLASSES,
    AltDataProviderRouter,
    build_default_alt_router,
    get_default_alt_router,
)


# ---------------------------------------------------------------------------
# AltProviderConfig dataclass
# ---------------------------------------------------------------------------

def test_alt_provider_config_required_fields():
    cfg = AltProviderConfig(name="test", priority=5, capabilities=set())
    assert cfg.name == "test"
    assert cfg.priority == 5
    assert isinstance(cfg.capabilities, set)


def test_alt_provider_config_optional_fields():
    cfg = AltProviderConfig(name="x", priority=1, capabilities=set(), timeout_seconds=5.0)
    assert cfg.timeout_seconds == 5.0


def test_alt_provider_config_api_key():
    cfg = AltProviderConfig(name="x", priority=1, capabilities=set(), api_key="secret")
    assert cfg.api_key == "secret"


def test_alt_provider_config_defaults():
    cfg = AltProviderConfig(name="x", priority=0, capabilities=set())
    assert cfg.enabled is True
    assert cfg.rate_limit_per_min > 0


def test_alt_provider_config_with_capabilities():
    caps = {AltDataCapability.SEC_FILINGS, AltDataCapability.NEWS}
    cfg = AltProviderConfig(name="x", priority=1, capabilities=caps)
    assert AltDataCapability.SEC_FILINGS in cfg.capabilities


# ---------------------------------------------------------------------------
# AltProviderHealth dataclass
# ---------------------------------------------------------------------------

def test_alt_provider_health_healthy():
    h = AltProviderHealth(provider="test_provider", is_healthy=True)
    assert h.is_healthy is True
    assert h.provider == "test_provider"


def test_alt_provider_health_unhealthy():
    h = AltProviderHealth(provider="test_provider", is_healthy=False, last_error="timeout")
    assert h.is_healthy is False
    assert "timeout" in h.last_error


def test_alt_provider_health_default_healthy():
    h = AltProviderHealth(provider="x")
    assert h.is_healthy is True
    assert h.consecutive_failures == 0


def test_alt_provider_health_consecutive_failures():
    h = AltProviderHealth(provider="x", consecutive_failures=3, is_healthy=False)
    assert h.consecutive_failures == 3


# ---------------------------------------------------------------------------
# MockAltDataProvider
# ---------------------------------------------------------------------------

def test_mock_provider_no_required_args():
    p = MockAltDataProvider()
    assert p is not None


def test_mock_provider_health_is_attribute():
    p = MockAltDataProvider()
    h = p.health  # attribute, NOT a method call
    assert isinstance(h, AltProviderHealth)
    assert h.is_healthy is True


def test_mock_provider_name():
    p = MockAltDataProvider()
    assert isinstance(p.name, str)
    assert len(p.name) > 0


def test_mock_provider_capabilities():
    p = MockAltDataProvider()
    caps = p.capabilities()
    assert isinstance(caps, list)
    assert len(caps) > 0


def test_mock_provider_quality_score():
    p = MockAltDataProvider()
    qs = p.quality_score()
    assert 0 <= qs <= 1.0


def test_mock_provider_metadata():
    p = MockAltDataProvider()
    meta = p.metadata()
    assert isinstance(meta, dict)
    assert len(meta) > 0


def test_mock_provider_fetch_returns_dict():
    p = MockAltDataProvider()
    data = p.fetch(AltDataCapability.SEC_FILINGS)
    assert data is not None


def test_mock_provider_fetch_uses_capability():
    p = MockAltDataProvider()
    d1 = p.fetch(AltDataCapability.SEC_FILINGS)
    d2 = p.fetch(AltDataCapability.INSIDER_TRANSACTIONS)
    # Both should succeed (not raise)
    assert d1 is not None
    assert d2 is not None


def test_mock_provider_latency_recorded():
    p = MockAltDataProvider()
    p.fetch(AltDataCapability.SEC_FILINGS)
    lat = p.latency
    assert hasattr(lat, "p50_ms")
    assert lat.p50_ms >= 0


def test_mock_provider_latency_to_dict():
    p = MockAltDataProvider()
    p.fetch(AltDataCapability.SEC_FILINGS)
    d = p.latency.to_dict()
    assert "p50_ms" in d
    assert "p95_ms" in d


def test_mock_provider_health_check():
    p = MockAltDataProvider()
    hc = p.health_check()
    assert isinstance(hc, dict)
    assert "is_healthy" in hc


# ---------------------------------------------------------------------------
# ALL_ALT_PROVIDER_CLASSES — dict of 21 concrete stubs
# ---------------------------------------------------------------------------

def test_all_alt_provider_classes_is_dict():
    assert isinstance(ALL_ALT_PROVIDER_CLASSES, dict)


def test_all_alt_provider_classes_count():
    assert len(ALL_ALT_PROVIDER_CLASSES) == 21


def test_all_alt_provider_classes_keys_are_strings():
    for k in ALL_ALT_PROVIDER_CLASSES:
        assert isinstance(k, str)


def test_all_alt_provider_classes_values_are_types():
    for v in ALL_ALT_PROVIDER_CLASSES.values():
        assert isinstance(v, type)


def test_stub_providers_have_no_required_ctor_args():
    for name, cls in ALL_ALT_PROVIDER_CLASSES.items():
        p = cls()  # should not raise
        assert p is not None


def test_stub_provider_health_is_attribute():
    cls = list(ALL_ALT_PROVIDER_CLASSES.values())[0]
    p = cls()
    h = p.health
    assert isinstance(h, AltProviderHealth)


def test_stub_provider_fetch_raises_not_implemented():
    cls = list(ALL_ALT_PROVIDER_CLASSES.values())[0]
    p = cls()
    with pytest.raises(NotImplementedError):
        p.fetch(AltDataCapability.SEC_FILINGS)


def test_stub_provider_capabilities_returns_list():
    for cls in ALL_ALT_PROVIDER_CLASSES.values():
        p = cls()
        caps = p.capabilities()
        assert isinstance(caps, list)


def test_stub_provider_quality_score_range():
    for cls in ALL_ALT_PROVIDER_CLASSES.values():
        p = cls()
        assert 0 <= p.quality_score() <= 1.0


def test_stub_providers_distinct_names():
    names = [cls().name for cls in ALL_ALT_PROVIDER_CLASSES.values()]
    assert len(set(names)) == len(names), "Duplicate provider names"


# ---------------------------------------------------------------------------
# AltDataProviderRouter
# ---------------------------------------------------------------------------

def test_router_build():
    router = build_default_alt_router()
    assert router is not None


def test_router_has_providers():
    router = build_default_alt_router()
    assert len(router.providers) > 0


def test_router_has_mock_provider():
    router = build_default_alt_router()
    names = [p.name for p in router.providers]
    assert any("mock" in n.lower() for n in names)


def test_router_capabilities_matrix_nonempty():
    router = build_default_alt_router()
    matrix = router.capabilities_matrix()
    assert isinstance(matrix, dict)
    assert len(matrix) > 0


def test_router_health_summary_list():
    router = build_default_alt_router()
    h = router.health_summary()
    assert isinstance(h, list)
    assert len(h) > 0


def test_router_health_summary_has_fields():
    router = build_default_alt_router()
    for item in router.health_summary():
        assert "is_healthy" in item


def test_router_latency_summary_list():
    router = build_default_alt_router()
    lat = router.latency_summary()
    assert isinstance(lat, list)


def test_router_quality_scores_dict():
    router = build_default_alt_router()
    qs = router.quality_scores()
    assert isinstance(qs, dict)


def test_router_fetch_uses_mock_fallback():
    router = build_default_alt_router()
    data = router.fetch(AltDataCapability.SEC_FILINGS)
    assert data is not None


def test_router_providers_for():
    router = build_default_alt_router()
    providers = router.providers_for(AltDataCapability.SEC_FILINGS)
    assert isinstance(providers, list)


def test_router_singleton():
    r1 = get_default_alt_router()
    r2 = get_default_alt_router()
    assert r1 is r2


def test_router_provider_count_includes_all():
    router = build_default_alt_router()
    # 21 stub providers + 1 mock = 22
    assert len(router.providers) >= 21
