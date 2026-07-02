"""M9 Phase 2 — Streaming enhanced tests."""
import json
import time
import pytest
from fastapi.testclient import TestClient
from main import app

from services.streaming_enhanced import (
    AuthValidator,
    CHANNEL_REGISTRY,
    ChannelInfo,
    ConnectionRateLimiter,
    RateLimiter,
    SequenceCounter,
    StreamEvent,
    compress_payload,
    decompress_payload,
    get_enhanced_status,
    is_valid_channel,
    maybe_compress,
    publish_agent_progress,
    publish_alert,
    publish_execution_update,
    publish_market_data,
    publish_provider_health,
    publish_system_metrics,
    publish_task_event,
    resolve_channel,
    validate_token,
    COMPRESS_THRESHOLD_BYTES,
)

client = TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# StreamEvent
# ---------------------------------------------------------------------------

class TestStreamEvent:
    def test_default_fields_populated(self):
        e = StreamEvent(event_type="data", channel="orders", payload={"x": 1})
        assert e.event_id  # non-empty
        assert e.timestamp  # non-empty
        assert e.version == "2"
        assert e.seq == 0
        assert not e.compressed

    def test_to_dict_has_all_keys(self):
        e = StreamEvent(event_type="data", channel="orders", payload={})
        d = e.to_dict()
        for k in ("v", "event_type", "channel", "payload", "event_id", "seq", "timestamp", "compressed"):
            assert k in d

    def test_to_json_is_valid_json(self):
        e = StreamEvent(event_type="system", channel="system", payload={"msg": "ok"})
        parsed = json.loads(e.to_json())
        assert parsed["event_type"] == "system"

    def test_classmethod_data_assigns_seq(self):
        e = StreamEvent.data("orders", {"order_id": "123"})
        assert e.seq > 0
        assert e.event_type == "data"
        assert e.channel == "orders"

    def test_classmethod_data_increments_seq(self):
        e1 = StreamEvent.data("orders", {})
        e2 = StreamEvent.data("orders", {})
        assert e2.seq == e1.seq + 1

    def test_classmethod_data_seq_per_channel_independent(self):
        before_orders = StreamEvent.data("orders", {}).seq
        e_exec = StreamEvent.data("executions", {})
        after_orders = StreamEvent.data("orders", {}).seq
        # executions increment doesn't affect orders
        assert after_orders == before_orders + 1

    def test_classmethod_error(self):
        e = StreamEvent.error("orders", "something failed", "ERR_CODE")
        assert e.event_type == "error"
        assert e.payload["code"] == "ERR_CODE"
        assert "something failed" in e.payload["message"]

    def test_classmethod_system(self):
        e = StreamEvent.system("startup", {"extra": "data"})
        assert e.event_type == "system"
        assert e.channel == "system"
        assert e.payload["extra"] == "data"

    def test_unique_event_ids(self):
        ids = {StreamEvent.data("orders", {}).event_id for _ in range(50)}
        assert len(ids) == 50


# ---------------------------------------------------------------------------
# SequenceCounter
# ---------------------------------------------------------------------------

class TestSequenceCounter:
    def test_first_call_returns_one(self):
        sc = SequenceCounter()
        assert sc.next("ch") == 1

    def test_increments(self):
        sc = SequenceCounter()
        for i in range(1, 6):
            assert sc.next("ch") == i

    def test_channels_independent(self):
        sc = SequenceCounter()
        sc.next("a")
        sc.next("a")
        assert sc.next("b") == 1

    def test_reset_restarts_from_one(self):
        sc = SequenceCounter()
        sc.next("r")
        sc.next("r")
        sc.reset("r")
        assert sc.next("r") == 1

    def test_current_before_any_call(self):
        sc = SequenceCounter()
        assert sc.current("never_called") == 0

    def test_thread_safety(self):
        import threading
        sc = SequenceCounter()
        results = []
        lock = threading.Lock()

        def worker():
            for _ in range(100):
                val = sc.next("concurrent")
                with lock:
                    results.append(val)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(results) == 500
        assert len(set(results)) == 500  # all unique


# ---------------------------------------------------------------------------
# RateLimiter
# ---------------------------------------------------------------------------

