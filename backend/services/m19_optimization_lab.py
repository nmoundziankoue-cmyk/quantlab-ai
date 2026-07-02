"""Portfolio optimization engine: mean-variance, risk parity, min-variance, max-Sharpe."""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from services.m19_factor_models import FactorModelEngine, FactorType, _mat_inv, _mat_T, _mat_mul


class OptimizationType(str, Enum):
    """Optimisation objective."""

    MEAN_VARIANCE = "MEAN_VARIANCE"
    MIN_VARIANCE = "MIN_VARIANCE"
    MAX_SHARPE = "MAX_SHARPE"
    RISK_PARITY = "RISK_PARITY"
    MAX_DIVERSIFICATION = "MAX_DIVERSIFICATION"


@dataclass
class WeightConstraint:
    """Per-asset or sector weight bounds.

    Attributes:
        ticker: Asset symbol this constraint applies to (None = global).
        min_weight: Minimum allowed portfolio weight.
        max_weight: Maximum allowed portfolio weight.
        sector: If set, constraint applies to all assets in this sector.
    """

    ticker: Optional[str] = None
    min_weight: float = 0.0
    max_weight: float = 1.0
    sector: Optional[str] = None


@dataclass
class OptimizationResult:
    """Result of a portfolio optimisation run.

    Attributes:
        result_id: Unique identifier.
        optimization_type: Which objective was used.
        weights: Asset weights (sum = 1).
        expected_return: Annualised expected portfolio return.
        volatility: Annualised portfolio volatility.
        sharpe_ratio: Return-to-risk ratio (rf = 4%).
        diversification_ratio: Weighted-average vol divided by portfolio vol.
        max_weight: Largest single-asset weight.
        min_weight: Smallest single-asset weight (non-zero).
        num_assets: Number of assets with weight > 1 bps.
        risk_contributions: Fractional risk contribution per asset.
        iterations: Number of solver iterations used.
    """

    result_id: str
    optimization_type: OptimizationType
    weights: Dict[str, float]
    expected_return: float
    volatility: float
    sharpe_ratio: float
    diversification_ratio: float
    max_weight: float
    min_weight: float
    num_assets: int
    risk_contributions: Dict[str, float]
    iterations: int

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "result_id": self.result_id,
            "optimization_type": self.optimization_type.value,
            "weights": self.weights,
            "expected_return": self.expected_return,
            "volatility": self.volatility,
            "sharpe_ratio": self.sharpe_ratio,
            "diversification_ratio": self.diversification_ratio,
            "max_weight": self.max_weight,
            "min_weight": self.min_weight,
            "num_assets": self.num_assets,
            "risk_contributions": self.risk_contributions,
            "iterations": self.iterations,
        }


@dataclass
class FrontierPoint:
    """Single point on the efficient frontier.

    Attributes:
        expected_return: Annualised expected return at this point.
        volatility: Annualised portfolio volatility at this point.
        sharpe_ratio: Sharpe ratio at this point.
        weights: Asset weights corresponding to this frontier point.
    """

    expected_return: float
    volatility: float
    sharpe_ratio: float
    weights: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "expected_return": self.expected_return,
            "volatility": self.volatility,
            "sharpe_ratio": self.sharpe_ratio,
            "weights": self.weights,
        }


