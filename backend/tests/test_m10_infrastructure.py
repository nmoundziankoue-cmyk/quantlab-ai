"""M10 infrastructure tests: cache/Redis (Phase 3), metrics (Phase 8), jobs (Phase 6), security (Phase 9)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app
from services.cache import cache, CacheBackend, _NAMESPACE, _BLACKLIST_PREFIX
from services.metrics import metrics, MetricsCollector, _normalize_path
from services.auth_service import validate_password_policy

client = TestClient(app)

_PWD = "TestPass1"


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_token(email: str) -> str:
    client.post("/auth/register", json={"email": email, "password": _PWD})
    r = client.post("/auth/login", json={"email": email, "password": _PWD})
    return r.json()["access_token"]


# ── Phase 3: Cache / Redis infrastructure ────────────────────────────────────

class TestCacheBackend:
    def test_in_memory_set_get_delete(self):
        b = CacheBackend()
        b.set("k1", {"a": 1}, ttl=60)
        assert b.get("k1") == {"a": 1}
        b.delete("k1")
        assert b.get("k1") is None

    def test_ttl_expiry(self):
        import time
        b = CacheBackend()
        b.set("expiring", "value", ttl=1)
        assert b.get("expiring") == "value"
        time.sleep(1.1)
        assert b.get("expiring") is None

    def test_clear_prefix(self):
        b = CacheBackend()
        b.set("prefix:a", 1, ttl=60)
        b.set("prefix:b", 2, ttl=60)
        b.set("other:c", 3, ttl=60)
        b.clear_prefix("prefix:")
        assert b.get("prefix:a") is None
        assert b.get("prefix:b") is None
        assert b.get("other:c") == 3

    def test_namespaced_set_get(self):
        b = CacheBackend()
        b.ns_set("testkey", "namespaced_value", ttl=60)
        assert b.ns_get("testkey") == "namespaced_value"
        # Raw key has namespace prefix
        assert b.get(f"{_NAMESPACE}testkey") == "namespaced_value"

    def test_ns_delete(self):
        b = CacheBackend()
        b.ns_set("delkey", "val", ttl=60)
        b.ns_delete("delkey")
        assert b.ns_get("delkey") is None

    def test_token_blacklist_add_check(self):
        b = CacheBackend()
        b.revoke_token("test-jti-123", ttl_seconds=300)
        assert b.is_token_revoked("test-jti-123") is True

    def test_token_not_in_blacklist(self):
        b = CacheBackend()
        assert b.is_token_revoked("nonexistent-jti") is False

    def test_backend_name_memory(self):
        b = CacheBackend()
        assert b.backend_name == "memory"

    def test_is_redis_connected_false_without_url(self):
        b = CacheBackend()
        assert b.is_redis_connected is False

    def test_redis_info_returns_not_connected(self):
        b = CacheBackend()
        info = b.redis_info()
        assert info is not None
        assert info["connected"] is False

    def test_publish_returns_zero_without_redis(self):
        b = CacheBackend()
        count = b.publish("test-channel", {"msg": "hello"})
        assert count == 0

    def test_get_pubsub_returns_none_without_redis(self):
        b = CacheBackend()
        assert b.get_pubsub() is None


class TestRedisHealthEndpoint:
    def test_redis_health_endpoint_reachable(self):
        r = client.get("/system/redis/health")
        assert r.status_code == 200
        body = r.json()
        assert "backend" in body
        assert "connected" in body

    def test_redis_health_shows_memory_fallback(self):
        r = client.get("/system/redis/health")
        body = r.json()
        # In test env Redis may not be running — either mode is valid
        assert body["backend"] in ("redis", "memory")


# ── Phase 8: Metrics ─────────────────────────────────────────────────────────

class TestMetricsCollector:
    def test_inc_request_increments_count(self):
        m = MetricsCollector()
        m.inc_request("GET", "/test/path", 200, 0.05)
        d = m.to_dict()
        assert d["total_requests"] == 1

    def test_inc_error_increments_error_count(self):
        m = MetricsCollector()
        m.inc_error("/auth/login", 401)
        assert m.to_dict()["total_errors"] == 1

    def test_set_ws_connections(self):
        m = MetricsCollector()
        m.set_ws_connections(5)
        assert m.to_dict()["ws_connections"] == 5

    def test_inc_ws_connections(self):
        m = MetricsCollector()
        m.inc_ws_connections(3)
        m.inc_ws_connections(-1)
        assert m.to_dict()["ws_connections"] == 2

    def test_ws_connections_never_negative(self):
        m = MetricsCollector()
        m.inc_ws_connections(-999)
        assert m.to_dict()["ws_connections"] == 0

    def test_cache_counters(self):
        m = MetricsCollector()
        m.inc_cache_hit()
        m.inc_cache_hit()
        m.inc_cache_miss()
        d = m.to_dict()
        assert d["cache_hits"] == 2
        assert d["cache_misses"] == 1

    def test_job_counters(self):
        m = MetricsCollector()
        m.inc_job_enqueued()
        m.inc_job_enqueued()
        m.inc_job_completed()
        m.inc_job_failed()
        d = m.to_dict()
        assert d["jobs_enqueued"] == 2
        assert d["jobs_completed"] == 1
        assert d["jobs_failed"] == 1

    def test_to_prometheus_contains_expected_metrics(self):
        m = MetricsCollector()
        m.inc_request("GET", "/health", 200, 0.01)
        m.inc_cache_hit()
        output = m.to_prometheus()
        assert "apexquant_uptime_seconds" in output
        assert "apexquant_cache_hits_total" in output
        assert "apexquant_http_requests_total" in output

    def test_prometheus_histogram_in_output(self):
        m = MetricsCollector()
        m.inc_request("POST", "/auth/login", 200, 0.15)
        output = m.to_prometheus()
        assert "apexquant_http_request_duration_seconds_bucket" in output
        assert "apexquant_http_request_duration_seconds_sum" in output

    def test_normalize_path_collapses_uuid(self):
        path = "/portfolios/123e4567-e89b-12d3-a456-426614174000/orders"
        assert _normalize_path(path) == "/portfolios/{id}/orders"

    def test_normalize_path_collapses_numeric_id(self):
        assert _normalize_path("/items/42/details") == "/items/{id}/details"

    def test_normalize_path_leaves_plain_path(self):
        assert _normalize_path("/auth/me") == "/auth/me"


class TestMetricsEndpoints:
    def test_prometheus_endpoint_returns_text(self):
        r = client.get("/system/metrics")
        assert r.status_code == 200
        assert "text/plain" in r.headers["content-type"]
        assert "apexquant_" in r.text

    def test_metrics_json_endpoint(self):
        r = client.get("/system/metrics/json")
        assert r.status_code == 200
        body = r.json()
        assert "total_requests" in body
        assert "ws_connections" in body


# ── Phase 6: Background jobs ─────────────────────────────────────────────────

class TestJobsEndpoints:
    def _auth_headers(self, email: str = "jobs_user@m10.com"):
        token = _get_token(email)
        return {"Authorization": f"Bearer {token}"}

    def test_enqueue_echo_job(self):
        r = client.post(
            "/jobs",
            json={"job_type": "echo", "payload": {"msg": "hello"}, "priority": 5},
            headers=self._auth_headers(),
        )
        assert r.status_code == 202
        body = r.json()
        assert "id" in body
        assert body["status"] in ("PENDING", "RUNNING", "COMPLETED")
        assert body["job_type"] == "echo"

    def test_get_job_by_id(self):
        r1 = client.post(
            "/jobs",
            json={"job_type": "echo", "payload": {}},
            headers=self._auth_headers("jobs_get@m10.com"),
        )
        job_id = r1.json()["id"]
        r2 = client.get(f"/jobs/{job_id}", headers=self._auth_headers("jobs_get@m10.com"))
        assert r2.status_code == 200
        assert r2.json()["id"] == job_id

    def test_get_nonexistent_job_returns_404(self):
        import uuid
        fake_id = str(uuid.uuid4())
        r = client.get(f"/jobs/{fake_id}", headers=self._auth_headers())
        assert r.status_code == 404

    def test_invalid_job_id_returns_400(self):
        r = client.get("/jobs/not-a-uuid", headers=self._auth_headers())
        assert r.status_code == 400

    def test_list_jobs_returns_array(self):
        r = client.get("/jobs", headers=self._auth_headers("jobs_list@m10.com"))
        assert r.status_code == 200
        body = r.json()
        assert "jobs" in body
        assert isinstance(body["jobs"], list)

    def test_idempotency_key_returns_same_job(self):
        headers = self._auth_headers("jobs_idem@m10.com")
        payload = {"job_type": "echo", "payload": {}, "idempotency_key": "unique-key-xyz-789"}
        r1 = client.post("/jobs", json=payload, headers=headers)
        r2 = client.post("/jobs", json=payload, headers=headers)
        assert r1.json()["id"] == r2.json()["id"]
        assert r2.json().get("idempotent") is True

    def test_enqueue_requires_auth(self):
        r = client.post("/jobs", json={"job_type": "echo", "payload": {}})
        assert r.status_code == 401

    def test_unknown_job_type_fails(self):
        import time
        headers = self._auth_headers("jobs_bad@m10.com")
        r = client.post(
            "/jobs",
            json={"job_type": "nonexistent_type", "payload": {}},
            headers=headers,
        )
        assert r.status_code == 202  # Accepted (async) — error shows in result
        job_id = r.json()["id"]
        # Poll briefly for completion
        for _ in range(10):
            time.sleep(0.3)
            r2 = client.get(f"/jobs/{job_id}", headers=headers)
            if r2.json()["status"] in ("FAILED", "COMPLETED"):
                break
        assert r2.json()["status"] == "FAILED"


# ── Phase 9: Security ─────────────────────────────────────────────────────────

class TestPasswordPolicy:
    def test_short_password_error(self):
        err = validate_password_policy("Ab1")
        assert err is not None
        assert "8" in err

    def test_no_uppercase_error(self):
        err = validate_password_policy("testpass1")
        assert err is not None
        assert "uppercase" in err.lower()

    def test_no_lowercase_error(self):
        err = validate_password_policy("TESTPASS1")
        assert err is not None
        assert "lowercase" in err.lower()

    def test_no_digit_error(self):
        err = validate_password_policy("TestPassword")
        assert err is not None
        assert "digit" in err.lower()

    def test_valid_password_returns_none(self):
        assert validate_password_policy("TestPass1") is None
        assert validate_password_policy("MySecure9Pass") is None
        assert validate_password_policy("A1bcdefgh") is None

    def test_exact_8_chars_valid(self):
        assert validate_password_policy("Abcdef1g") is None

    def test_7_chars_invalid(self):
        assert validate_password_policy("Abcde1g") is not None


class TestRequestSizeLimit:
    def test_normal_request_passes(self):
        r = client.get("/system/health")
        assert r.status_code == 200

    def test_oversized_request_rejected(self):
        large_body = "x" * (11 * 1024 * 1024)  # 11 MB
        r = client.post(
            "/auth/login",
            content=large_body,
            headers={"Content-Type": "application/json", "Content-Length": str(len(large_body))},
        )
        assert r.status_code == 413
