"""M20 — Correlation and Covariance Engine.

Computes pairwise Pearson correlations, covariance matrices, rolling
correlations over time windows, and threshold-based asset clusters —
all in pure Python with no scientific library dependencies.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from services.m19_factor_models import _pearson


# ---------------------------------------------------------------------------
# Domain dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CorrelationMatrix:
    """Pairwise Pearson correlation matrix for a set of tickers.

    Attributes:
        matrix_id: Unique UUID for this computation.
        tickers: Ordered list of tickers.
        values: 2-D list (N×N) of correlation coefficients.
        num_observations: Number of common date observations used.
        min_correlation: Minimum off-diagonal value.
        max_correlation: Maximum off-diagonal value.
        avg_correlation: Mean absolute off-diagonal correlation.
    """

    matrix_id: str
    tickers: List[str]
    values: List[List[float]]
    num_observations: int
    min_correlation: float
    max_correlation: float
    avg_correlation: float

    def get(self, ticker_a: str, ticker_b: str) -> Optional[float]:
        """Return correlation between two tickers.

        Args:
            ticker_a: First ticker.
            ticker_b: Second ticker.

        Returns:
            Pearson correlation, or None if either ticker is absent.
        """
        if ticker_a not in self.tickers or ticker_b not in self.tickers:
            return None
        i = self.tickers.index(ticker_a)
        j = self.tickers.index(ticker_b)
        return self.values[i][j]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to plain dict."""
        return {
            "matrix_id": self.matrix_id,
            "tickers": self.tickers,
            "values": self.values,
            "num_observations": self.num_observations,
            "min_correlation": self.min_correlation,
            "max_correlation": self.max_correlation,
            "avg_correlation": self.avg_correlation,
        }


@dataclass
class CovarianceMatrix:
    """Sample covariance matrix for a set of tickers.

    Attributes:
        matrix_id: Unique UUID.
        tickers: Ordered list of tickers.
        values: 2-D list (N×N) of covariance values.
        num_observations: Common observation count.
        annualized: Whether the matrix is annualised (×252).
    """

    matrix_id: str
    tickers: List[str]
    values: List[List[float]]
    num_observations: int
    annualized: bool

    def get(self, ticker_a: str, ticker_b: str) -> Optional[float]:
        """Return covariance between two tickers.

        Args:
            ticker_a: First ticker.
            ticker_b: Second ticker.

        Returns:
            Covariance value, or None if either ticker is absent.
        """
        if ticker_a not in self.tickers or ticker_b not in self.tickers:
            return None
        i = self.tickers.index(ticker_a)
        j = self.tickers.index(ticker_b)
        return self.values[i][j]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to plain dict."""
        return {
            "matrix_id": self.matrix_id,
            "tickers": self.tickers,
            "values": self.values,
            "num_observations": self.num_observations,
            "annualized": self.annualized,
        }


@dataclass
class RollingCorrelation:
    """Time series of rolling-window correlation between two tickers.

    Attributes:
        ticker_a: First ticker.
        ticker_b: Second ticker.
        window: Rolling window in bars.
        dates: Ordered dates (one per window endpoint).
        correlations: Correlation value at each date.
        avg_correlation: Mean correlation over the series.
        std_correlation: Standard deviation of the series.
    """

    ticker_a: str
    ticker_b: str
    window: int
    dates: List[str]
    correlations: List[float]
    avg_correlation: float
    std_correlation: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to plain dict."""
        return {
            "ticker_a": self.ticker_a,
            "ticker_b": self.ticker_b,
            "window": self.window,
            "dates": self.dates,
            "correlations": self.correlations,
            "avg_correlation": self.avg_correlation,
            "std_correlation": self.std_correlation,
        }