class TestRateLimiter:
    def test_allows_up_to_capacity(self):
        rl = RateLimiter(capacity=5.0, refill_rate=0.0)
        for _ in range(5):
            assert rl.allow()

    def test_blocks_over_capacity(self):
        rl = RateLimiter(capacity=3.0, refill_rate=0.0)
        for _ in range(3):
            rl.allow()
        assert not rl.allow()

    def test_refill_over_time(self):
        rl = RateLimiter(capacity=2.0, refill_rate=1000.0)  # fast refill
        rl.allow()
        rl.allow()
        assert not rl.allow()
        time.sleep(0.01)  # 10ms → 10 tokens added
        assert rl.allow()

    def test_tokens_available_reflects_state(self):
        rl = RateLimiter(capacity=10.0, refill_rate=0.0)
        rl.allow()
        rl.allow()
        assert rl.tokens_available == pytest.approx(8.0, abs=0.1)

    def test_cost_parameter(self):
        rl = RateLimiter(capacity=10.0, refill_rate=0.0)
        assert rl.allow(cost=5.0)
        assert rl.allow(cost=5.0)
        assert not rl.allow(cost=1.0)

    def test_partial_cost_rejected(self):
        rl = RateLimiter(capacity=3.0, refill_rate=0.0)
        assert rl.allow(cost=3.0)
        assert not rl.allow(cost=0.1)


# ---------------------------------------------------------------------------
# ConnectionRateLimiter
# ---------------------------------------------------------------------------

class TestConnectionRateLimiter:
    def test_creates_limiter_per_conn(self):
        crl = ConnectionRateLimiter(capacity=5.0, refill_rate=0.0)
        crl.allow("conn_a")
        crl.allow("conn_b")
        assert crl.get("conn_a") is not crl.get("conn_b")

    def test_remove_cleans_up(self):
        crl = ConnectionRateLimiter()
        crl.allow("temp_conn")
        crl.remove("temp_conn")
        assert "temp_conn" not in crl._limiters

    def test_different_conns_independent(self):
        crl = ConnectionRateLimiter(capacity=1.0, refill_rate=0.0)
        crl.allow("c1")  # exhaust c1
        assert not crl.allow("c1")  # blocked
        assert crl.allow("c2")     # c2 unaffected


# ---------------------------------------------------------------------------
# ChannelRegistry
# ---------------------------------------------------------------------------

class TestChannelRegistry:
    def test_required_channels_present(self):
        for ch in ("orders", "executions", "positions", "alerts",
                   "market_data", "agent_progress", "task_queue",
                   "system_metrics", "provider_health", "execution_updates"):
            assert ch in CHANNEL_REGISTRY, f"Missing channel: {ch}"

    def test_channel_info_fields(self):
        for key, info in CHANNEL_REGISTRY.items():
            assert info.name
            assert info.pattern
            assert info.description
            assert info.category

    def test_resolve_exact_match(self):
        assert resolve_channel("orders") == "orders"
        assert resolve_channel("alerts") == "alerts"

    def test_resolve_parameterized(self):
        assert resolve_channel("market_data:AAPL") == "market_data"
        assert resolve_channel("prices:MSFT") == "prices"
        assert resolve_channel("agent_progress:abc-123") == "agent_progress"

    def test_resolve_unknown_returns_none(self):
        assert resolve_channel("totally_unknown_channel_xyz") is None

    def test_is_valid_channel_known(self):
        assert is_valid_channel("orders")
        assert is_valid_channel("market_data:NVDA")
        assert is_valid_channel("system_metrics")

    def test_is_valid_channel_unknown(self):
        assert not is_valid_channel("not_a_real_channel_xyz")


# ---------------------------------------------------------------------------
# AuthValidator
# ---------------------------------------------------------------------------

class TestAuthValidator:
    def setup_method(self):
        self.av = AuthValidator(secret="test-secret")

    def test_none_token_is_valid_anonymous(self):
        ok, uid = self.av.validate(None)
        assert ok
        assert uid is None

    def test_empty_token_treated_as_anonymous(self):
        ok, uid = self.av.validate("")
        # empty string is falsy → treated as no token → anonymous
        assert ok
        assert uid is None

    def test_short_token_invalid(self):
        ok, uid = self.av.validate("short")
        assert not ok

    def test_valid_token_returns_user_id(self):
        ok, uid = self.av.validate("a-valid-token-long-enough")
        assert ok
        assert uid is not None
        assert uid.startswith("user_")

    def test_same_token_deterministic_user_id(self):
        _, u1 = self.av.validate("fixed-token-abc")
        _, u2 = self.av.validate("fixed-token-abc")
        assert u1 == u2

    def test_different_tokens_different_users(self):
        _, u1 = self.av.validate("token-aaa-long-enough")
        _, u2 = self.av.validate("token-bbb-long-enough")
        assert u1 != u2

    def test_channel_access_public_no_auth(self):
        assert self.av.validate_channel_access("orders", None)

    def test_validate_token_module_function(self):
        ok, uid = validate_token("a-token-that-is-long-enough")
        assert ok


# ---------------------------------------------------------------------------
# Compression
# ---------------------------------------------------------------------------

