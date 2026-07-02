"""Multi-factor regression, exposure analysis, and performance attribution engine."""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class FactorType(str, Enum):
    """Canonical factor names for multi-factor models."""

    MARKET = "MARKET"
    SIZE = "SIZE"
    VALUE = "VALUE"
    MOMENTUM = "MOMENTUM"
    QUALITY = "QUALITY"
    LOW_VOL = "LOW_VOL"
    CUSTOM = "CUSTOM"


# ---------------------------------------------------------------------------
# Pure-Python linear-algebra helpers (no numpy / scipy)
# ---------------------------------------------------------------------------

def _mat_T(A: List[List[float]]) -> List[List[float]]:
    """Return the transpose of matrix A."""
    n, m = len(A), len(A[0])
    return [[A[i][j] for i in range(n)] for j in range(m)]


def _mat_mul(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
    """Multiply matrix A (n×m) by B (m×p), returning n×p result."""
    n, m = len(A), len(A[0])
    p = len(B[0])
    C = [[0.0] * p for _ in range(n)]
    for i in range(n):
        for k in range(m):
            if A[i][k] == 0.0:
                continue
            for j in range(p):
                C[i][j] += A[i][k] * B[k][j]
    return C


def _mat_inv(A: List[List[float]]) -> List[List[float]]:
    """Invert square matrix A using Gauss-Jordan elimination with partial pivoting."""
    n = len(A)
    M: List[List[float]] = [
        row[:] + [1.0 if i == j else 0.0 for j in range(n)]
        for i, row in enumerate(A)
    ]
    for col in range(n):
        max_row = max(range(col, n), key=lambda r: abs(M[r][col]))
        M[col], M[max_row] = M[max_row], M[col]
        pivot = M[col][col]
        if abs(pivot) < 1e-14:
            ridge = 1e-8
            M[col][col] += ridge
            pivot = M[col][col]
        M[col] = [x / pivot for x in M[col]]
        for row in range(n):
            if row != col:
                f = M[row][col]
                M[row] = [M[row][j] - f * M[col][j] for j in range(2 * n)]
    return [row[n:] for row in M]


def _ols(
    X: List[List[float]], y: List[List[float]]
) -> Tuple[List[float], List[float], float, float]:
    """Ordinary least squares regression.

    Solves β = (X'X)⁻¹ X'y and computes std errors, R², and adjusted R².

    Args:
        X: Design matrix of shape n × k (rows = observations, cols = factors).
        y: Response column vector of shape n × 1.

    Returns:
        Tuple of (beta, std_errors, r_squared, adj_r_squared).
    """
    n = len(X)
    k = len(X[0])
    Xt = _mat_T(X)
    XtX = _mat_mul(Xt, X)
    Xty = _mat_mul(Xt, y)
    XtX_inv = _mat_inv(XtX)
    beta_mat = _mat_mul(XtX_inv, Xty)
    beta = [b[0] for b in beta_mat]

    y_hat = [sum(X[i][j] * beta[j] for j in range(k)) for i in range(n)]
    y_vals = [row[0] for row in y]
    y_mean = sum(y_vals) / n if n else 0.0

    ss_res = sum((y_vals[i] - y_hat[i]) ** 2 for i in range(n))
    ss_tot = sum((y_vals[i] - y_mean) ** 2 for i in range(n))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-14 else 0.0
    adj_r2 = 1.0 - (1.0 - r2) * (n - 1) / max(n - k - 1, 1)

    mse = ss_res / max(n - k, 1)
    se = [math.sqrt(max(0.0, mse * XtX_inv[j][j])) for j in range(k)]

    return beta, se, max(0.0, r2), adj_r2


def _pearson(x: List[float], y: List[float]) -> float:
    """Compute Pearson correlation coefficient between two equal-length sequences.

    Args:
        x: First sequence of floats.
        y: Second sequence of floats.

    Returns:
        Pearson correlation in [-1, 1], or 0.0 if std of either series is zero.
    """
    n = len(x)
    if n < 2:
        return 0.0
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    sx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    sy = math.sqrt(sum((yi - my) ** 2 for yi in y))
    if sx < 1e-12 or sy < 1e-12:
        return 0.0
    return num / (sx * sy)


# ---------------------------------------------------------------------------
# Domain dataclasses
# ---------------------------------------------------------------------------

@dataclass
class FactorReturn:
    """Observed return for a factor on a single date.

    Attributes:
        date: ISO date string.
        factor: Factor type.
        return_value: Fractional daily return for this factor.
    """

    date: str
    factor: FactorType
    return_value: float


@dataclass
class FactorExposure:
    """Multi-factor regression results for a security or portfolio.

    Attributes:
        ticker: Instrument symbol (or portfolio name).
        alpha: Annualised excess return not explained by factors (Jensen's α).
        betas: Mapping of factor name to factor loading (β).
        t_stats: Mapping of factor name to t-statistic.
        p_values: Approximate two-tailed p-value per factor.
        r_squared: Fraction of return variance explained.
        adj_r_squared: R² adjusted for number of factors.
        tracking_error: Annualised residual standard deviation.
        information_ratio: Alpha divided by tracking error.
    """

    ticker: str
    alpha: float
    betas: Dict[str, float]
    t_stats: Dict[str, float]
    p_values: Dict[str, float]
    r_squared: float
    adj_r_squared: float
    tracking_error: float
    information_ratio: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "ticker": self.ticker,
            "alpha": self.alpha,
            "betas": self.betas,
            "t_stats": self.t_stats,
            "p_values": self.p_values,
            "r_squared": self.r_squared,
            "adj_r_squared": self.adj_r_squared,
            "tracking_error": self.tracking_error,
            "information_ratio": self.information_ratio,
        }


