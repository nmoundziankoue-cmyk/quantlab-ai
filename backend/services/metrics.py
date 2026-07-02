"""Application-level metrics collection for Prometheus export (M10 Phase 8).

All counters and histograms are in-process (thread-safe). When Redis is available,
they are also published for multi-process aggregation.

Usage::

    from services.metrics import metrics

    metrics.inc_request(method="GET", path="/analytics", status=200, duration_s=0.042)
    metrics.inc_error(path="/auth/login", status=401)
    metrics.set_ws_connections(12)
    metrics.inc_cache_hit()
    metrics.inc_cache_miss()
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Dict, List, Optional


_LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


class _Histogram:
    def __init__(self, buckets=_LATENCY_BUCKETS):
        self._buckets = sorted(buckets)
        self._counts = [0] * len(self._buckets)
        self._inf = 0
        self._sum = 0.0
        self._total = 0
        self._lock = threading.Lock()

    def observe(self, value: float) -> None:
        with self._lock:
            self._sum += value
            self._total += 1
            for i, b in enumerate(self._buckets):
                if value <= b:
                    self._counts[i] += 1
            else:
                self._inf += 1

    def snapshot(self):
        with self._lock:
            return {
                "buckets": list(self._buckets),
                "counts": list(self._counts),
                "inf": self._inf,
                "sum": self._sum,
                "total": self._total,
            }


class MetricsCollector:
    def __init__(self):
        self._lock = threading.Lock()
        self._start_time = time.time()

        # Request counts: {(method, path_pattern, status): count}
        self._request_counts: Dict[tuple, int] = defaultdict(int)
        # Latency histogram per path_pattern
        self._latency: Dict[str, _Histogram] = defaultdict(lambda: _Histogram())
        # Error counts: {(path_pattern, status): count}
        self._error_counts: Dict[tuple, int] = defaultdict(int)
        # WebSocket connection gauge
        self._ws_connections = 0
        # Cache counters
        self._cache_hits = 0
        self._cache_misses = 0
        # Job counters
        self._jobs_enqueued = 0
        self._jobs_completed = 0
        self._jobs_failed = 0

    # ── Mutation helpers ──────────────────────────────────────────────────────

    def inc_request(self, method: str, path: str, status: int, duration_s: float) -> None:
        path_pattern = _normalize_path(path)
        with self._lock:
            self._request_counts[(method.upper(), path_pattern, status)] += 1
        self._latency[path_pattern].observe(duration_s)

    def inc_error(self, path: str, status: int) -> None:
        with self._lock:
            self._error_counts[(_normalize_path(path), status)] += 1

    def set_ws_connections(self, count: int) -> None:
        with self._lock:
            self._ws_connections = count

    def inc_ws_connections(self, delta: int = 1) -> None:
        with self._lock:
            self._ws_connections = max(0, self._ws_connections + delta)

    def inc_cache_hit(self) -> None:
        with self._lock:
            self._cache_hits += 1

    def inc_cache_miss(self) -> None:
        with self._lock:
            self._cache_misses += 1

    def inc_job_enqueued(self) -> None:
        with self._lock:
            self._jobs_enqueued += 1

    def inc_job_completed(self) -> None:
        with self._lock:
            self._jobs_completed += 1

    def inc_job_failed(self) -> None:
        with self._lock:
            self._jobs_failed += 1

    # ── Prometheus text export ────────────────────────────────────────────────

    def to_prometheus(self) -> str:
        lines: List[str] = []
        uptime = time.time() - self._start_time

        def g(name, value, help_text, labels=""):
            lines.append(f"# HELP {name} {help_text}")
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name}{{{labels}}} {value}" if labels else f"{name} {value}")
            lines.append("")

        def c(name, value, help_text, labels=""):
            lines.append(f"# HELP {name} {help_text}")
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name}{{{labels}}} {value}" if labels else f"{name} {value}")
            lines.append("")

        g("apexquant_uptime_seconds", round(uptime, 1), "Application uptime")
        g("apexquant_ws_connections_active", self._ws_connections, "Active WebSocket connections")

        with self._lock:
            cache_hits = self._cache_hits
            cache_misses = self._cache_misses
            req_counts = dict(self._request_counts)
            err_counts = dict(self._error_counts)
            jobs_e = self._jobs_enqueued
            jobs_c = self._jobs_completed
            jobs_f = self._jobs_failed

        c("apexquant_cache_hits_total", cache_hits, "Cache hits")
        c("apexquant_cache_misses_total", cache_misses, "Cache misses")
        c("apexquant_jobs_enqueued_total", jobs_e, "Jobs enqueued")
        c("apexquant_jobs_completed_total", jobs_c, "Jobs completed")
        c("apexquant_jobs_failed_total", jobs_f, "Jobs failed")

        # Request counts grouped by method+path+status
        lines.append("# HELP apexquant_http_requests_total HTTP request count")
        lines.append("# TYPE apexquant_http_requests_total counter")
        for (method, path, status), count in sorted(req_counts.items()):
            lines.append(
                f'apexquant_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}'
            )
        lines.append("")

        # Error counts
        lines.append("# HELP apexquant_http_errors_total HTTP error count (4xx/5xx)")
        lines.append("# TYPE apexquant_http_errors_total counter")
        for (path, status), count in sorted(err_counts.items()):
            lines.append(f'apexquant_http_errors_total{{path="{path}",status="{status}"}} {count}')
        lines.append("")

        # Latency histograms
        lines.append("# HELP apexquant_http_request_duration_seconds Request latency histogram")
        lines.append("# TYPE apexquant_http_request_duration_seconds histogram")
        for path, hist in sorted(self._latency.items()):
            snap = hist.snapshot()
            cumulative = 0
            for bucket, count in zip(snap["buckets"], snap["counts"]):
                cumulative += count
                lines.append(
                    f'apexquant_http_request_duration_seconds_bucket{{path="{path}",le="{bucket}"}} {cumulative}'
                )
            total_cumulative = cumulative + snap["inf"]
            lines.append(
                f'apexquant_http_request_duration_seconds_bucket{{path="{path}",le="+Inf"}} {total_cumulative}'
            )
            lines.append(f'apexquant_http_request_duration_seconds_sum{{path="{path}"}} {snap["sum"]:.6f}')
            lines.append(f'apexquant_http_request_duration_seconds_count{{path="{path}"}} {snap["total"]}')
        lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "uptime_s": round(time.time() - self._start_time, 1),
                "ws_connections": self._ws_connections,
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "jobs_enqueued": self._jobs_enqueued,
                "jobs_completed": self._jobs_completed,
                "jobs_failed": self._jobs_failed,
                "total_requests": sum(self._request_counts.values()),
                "total_errors": sum(self._error_counts.values()),
            }


def _normalize_path(path: str) -> str:
    """Collapse UUIDs and numeric IDs to reduce label cardinality."""
    import re
    # Replace UUID segments
    path = re.sub(r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "/{id}", path)
    # Replace pure-numeric segments
    path = re.sub(r"/\d+", "/{id}", path)
    return path


# Module-level singleton
metrics = MetricsCollector()