class OptimizationLab:
    """Portfolio optimisation laboratory supporting four objectives.

    All optimisation routines are implemented in pure Python using
    iterative / gradient-descent methods.  Covariance matrices are
    inverted analytically via Gauss-Jordan elimination (imported from
    the factor models module).

    Attributes:
        _results: Cached OptimizationResult objects.
        _factor_engine: Optional FactorModelEngine for factor-constrained runs.
    """

    def __init__(self, factor_engine: Optional[FactorModelEngine] = None) -> None:
        self._results: Dict[str, OptimizationResult] = {}
        self._factor_engine = factor_engine

    def reset(self) -> None:
        """Clear all cached optimisation results."""
        self._results.clear()

    # ------------------------------------------------------------------
    # Public optimisation methods
    # ------------------------------------------------------------------

    def mean_variance(
        self,
        tickers: List[str],
        expected_returns: Dict[str, float],
        covariance_matrix: Dict[str, Dict[str, float]],
        risk_aversion: float = 2.0,
        constraints: Optional[List[WeightConstraint]] = None,
        risk_free_rate: float = 0.04,
    ) -> OptimizationResult:
        """Solve the mean-variance optimisation problem.

        Maximises U = μ'w - λ/2 * w'Σw subject to sum(w)=1 and
        optional per-asset weight bounds via projected gradient descent.

        Args:
            tickers: Asset symbols to include.
            expected_returns: Annual expected return per ticker.
            covariance_matrix: Annual covariance matrix as nested dict.
            risk_aversion: Lambda (λ) risk-aversion coefficient.
            constraints: Per-asset weight bounds.
            risk_free_rate: Annual risk-free rate for Sharpe calculation.

        Returns:
            OptimizationResult with optimal weights and diagnostics.
        """
        n = len(tickers)
        mu = [expected_returns.get(t, 0.0) for t in tickers]
        Sigma = self._build_cov_matrix(tickers, covariance_matrix)
        lb, ub = self._build_bounds(tickers, constraints)

        w = [1.0 / n] * n
        lr = 0.01
        iters = 0
        for _ in range(2000):
            iters += 1
            grad = [
                risk_aversion * sum(Sigma[i][j] * w[j] for j in range(n)) - mu[i]
                for i in range(n)
            ]
            w_new = [max(lb[i], min(ub[i], w[i] - lr * grad[i])) for i in range(n)]
            w_new = self._project_simplex(w_new, lb, ub)
            diff = math.sqrt(sum((w_new[i] - w[i]) ** 2 for i in range(n)))
            w = w_new
            if diff < 1e-8:
                break

        return self._build_result(
            tickers, w, mu, Sigma, OptimizationType.MEAN_VARIANCE, risk_free_rate, iters
        )

    def min_variance(
        self,
        tickers: List[str],
        covariance_matrix: Dict[str, Dict[str, float]],
        constraints: Optional[List[WeightConstraint]] = None,
        risk_free_rate: float = 0.04,
    ) -> OptimizationResult:
        """Find the global minimum-variance portfolio.

        When unconstrained, applies the analytic solution w = Σ⁻¹1 / (1'Σ⁻¹1).
        Constraints are enforced via projected gradient descent fallback.

        Args:
            tickers: Asset symbols to include.
            covariance_matrix: Annual covariance matrix.
            constraints: Per-asset weight bounds.
            risk_free_rate: Annual risk-free rate.

        Returns:
            OptimizationResult at the minimum variance point.
        """
        n = len(tickers)
        Sigma = self._build_cov_matrix(tickers, covariance_matrix)
        lb, ub = self._build_bounds(tickers, constraints)
        all_unconstrained = all(lb[i] == 0.0 and ub[i] == 1.0 for i in range(n))

        iters = 1
        if all_unconstrained:
            try:
                Sigma_inv = _mat_inv(Sigma)
                ones = [[1.0]] * n
                w_unnorm = _mat_mul(Sigma_inv, ones)
                total = sum(row[0] for row in w_unnorm)
                w = [row[0] / total if total > 0 else 1.0 / n for row in w_unnorm]
                w = [max(0.0, min(1.0, wi)) for wi in w]
            except (ValueError, ZeroDivisionError):
                w = [1.0 / n] * n
        else:
            w = [1.0 / n] * n
            lr = 0.01
            for _ in range(2000):
                iters += 1
                grad = [2.0 * sum(Sigma[i][j] * w[j] for j in range(n)) for i in range(n)]
                w_new = [max(lb[i], min(ub[i], w[i] - lr * grad[i])) for i in range(n)]
                w_new = self._project_simplex(w_new, lb, ub)
                diff = math.sqrt(sum((w_new[i] - w[i]) ** 2 for i in range(n)))
                w = w_new
                if diff < 1e-8:
                    break

        mu = [0.0] * n
        return self._build_result(
            tickers, w, mu, Sigma, OptimizationType.MIN_VARIANCE, risk_free_rate, iters
        )

    def max_sharpe(
        self,
        tickers: List[str],
        expected_returns: Dict[str, float],
        covariance_matrix: Dict[str, Dict[str, float]],
        constraints: Optional[List[WeightConstraint]] = None,
        risk_free_rate: float = 0.04,
    ) -> OptimizationResult:
        """Find the portfolio that maximises the Sharpe ratio.

        Uses gradient ascent on the Sharpe objective with projection
        onto the feasible simplex at each iteration.

        Args:
            tickers: Asset symbols to include.
            expected_returns: Annual expected return per ticker.
            covariance_matrix: Annual covariance matrix.
            constraints: Per-asset weight bounds.
            risk_free_rate: Annual risk-free rate.

        Returns:
            OptimizationResult at the maximum Sharpe point.
        """
        n = len(tickers)
        mu = [expected_returns.get(t, 0.0) for t in tickers]
        Sigma = self._build_cov_matrix(tickers, covariance_matrix)
        lb, ub = self._build_bounds(tickers, constraints)

        w = [1.0 / n] * n
        best_sharpe = -1e18
        best_w = w[:]
        lr = 0.05
        iters = 0
        for _ in range(3000):
            iters += 1
            port_ret = sum(mu[i] * w[i] for i in range(n))
            port_var = sum(Sigma[i][j] * w[i] * w[j] for i in range(n) for j in range(n))
            port_vol = math.sqrt(max(port_var, 1e-12))
            excess = port_ret - risk_free_rate
            sharpe = excess / port_vol

            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_w = w[:]

            grad_ret = mu[:]
            grad_vol = [
                sum(Sigma[i][j] * w[j] for j in range(n)) / port_vol
                for i in range(n)
            ]
            grad_sharpe = [
                (grad_ret[i] * port_vol - excess * grad_vol[i]) / (port_vol ** 2)
                for i in range(n)
            ]
            w_new = [max(lb[i], min(ub[i], w[i] + lr * grad_sharpe[i])) for i in range(n)]
            w_new = self._project_simplex(w_new, lb, ub)
            diff = math.sqrt(sum((w_new[i] - w[i]) ** 2 for i in range(n)))
            w = w_new
            if diff < 1e-9:
                break

        return self._build_result(
            tickers, best_w, mu, Sigma, OptimizationType.MAX_SHARPE, risk_free_rate, iters
        )

    def risk_parity(
        self,
        tickers: List[str],
        covariance_matrix: Dict[str, Dict[str, float]],
        target_risk_contributions: Optional[Dict[str, float]] = None,
        risk_free_rate: float = 0.04,
    ) -> OptimizationResult:
        """Find the risk-parity portfolio (equal risk contribution).

        Uses iterative Newton-type updates until each asset's marginal
        risk contribution matches its target share.

        Args:
            tickers: Asset symbols to include.
            covariance_matrix: Annual covariance matrix.
            target_risk_contributions: Optional mapping of ticker to target
                fractional risk share (defaults to 1/n for all assets).
            risk_free_rate: Annual risk-free rate.

        Returns:
            OptimizationResult where each asset contributes equally to risk.
        """
        n = len(tickers)
        Sigma = self._build_cov_matrix(tickers, covariance_matrix)

        if target_risk_contributions:
            targets = [target_risk_contributions.get(t, 1.0 / n) for t in tickers]
        else:
            targets = [1.0 / n] * n
        total_t = sum(targets)
        targets = [t / total_t for t in targets]

        w = [1.0 / n] * n
        iters = 0
        for _ in range(3000):
            iters += 1
            Sw = [sum(Sigma[i][j] * w[j] for j in range(n)) for i in range(n)]
            port_var = sum(w[i] * Sw[i] for i in range(n))
            port_vol = math.sqrt(max(port_var, 1e-12))
            mrc = [Sw[i] / port_vol for i in range(n)]
            rc = [w[i] * mrc[i] for i in range(n)]
            total_rc = sum(rc)

            converged = True
            for i in range(n):
                target_rc = targets[i] * total_rc
                if abs(rc[i] - target_rc) > 1e-8 * total_rc:
                    converged = False
                    break
            if converged:
                break

            for i in range(n):
                if rc[i] > 1e-12:
                    w[i] *= targets[i] * total_rc / rc[i]
            total_w = sum(w)
            if total_w > 0:
                w = [wi / total_w for wi in w]

        mu = [0.0] * n
        return self._build_result(
            tickers, w, mu, Sigma, OptimizationType.RISK_PARITY, risk_free_rate, iters
        )

    def compute_frontier(
        self,
        tickers: List[str],
        expected_returns: Dict[str, float],
        covariance_matrix: Dict[str, Dict[str, float]],
        n_points: int = 20,
        risk_free_rate: float = 0.04,
        constraints: Optional[List[WeightConstraint]] = None,
    ) -> List[FrontierPoint]:
        """Trace the efficient frontier by sweeping risk-aversion values.

        Args:
            tickers: Asset symbols.
            expected_returns: Annual expected return per ticker.
            covariance_matrix: Annual covariance matrix.
            n_points: Number of frontier points to compute.
            risk_free_rate: Annual risk-free rate for Sharpe.
            constraints: Optional per-asset weight bounds.

        Returns:
            List of FrontierPoint objects from min-variance to max-return.
        """
        lambdas = [0.1 + 9.9 * i / max(n_points - 1, 1) for i in range(n_points)]
        points: List[FrontierPoint] = []
        seen_vols: set = set()

        for lam in lambdas:
            res = self.mean_variance(
                tickers, expected_returns, covariance_matrix,
                risk_aversion=lam, constraints=constraints, risk_free_rate=risk_free_rate,
            )
            vol_key = round(res.volatility, 4)
            if vol_key in seen_vols:
                continue
            seen_vols.add(vol_key)
            points.append(FrontierPoint(
                expected_return=res.expected_return,
                volatility=res.volatility,
                sharpe_ratio=res.sharpe_ratio,
                weights={t: res.weights.get(t, 0.0) for t in tickers},
            ))

        points.sort(key=lambda p: p.volatility)
        return points

    def factor_constrained_optimize(
        self,
        tickers: List[str],
        expected_returns: Dict[str, float],
        covariance_matrix: Dict[str, Dict[str, float]],
        factor_constraints: Dict[str, Tuple[float, float]],
        risk_aversion: float = 2.0,
        risk_free_rate: float = 0.04,
    ) -> OptimizationResult:
        """Mean-variance optimisation with factor exposure constraints.

        Penalises deviations from allowed factor exposure ranges.
        Requires that factor exposures have been precomputed via the
        FactorModelEngine.

        Args:
            tickers: Asset symbols.
            expected_returns: Annual expected return per ticker.
            covariance_matrix: Annual covariance matrix.
            factor_constraints: Mapping of factor name to (min_beta, max_beta).
            risk_aversion: Risk-aversion coefficient.
            risk_free_rate: Annual risk-free rate.

        Returns:
            OptimizationResult satisfying factor constraints.
        """
        n = len(tickers)
        mu = [expected_returns.get(t, 0.0) for t in tickers]
        Sigma = self._build_cov_matrix(tickers, covariance_matrix)
        lb = [0.0] * n
        ub = [1.0] * n

        betas_per_factor: Dict[str, List[float]] = {}
        if self._factor_engine:
            for fac_name in factor_constraints:
                try:
                    fac_type = FactorType(fac_name)
                except ValueError:
                    fac_type = None
                row: List[float] = []
                for t in tickers:
                    exp = self._factor_engine.get_exposure(t)
                    if exp and fac_type:
                        row.append(exp.betas.get(fac_name, 0.0))
                    else:
                        row.append(0.0)
                betas_per_factor[fac_name] = row

        penalty_weight = 100.0
        w = [1.0 / n] * n
        lr = 0.01
        iters = 0
        for _ in range(2000):
            iters += 1
            grad = [
                risk_aversion * sum(Sigma[i][j] * w[j] for j in range(n)) - mu[i]
                for i in range(n)
            ]
            for fac_name, (lo, hi) in factor_constraints.items():
                betas = betas_per_factor.get(fac_name, [0.0] * n)
                port_beta = sum(betas[i] * w[i] for i in range(n))
                if port_beta < lo:
                    pen_grad = [-2.0 * penalty_weight * (port_beta - lo) * betas[i] for i in range(n)]
                    grad = [grad[i] + pen_grad[i] for i in range(n)]
                elif port_beta > hi:
                    pen_grad = [-2.0 * penalty_weight * (port_beta - hi) * betas[i] for i in range(n)]
                    grad = [grad[i] + pen_grad[i] for i in range(n)]

            w_new = [max(lb[i], min(ub[i], w[i] - lr * grad[i])) for i in range(n)]
            w_new = self._project_simplex(w_new, lb, ub)
            diff = math.sqrt(sum((w_new[i] - w[i]) ** 2 for i in range(n)))
            w = w_new
            if diff < 1e-8:
                break

        return self._build_result(
            tickers, w, mu, Sigma, OptimizationType.MEAN_VARIANCE, risk_free_rate, iters
        )

    # ------------------------------------------------------------------
    # Result retrieval
    # ------------------------------------------------------------------

    def get_result(self, result_id: str) -> Optional[OptimizationResult]:
        """Retrieve a cached optimisation result.

        Args:
            result_id: UUID from a previous optimisation call.

        Returns:
            OptimizationResult or None if not found.
        """
        return self._results.get(result_id)

    def list_results(self) -> List[Dict[str, Any]]:
        """Summarise all cached optimisation results.

        Returns:
            List of summary dicts.
        """
        return [
            {
                "result_id": rid,
                "optimization_type": r.optimization_type.value,
                "sharpe_ratio": r.sharpe_ratio,
                "volatility": r.volatility,
                "num_assets": r.num_assets,
            }
            for rid, r in self._results.items()
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_cov_matrix(
        self,
        tickers: List[str],
        cov: Dict[str, Dict[str, float]],
    ) -> List[List[float]]:
        """Convert a nested-dict covariance matrix to a 2-D list.

        Diagonal elements are set to max(sigma²_i, 1e-6) to ensure
        positive definiteness.

        Args:
            tickers: Ordered asset list.
            cov: Covariance matrix as nested dicts.

        Returns:
            2-D list of floats representing the covariance matrix.
        """
        n = len(tickers)
        Sigma: List[List[float]] = []
        for i, ti in enumerate(tickers):
            row: List[float] = []
            for j, tj in enumerate(tickers):
                val = cov.get(ti, {}).get(tj, 0.0)
                if i == j:
                    val = max(val, 1e-6)
                row.append(val)
            Sigma.append(row)
        return Sigma

    def _build_bounds(
        self,
        tickers: List[str],
        constraints: Optional[List[WeightConstraint]],
    ) -> Tuple[List[float], List[float]]:
        """Extract per-asset lower and upper weight bounds.

        Args:
            tickers: Ordered asset list.
            constraints: Optional constraint specs.

        Returns:
            Tuple of (lower_bounds, upper_bounds) lists.
        """
        lb = [0.0] * len(tickers)
        ub = [1.0] * len(tickers)
        if not constraints:
            return lb, ub
        for con in constraints:
            if con.ticker and con.ticker in tickers:
                idx = tickers.index(con.ticker)
                lb[idx] = max(lb[idx], con.min_weight)
                ub[idx] = min(ub[idx], con.max_weight)
        return lb, ub

    def _project_simplex(
        self,
        w: List[float],
        lb: List[float],
        ub: List[float],
    ) -> List[float]:
        """Project weights onto the probability simplex with box constraints.

        Uses the iterative clipping and re-normalisation algorithm.

        Args:
            w: Raw (un-normalised) weights after gradient step.
            lb: Per-asset lower bounds.
            ub: Per-asset upper bounds.

        Returns:
            Feasible weights satisfying sum=1 and lb_i <= w_i <= ub_i.
        """
        n = len(w)
        for _ in range(200):
            s = sum(w)
            if s > 1e-12:
                w = [wi / s for wi in w]
            for i in range(n):
                w[i] = max(lb[i], min(ub[i], w[i]))
            if abs(sum(w) - 1.0) < 1e-9:
                break
        s = sum(w)
        if s > 0:
            w = [wi / s for wi in w]
        return w

    def _compute_risk_contributions(
        self, w: List[float], Sigma: List[List[float]]
    ) -> List[float]:
        """Compute each asset's fractional contribution to portfolio risk.

        Args:
            w: Portfolio weights.
            Sigma: Covariance matrix.

        Returns:
            List of risk contributions summing to 1.
        """
        n = len(w)
        Sw = [sum(Sigma[i][j] * w[j] for j in range(n)) for i in range(n)]
        port_var = sum(w[i] * Sw[i] for i in range(n))
        port_vol = math.sqrt(max(port_var, 1e-12))
        rc = [w[i] * Sw[i] / port_vol for i in range(n)]
        total = sum(rc)
        return [r / total if total > 0 else 1.0 / n for r in rc]

    def _build_result(
        self,
        tickers: List[str],
        w: List[float],
        mu: List[float],
        Sigma: List[List[float]],
        opt_type: OptimizationType,
        risk_free_rate: float,
        iters: int,
    ) -> OptimizationResult:
        """Package raw weight vector into an OptimizationResult.

        Args:
            tickers: Asset symbols in order.
            w: Optimised weight vector.
            mu: Expected return vector.
            Sigma: Covariance matrix.
            opt_type: Optimisation objective used.
            risk_free_rate: Annual risk-free rate.
            iters: Solver iteration count.

        Returns:
            Populated OptimizationResult cached and returned.
        """
        n = len(tickers)
        port_ret = sum(mu[i] * w[i] for i in range(n))
        port_var = sum(Sigma[i][j] * w[i] * w[j] for i in range(n) for j in range(n))
        port_vol = math.sqrt(max(port_var, 0.0))

        Sw = [sum(Sigma[i][j] * w[j] for j in range(n)) for i in range(n)]
        ind_vols = [math.sqrt(max(Sigma[i][i], 0.0)) for i in range(n)]
        weighted_avg_vol = sum(w[i] * ind_vols[i] for i in range(n))
        div_ratio = weighted_avg_vol / port_vol if port_vol > 0 else 1.0

        sharpe = (port_ret - risk_free_rate) / port_vol if port_vol > 0 else 0.0
        rc = self._compute_risk_contributions(w, Sigma)
        weights_dict = {tickers[i]: round(w[i], 6) for i in range(n)}
        rc_dict = {tickers[i]: round(rc[i], 6) for i in range(n)}
        nonzero_w = [wi for wi in w if wi > 1e-4]

        result_id = str(uuid.uuid4())
        result = OptimizationResult(
            result_id=result_id,
            optimization_type=opt_type,
            weights=weights_dict,
            expected_return=round(port_ret, 6),
            volatility=round(port_vol, 6),
            sharpe_ratio=round(sharpe, 4),
            diversification_ratio=round(div_ratio, 4),
            max_weight=round(max(w), 6) if w else 0.0,
            min_weight=round(min(nonzero_w), 6) if nonzero_w else 0.0,
            num_assets=len(nonzero_w),
            risk_contributions=rc_dict,
            iterations=iters,
        )
        self._results[result_id] = result
        return result