@dataclass
class FactorAttribution:
    """Decomposes a portfolio's total return into factor contributions.

    Attributes:
        ticker: Portfolio or security label.
        total_return: Observed total return over the period.
        factor_contributions: Fractional return attributed to each factor.
        alpha_contribution: Unexplained (idiosyncratic) return component.
        residual: Numerical residual after summing all contributions.
    """

    ticker: str
    total_return: float
    factor_contributions: Dict[str, float]
    alpha_contribution: float
    residual: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "ticker": self.ticker,
            "total_return": self.total_return,
            "factor_contributions": self.factor_contributions,
            "alpha_contribution": self.alpha_contribution,
            "residual": self.residual,
        }


@dataclass
class FactorCorrelation:
    """Pairwise correlation between two factors.

    Attributes:
        factor_a: First factor name.
        factor_b: Second factor name.
        correlation: Pearson correlation coefficient.
        num_observations: Number of date points used.
    """

    factor_a: str
    factor_b: str
    correlation: float
    num_observations: int

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict."""
        return self.__dict__.copy()


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class FactorModelEngine:
    """Fits and queries multi-factor models for securities and portfolios.

    Factor return time series are registered once; individual securities
    are then regressed against the factor matrix.

    Attributes:
        _factor_returns: Stored factor returns per date.
        _exposures: Cached FactorExposure results keyed by ticker.
    """

    def __init__(self) -> None:
        self._factor_returns: Dict[str, Dict[str, float]] = {}
        self._exposures: Dict[str, FactorExposure] = {}

    def reset(self) -> None:
        """Clear all stored factor data and cached exposures."""
        self._factor_returns.clear()
        self._exposures.clear()

    def add_factor_returns(self, factor_rets: List[FactorReturn]) -> None:
        """Register daily factor returns.

        Args:
            factor_rets: List of FactorReturn observations to store.
        """
        for fr in factor_rets:
            self._factor_returns.setdefault(fr.date, {})[fr.factor.value] = fr.return_value

    def regress(
        self,
        ticker: str,
        security_returns: Dict[str, float],
        factors: List[FactorType],
        include_alpha: bool = True,
    ) -> FactorExposure:
        """Regress a security's returns against the registered factor returns.

        Args:
            ticker: Symbol or label of the security / portfolio.
            security_returns: Dict mapping ISO date to daily return fraction.
            factors: Which factors to include in the regression.
            include_alpha: If True, add an intercept column to the design matrix.

        Returns:
            FactorExposure with beta estimates, t-stats, and R².
        """
        common_dates = sorted(
            d for d in security_returns if d in self._factor_returns
        )
        if len(common_dates) < max(len(factors) + 2, 10):
            return FactorExposure(
                ticker=ticker,
                alpha=0.0,
                betas={f.value: 0.0 for f in factors},
                t_stats={f.value: 0.0 for f in factors},
                p_values={f.value: 1.0 for f in factors},
                r_squared=0.0,
                adj_r_squared=0.0,
                tracking_error=0.0,
                information_ratio=0.0,
            )

        X: List[List[float]] = []
        y: List[List[float]] = []
        for d in common_dates:
            row: List[float] = []
            if include_alpha:
                row.append(1.0)
            for fac in factors:
                row.append(self._factor_returns[d].get(fac.value, 0.0))
            X.append(row)
            y.append([security_returns[d]])

        beta, se, r2, adj_r2 = _ols(X, y)

        names = (["alpha"] if include_alpha else []) + [f.value for f in factors]
        beta_dict: Dict[str, float] = {}
        t_dict: Dict[str, float] = {}
        p_dict: Dict[str, float] = {}
        for i, name in enumerate(names):
            if name == "alpha":
                continue
            beta_dict[name] = round(beta[i], 6)
            t_val = beta[i] / se[i] if se[i] > 1e-14 else 0.0
            t_dict[name] = round(t_val, 4)
            p_dict[name] = round(self._approx_p_value(t_val, len(common_dates) - len(names)), 4)

        alpha_daily = beta[0] if include_alpha else 0.0
        alpha_ann = (1.0 + alpha_daily) ** 252 - 1.0
        t_alpha = beta[0] / se[0] if se and se[0] > 1e-14 else 0.0
        t_dict["alpha"] = round(t_alpha, 4)
        p_dict["alpha"] = round(self._approx_p_value(t_alpha, len(common_dates) - len(names)), 4)

        y_vals = [row[0] for row in y]
        y_hat = [sum(X[i][j] * beta[j] for j in range(len(beta))) for i in range(len(X))]
        residuals = [y_vals[i] - y_hat[i] for i in range(len(y_vals))]
        res_var = sum(r ** 2 for r in residuals) / max(len(residuals) - 1, 1)
        te = math.sqrt(res_var) * math.sqrt(252.0)
        ir = alpha_ann / te if te > 0 else 0.0

        exposure = FactorExposure(
            ticker=ticker,
            alpha=round(alpha_ann, 6),
            betas=beta_dict,
            t_stats=t_dict,
            p_values=p_dict,
            r_squared=round(r2, 6),
            adj_r_squared=round(adj_r2, 6),
            tracking_error=round(te, 6),
            information_ratio=round(ir, 4),
        )
        self._exposures[ticker] = exposure
        return exposure

    def _approx_p_value(self, t: float, df: int) -> float:
        """Approximate two-tailed p-value from t-statistic using normal approximation.

        Args:
            t: T-statistic value.
            df: Degrees of freedom.

        Returns:
            Approximate p-value in [0, 1].
        """
        abs_t = abs(t)
        p_one_tail = 0.5 * math.erfc(abs_t / math.sqrt(2.0))
        return min(1.0, 2.0 * p_one_tail)

    def get_exposure(self, ticker: str) -> Optional[FactorExposure]:
        """Retrieve a cached factor exposure for a ticker.

        Args:
            ticker: Symbol whose exposure was previously computed.

        Returns:
            FactorExposure or None.
        """
        return self._exposures.get(ticker)

    def compute_attribution(
        self,
        ticker: str,
        total_return: float,
        period_factor_returns: Dict[str, float],
    ) -> FactorAttribution:
        """Decompose total return into factor and alpha contributions.

        Args:
            ticker: Symbol whose exposure is used.
            total_return: Observed total return over the attribution period.
            period_factor_returns: Cumulative factor return per factor name.

        Returns:
            FactorAttribution with factor contributions and residual.
        """
        exposure = self._exposures.get(ticker)
        if not exposure:
            return FactorAttribution(
                ticker=ticker,
                total_return=total_return,
                factor_contributions={},
                alpha_contribution=0.0,
                residual=total_return,
            )
        contributions: Dict[str, float] = {}
        explained = 0.0
        for fac_name, beta in exposure.betas.items():
            fac_ret = period_factor_returns.get(fac_name, 0.0)
            contrib = beta * fac_ret
            contributions[fac_name] = round(contrib, 6)
            explained += contrib

        alpha_contrib = exposure.alpha
        residual = total_return - explained - alpha_contrib
        return FactorAttribution(
            ticker=ticker,
            total_return=round(total_return, 6),
            factor_contributions=contributions,
            alpha_contribution=round(alpha_contrib, 6),
            residual=round(residual, 6),
        )

    def compute_factor_correlations(
        self,
        factors: List[FactorType],
    ) -> List[FactorCorrelation]:
        """Compute pairwise Pearson correlations between registered factors.

        Args:
            factors: Factor types to include in the correlation matrix.

        Returns:
            List of FactorCorrelation objects (upper triangle only).
        """
        dates = sorted(self._factor_returns.keys())
        correlations: List[FactorCorrelation] = []
        for i, fa in enumerate(factors):
            for j, fb in enumerate(factors):
                if j <= i:
                    continue
                ra = [self._factor_returns[d].get(fa.value, 0.0) for d in dates]
                rb = [self._factor_returns[d].get(fb.value, 0.0) for d in dates]
                corr = self._pearson(ra, rb)
                correlations.append(FactorCorrelation(
                    factor_a=fa.value,
                    factor_b=fb.value,
                    correlation=round(corr, 6),
                    num_observations=len(dates),
                ))
        return correlations

    def _pearson(self, x: List[float], y: List[float]) -> float:
        """Compute Pearson correlation between two equal-length series.

        Args:
            x: First series.
            y: Second series.

        Returns:
            Pearson r in [-1, 1].
        """
        n = len(x)
        if n < 2:
            return 0.0
        mx = sum(x) / n
        my = sum(y) / n
        num = sum((x[i] - mx) * (y[i] - my) for i in range(n))
        dx = math.sqrt(sum((v - mx) ** 2 for v in x))
        dy = math.sqrt(sum((v - my) ** 2 for v in y))
        if dx < 1e-14 or dy < 1e-14:
            return 0.0
        return num / (dx * dy)

    def build_factor_return_series(
        self,
        factor: FactorType,
    ) -> List[Dict[str, Any]]:
        """Retrieve the stored time series for a single factor.

        Args:
            factor: The factor whose returns to retrieve.

        Returns:
            List of {date, return_value} dicts sorted by date.
        """
        return [
            {"date": d, "return_value": vals[factor.value]}
            for d, vals in sorted(self._factor_returns.items())
            if factor.value in vals
        ]

    def compute_portfolio_beta(
        self,
        weights: Dict[str, float],
        factor: FactorType,
    ) -> float:
        """Compute the weighted-average factor beta for a portfolio.

        Args:
            weights: Mapping of ticker to portfolio weight (sum should equal 1).
            factor: Factor for which to aggregate the beta.

        Returns:
            Portfolio-level beta for the specified factor.
        """
        total = 0.0
        for ticker, w in weights.items():
            exp = self._exposures.get(ticker)
            if exp:
                total += w * exp.betas.get(factor.value, 0.0)
        return round(total, 6)

    def list_tickers(self) -> List[str]:
        """List all tickers with stored factor exposures.

        Returns:
            Sorted list of ticker symbols.
        """
        return sorted(self._exposures.keys())