class TestCompression:
    def test_compress_decompress_roundtrip(self):
        original = '{"data": "hello world"}'
        assert decompress_payload(compress_payload(original)) == original

    def test_compress_reduces_size_for_large_data(self):
        large = json.dumps({"x": "A" * 5000})
        compressed = compress_payload(large)
        assert len(compressed) < len(large)

    def test_maybe_compress_small_payload_not_compressed(self):
        e = StreamEvent(event_type="data", channel="orders", payload={"x": 1})
        result = maybe_compress(e)
        parsed = json.loads(result)
        assert not parsed["compressed"]

    def test_maybe_compress_large_payload_compressed(self):
        big_payload = {"data": "X" * (COMPRESS_THRESHOLD_BYTES * 2)}
        e = StreamEvent(event_type="data", channel="system_metrics", payload=big_payload)
        result = maybe_compress(e)
        parsed = json.loads(result)
        assert parsed["compressed"]
        assert "_compressed" in parsed["payload"]

    def test_compressed_payload_decompresses_back(self):
        original_payload = {"items": list(range(500))}
        e = StreamEvent(event_type="data", channel="system_metrics", payload=original_payload)
        result = maybe_compress(e)
        parsed = json.loads(result)
        if parsed["compressed"]:
            recovered_str = decompress_payload(parsed["payload"]["_compressed"])
            recovered = json.loads(recovered_str)
            assert recovered == original_payload


# ---------------------------------------------------------------------------
# Publisher helpers (smoke tests — no live WS)
# ---------------------------------------------------------------------------

class TestPublishHelpers:
    def test_publish_market_data_no_crash(self):
        publish_market_data("AAPL", {"price": 150.0, "volume": 1000})

    def test_publish_agent_progress_no_crash(self):
        publish_agent_progress("session-abc", "macro_economist", {"step": 1, "total": 5})

    def test_publish_alert_no_crash(self):
        publish_alert({"ticker": "AAPL", "message": "RSI overbought", "severity": "medium"})

    def test_publish_task_event_no_crash(self):
        publish_task_event("task-xyz", "running", {"progress_pct": 50})

    def test_publish_system_metrics_no_crash(self):
        publish_system_metrics({"cpu_pct": 42.0, "mem_pct": 60.0, "latency_ms": 12})

    def test_publish_provider_health_no_crash(self):
        publish_provider_health("yahoo", {"health_score": 0.95, "avg_latency_ms": 45})

    def test_publish_execution_update_no_crash(self):
        publish_execution_update({"order_id": "ord-1", "status": "filled", "filled_qty": 100})


# ---------------------------------------------------------------------------
# get_enhanced_status
# ---------------------------------------------------------------------------

class TestEnhancedStatus:
    def test_returns_dict(self):
        s = get_enhanced_status()
        assert isinstance(s, dict)

    def test_has_features(self):
        s = get_enhanced_status()
        assert "features" in s
        assert s["features"]["authentication"] is True
        assert s["features"]["rate_limiting"] is True
        assert s["features"]["compression"] is True
        assert s["features"]["sequence_numbers"] is True

    def test_channel_count_correct(self):
        s = get_enhanced_status()
        assert s["channel_count"] == len(CHANNEL_REGISTRY)

    def test_envelope_version_is_2(self):
        assert get_enhanced_status()["envelope_version"] == "2"


# ---------------------------------------------------------------------------
# HTTP endpoints via TestClient
# ---------------------------------------------------------------------------

class TestStreamingV2HTTP:
    def test_v2_status_200(self):
        r = client.get("/ws/v2/status")
        assert r.status_code == 200
        data = r.json()
        assert "active_connections" in data
        assert "features" in data

    def test_v2_status_has_channel_list(self):
        r = client.get("/ws/v2/status")
        data = r.json()
        assert "channels" in data
        assert len(data["channels"]) == len(CHANNEL_REGISTRY)

    def test_v2_channels_200(self):
        r = client.get("/ws/v2/channels")
        assert r.status_code == 200
        data = r.json()
        assert "channels" in data
        assert data["total"] == len(CHANNEL_REGISTRY)

    def test_v2_channels_has_categories(self):
        r = client.get("/ws/v2/channels")
        data = r.json()
        assert "categories" in data
        assert len(data["categories"]) > 0

    def test_v2_channels_all_have_keys(self):
        r = client.get("/ws/v2/channels")
        for ch in r.json()["channels"]:
            assert "key" in ch
            assert "pattern" in ch
            assert "description" in ch
            assert "category" in ch

    def test_existing_ws_status_still_works(self):
        r = client.get("/ws/status")
        assert r.status_code == 200
        assert "active_connections" in r.json()

    def test_existing_ws_status_available_channels(self):
        r = client.get("/ws/status")
        data = r.json()
        assert "available_channels" in data