@dataclass
class CorrelationCluster:
    """Group of assets whose pairwise correlations exceed a threshold.

    Attributes:
        cluster_id: Integer label (0-indexed).
        tickers: Members of the cluster.
        avg_intra_correlation: Mean correlation within the cluster.
        representative: Ticker with highest average intra-cluster correlation.
    """

    cluster_id: int
    tickers: List[str]
    avg_intra_correlation: float
    representative: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to plain dict."""
        return {
            "cluster_id": self.cluster_id,
            "tickers": self.tickers,
            "avg_intra_correlation": self.avg_intra_correlation,
            "representative": self.representative,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _common_returns(
    returns_a: Dict[str, float],
    returns_b: Dict[str, float],
) -> Tuple[List[float], List[float], List[str]]:
    """Extract aligned return lists for the common dates of two tickers.

    Args:
        returns_a: Date → return mapping for ticker A.
        returns_b: Date → return mapping for ticker B.

    Returns:
        Tuple (series_a, series_b, common_dates) aligned and sorted.
    """
    common_dates = sorted(set(returns_a) & set(returns_b))
    sa = [returns_a[d] for d in common_dates]
    sb = [returns_b[d] for d in common_dates]
    return sa, sb, common_dates


def _sample_covariance(x: List[float], y: List[float]) -> float:
    """Compute sample covariance between two equal-length series.

    Args:
        x: First return series.
        y: Second return series.

    Returns:
        Sample covariance (divided by N-1).  Zero if fewer than 2 obs.
    """
    n = len(x)
    if n < 2:
        return 0.0
    mx = sum(x) / n
    my = sum(y) / n
    return sum((x[i] - mx) * (y[i] - my) for i in range(n)) / (n - 1)


def _std_stats(series: List[float]) -> Tuple[float, float]:
    """Compute mean and standard deviation of a series.

    Args:
        series: List of floats.

    Returns:
        Tuple (mean, std_dev).
    """
    if not series:
        return 0.0, 0.0
    mean = sum(series) / len(series)
    var = sum((v - mean) ** 2 for v in series) / len(series)
    return mean, math.sqrt(var)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class CorrelationCovarianceEngine:
    """Computes correlation and covariance matrices, rolling correlation, and
    threshold-based asset clusters from stored return series.

    Return data is stored per ticker as a dict of ISO date → fractional return.
    All pairwise computations use common (intersecting) dates.
    """

    def __init__(self) -> None:
        """Initialise with empty return storage."""
        self._returns: Dict[str, Dict[str, float]] = {}
        self._corr_cache: Dict[str, CorrelationMatrix] = {}
        self._cov_cache: Dict[str, CovarianceMatrix] = {}

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def add_returns(self, ticker: str, returns: Dict[str, float]) -> None:
        """Store or replace the return series for a ticker.

        Args:
            ticker: Instrument symbol.
            returns: Mapping of ISO date string → fractional daily return.
        """
        self._returns[ticker] = dict(returns)

    def add_returns_batch(self, returns_map: Dict[str, Dict[str, float]]) -> None:
        """Store return series for multiple tickers at once.

        Args:
            returns_map: Ticker → date → return mapping.
        """
        for ticker, rets in returns_map.items():
            self._returns[ticker] = dict(rets)

    # ------------------------------------------------------------------
    # Correlation matrix
    # ------------------------------------------------------------------

    def compute_correlation_matrix(self, tickers: List[str]) -> CorrelationMatrix:
        """Compute N×N Pearson correlation matrix for the given tickers.

        Args:
            tickers: Ordered list of tickers (must be stored via add_returns).

        Returns:
            CorrelationMatrix with values and summary statistics.

        Raises:
            ValueError: If any ticker has no stored returns.
        """
        for t in tickers:
            if t not in self._returns:
                raise ValueError(f"No returns stored for ticker '{t}'")

        n = len(tickers)
        values: List[List[float]] = [[0.0] * n for _ in range(n)]
        min_obs = 10 ** 9

        for i in range(n):
            values[i][i] = 1.0
            for j in range(i + 1, n):
                sa, sb, common = _common_returns(self._returns[tickers[i]], self._returns[tickers[j]])
                corr = _pearson(sa, sb)
                values[i][j] = round(corr, 6)
                values[j][i] = round(corr, 6)
                if len(common) < min_obs:
                    min_obs = len(common)

        off_diag = [values[i][j] for i in range(n) for j in range(n) if i != j]
        matrix = CorrelationMatrix(
            matrix_id=str(uuid.uuid4()),
            tickers=list(tickers),
            values=values,
            num_observations=min_obs if min_obs < 10 ** 9 else 0,
            min_correlation=min(off_diag) if off_diag else 0.0,
            max_correlation=max(off_diag) if off_diag else 0.0,
            avg_correlation=sum(abs(v) for v in off_diag) / len(off_diag) if off_diag else 0.0,
        )
        self._corr_cache[matrix.matrix_id] = matrix
        return matrix

    def get_correlation_matrix(self, matrix_id: str) -> Optional[CorrelationMatrix]:
        """Retrieve a previously computed correlation matrix by ID.

        Args:
            matrix_id: UUID of the matrix to retrieve.

        Returns:
            CorrelationMatrix, or None if not found.
        """
        return self._corr_cache.get(matrix_id)

    # ------------------------------------------------------------------
    # Covariance matrix
    # ------------------------------------------------------------------

    def compute_covariance_matrix(
        self, tickers: List[str], annualize: bool = True
    ) -> CovarianceMatrix:
        """Compute N×N sample covariance matrix.

        Args:
            tickers: Ordered list of tickers.
            annualize: If True, multiply by 252 to annualise daily covariances.

        Returns:
            CovarianceMatrix with values.

        Raises:
            ValueError: If any ticker has no stored returns.
        """
        for t in tickers:
            if t not in self._returns:
                raise ValueError(f"No returns stored for ticker '{t}'")

        n = len(tickers)
        values: List[List[float]] = [[0.0] * n for _ in range(n)]
        scale = 252.0 if annualize else 1.0

        for i in range(n):
            for j in range(i, n):
                sa, sb, _ = _common_returns(self._returns[tickers[i]], self._returns[tickers[j]])
                cov = _sample_covariance(sa, sb) * scale
                values[i][j] = round(cov, 8)
                values[j][i] = round(cov, 8)

        obs = min(
            len(self._returns[t]) for t in tickers
        ) if tickers else 0

        matrix = CovarianceMatrix(
            matrix_id=str(uuid.uuid4()),
            tickers=list(tickers),
            values=values,
            num_observations=obs,
            annualized=annualize,
        )
        self._cov_cache[matrix.matrix_id] = matrix
        return matrix

    def get_covariance_matrix(self, matrix_id: str) -> Optional[CovarianceMatrix]:
        """Retrieve a previously computed covariance matrix by ID.

        Args:
            matrix_id: UUID of the matrix.

        Returns:
            CovarianceMatrix, or None if not found.
        """
        return self._cov_cache.get(matrix_id)

    # ------------------------------------------------------------------
    # Rolling correlation
    # ------------------------------------------------------------------

    def compute_rolling_correlation(
        self, ticker_a: str, ticker_b: str, window: int = 60
    ) -> RollingCorrelation:
        """Compute rolling Pearson correlation between two tickers.

        Args:
            ticker_a: First ticker.
            ticker_b: Second ticker.
            window: Rolling window size in bars.

        Returns:
            RollingCorrelation with per-date correlation values.

        Raises:
            ValueError: If either ticker is not stored.
        """
        for t in (ticker_a, ticker_b):
            if t not in self._returns:
                raise ValueError(f"No returns stored for ticker '{t}'")

        _, _, all_dates = _common_returns(self._returns[ticker_a], self._returns[ticker_b])
        ra = self._returns[ticker_a]
        rb = self._returns[ticker_b]

        roll_dates: List[str] = []
        roll_corrs: List[float] = []

        for end in range(window - 1, len(all_dates)):
            window_dates = all_dates[end - window + 1: end + 1]
            xa = [ra[d] for d in window_dates]
            xb = [rb[d] for d in window_dates]
            corr = _pearson(xa, xb)
            roll_dates.append(all_dates[end])
            roll_corrs.append(round(corr, 6))

        avg, std = _std_stats(roll_corrs)
        return RollingCorrelation(
            ticker_a=ticker_a,
            ticker_b=ticker_b,
            window=window,
            dates=roll_dates,
            correlations=roll_corrs,
            avg_correlation=round(avg, 6),
            std_correlation=round(std, 6),
        )

    # ------------------------------------------------------------------
    # Cluster detection
    # ------------------------------------------------------------------

    def detect_clusters(
        self, tickers: List[str], threshold: float = 0.70
    ) -> List[CorrelationCluster]:
        """Group assets into clusters where |correlation| ≥ threshold.

        Uses greedy single-linkage: a ticker joins an existing cluster if its
        correlation with any current member exceeds the threshold.  Otherwise
        it starts a new cluster.

        Args:
            tickers: Tickers to cluster (must be stored).
            threshold: Absolute correlation threshold for cluster membership.

        Returns:
            List of CorrelationCluster objects.
        """
        if not tickers:
            return []
        corr_mat = self.compute_correlation_matrix(tickers)

        clusters: List[List[str]] = []
        assigned: set = set()

        for ticker in tickers:
            if ticker in assigned:
                continue
            idx_t = tickers.index(ticker)
            placed = False
            for cluster in clusters:
                for member in cluster:
                    idx_m = tickers.index(member)
                    if abs(corr_mat.values[idx_t][idx_m]) >= threshold:
                        cluster.append(ticker)
                        assigned.add(ticker)
                        placed = True
                        break
                if placed:
                    break
            if not placed:
                clusters.append([ticker])
                assigned.add(ticker)

        result: List[CorrelationCluster] = []
        for cid, members in enumerate(clusters):
            if len(members) == 1:
                avg_intra = 1.0
                rep = members[0]
            else:
                pairs = [
                    abs(corr_mat.values[tickers.index(a)][tickers.index(b)])
                    for i, a in enumerate(members)
                    for b in members[i + 1:]
                ]
                avg_intra = sum(pairs) / len(pairs) if pairs else 1.0
                rep = max(
                    members,
                    key=lambda t: sum(
                        abs(corr_mat.values[tickers.index(t)][tickers.index(m)])
                        for m in members if m != t
                    ) / max(len(members) - 1, 1),
                )
            result.append(CorrelationCluster(
                cluster_id=cid,
                tickers=list(members),
                avg_intra_correlation=round(avg_intra, 4),
                representative=rep,
            ))
        return result

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def list_tickers(self) -> List[str]:
        """Return all tickers with stored return data.

        Returns:
            Sorted list of ticker symbols.
        """
        return sorted(self._returns.keys())

    def pairwise_correlation(self, ticker_a: str, ticker_b: str) -> float:
        """Compute scalar Pearson correlation between two tickers.

        Args:
            ticker_a: First ticker.
            ticker_b: Second ticker.

        Returns:
            Pearson correlation coefficient.

        Raises:
            ValueError: If either ticker is not stored.
        """
        for t in (ticker_a, ticker_b):
            if t not in self._returns:
                raise ValueError(f"No returns stored for ticker '{t}'")
        sa, sb, _ = _common_returns(self._returns[ticker_a], self._returns[ticker_b])
        return _pearson(sa, sb)

    def most_correlated_pair(self, tickers: List[str]) -> Tuple[str, str, float]:
        """Find the ticker pair with the highest absolute correlation.

        Args:
            tickers: Tickers to search (must be stored).

        Returns:
            Tuple (ticker_a, ticker_b, correlation).
        """
        best_pair = ("", "", 0.0)
        for i, ta in enumerate(tickers):
            for tb in tickers[i + 1:]:
                try:
                    corr = abs(self.pairwise_correlation(ta, tb))
                except ValueError:
                    continue
                if corr > abs(best_pair[2]):
                    best_pair = (ta, tb, self.pairwise_correlation(ta, tb))
        return best_pair

    def least_correlated_pair(self, tickers: List[str]) -> Tuple[str, str, float]:
        """Find the ticker pair with the lowest absolute correlation.

        Args:
            tickers: Tickers to search (must be stored).

        Returns:
            Tuple (ticker_a, ticker_b, correlation).
        """
        best_pair = ("", "", 1.0)
        for i, ta in enumerate(tickers):
            for tb in tickers[i + 1:]:
                try:
                    corr = abs(self.pairwise_correlation(ta, tb))
                except ValueError:
                    continue
                if corr < abs(best_pair[2]):
                    best_pair = (ta, tb, self.pairwise_correlation(ta, tb))
        return best_pair

    def reset(self) -> None:
        """Clear all stored returns and cached matrices."""
        self._returns.clear()
        self._corr_cache.clear()
        self._cov_cache.clear()
