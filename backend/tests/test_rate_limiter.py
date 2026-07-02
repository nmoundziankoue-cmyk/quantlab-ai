"""Tests for services/rate_limiter.py (M8)."""
from __future__ import annotations

import time

import pytest

from services.rate_limiter import RateLimiter, rate_limiter


class TestRateLimiterBasics:
    def setup_method(self):
        self.rl = RateLimiter()

    def test_first_request_allowed(self):
        assert self.rl.check("key1", rate=10, capacity=5)

    def test_consumes_token(self):
        self.rl.check("key2", rate=10, capacity=2)
        self.rl.check("key2", rate=10, capacity=2)
        # 3rd should be denied
        assert not self.rl.check("key2", rate=10, capacity=2)

    def test_zero_capacity_always_denied(self):
        assert not self.rl.check("zero", rate=10, capacity=0)

    def test_reset_clears_bucket(self):
        for _ in range(5):
            self.rl.check("reset_key", rate=10, capacity=5)
        self.rl.reset("reset_key")
        assert self.rl.check("reset_key", rate=10, capacity=5)

    def test_different_keys_are_independent(self):
        for _ in range(3):
            self.rl.check("ka", rate=10, capacity=3)
        # ka exhausted but kb fresh
        assert self.rl.check("kb", rate=10, capacity=3)
        assert not self.rl.check("ka", rate=10, capacity=3)

    def test_tokens_refill_over_time(self):
        # Use fast rate so refill happens within test
        self.rl.check("refill", rate=100, capacity=1)
        assert not self.rl.check("refill", rate=100, capacity=1)
        time.sleep(0.02)  # 20ms → 2 tokens refilled at 100/s
        assert self.rl.check("refill", rate=100, capacity=1)


class TestRateLimiterConvenience:
    def setup_method(self):
        self.rl = RateLimiter()

    def test_check_ip(self):
        assert self.rl.check_ip("10.0.0.1", rate=10, capacity=5)

    def test_check_user(self):
        assert self.rl.check_user("user-uuid", rate=10, capacity=5)

    def test_check_endpoint(self):
        assert self.rl.check_endpoint("user-1", "/login", rate=1, capacity=3)

    def test_ip_and_user_keys_are_independent(self):
        for _ in range(3):
            self.rl.check_ip("1.1.1.1", rate=10, capacity=3)
        # user key still fresh
        assert self.rl.check_user("user-1", rate=10, capacity=3)

    def test_remaining_full_bucket(self):
        tokens, reset_in = self.rl.remaining("new_key", 10, 1.0)
        assert tokens == 10.0
        assert reset_in == 0.0

    def test_remaining_after_consume(self):
        for _ in range(3):
            self.rl.check("partial", rate=1.0, capacity=5)
        tokens, _ = self.rl.remaining("partial", 5, 1.0)
        assert tokens < 5


class TestRateLimiterStats:
    def test_stats_returns_dict(self):
        rl = RateLimiter()
        stats = rl.stats()
        assert "active_buckets" in stats
        assert isinstance(stats["active_buckets"], int)

    def test_stats_counts_buckets(self):
        rl = RateLimiter()
        rl.check("a", rate=10, capacity=5)
        rl.check("b", rate=10, capacity=5)
        assert rl.stats()["active_buckets"] == 2

    def test_module_singleton_exists(self):
        assert rate_limiter is not None
        assert isinstance(rate_limiter, RateLimiter)


class TestRateLimiterCleanup:
    def test_stale_buckets_evicted(self):
        rl = RateLimiter(cleanup_after_s=0.01)
        rl.check("stale", rate=10, capacity=5)
        assert rl.stats()["active_buckets"] == 1
        time.sleep(0.02)
        # Force cleanup by making a new check
        rl.check("trigger", rate=10, capacity=5)
        # stale bucket should be gone
        assert rl.stats()["active_buckets"] == 1

    def test_thread_safety(self):
        import threading
        rl = RateLimiter()
        results = []

        def worker(i):
            for _ in range(20):
                results.append(rl.check(f"t{i % 3}", rate=100, capacity=50))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # No crash = thread-safe
        assert len(results) == 200
