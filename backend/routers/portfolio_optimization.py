"""M12 — Portfolio Optimization API router.

Prefix: /portfolio-optimization

Endpoints:
  GET  /methods                  — list available optimization methods
  POST /optimize                 — run a single method
  POST /compare                  — run all methods for comparison
  POST /frontier                 — compute efficient frontier
  POST /risk                     — compute full risk report
  POST /attribution              — risk attribution for given weights
  POST /stress                   — stress test (single or all built-in scenarios)
  POST /monte-carlo              — Monte Carlo projection
  POST /covariance               — covariance diagnostics
  POST /full-analysis            — optimize + frontier + stress + MC in one call
"""
from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, status

from schemas.portfolio_optimization import (
    AllScenariosResponse,
    AttributionRequest,
    AttributionResponse,
    CompareRequest,
    CovRequest,
    CovResponse,
    FrontierRequest,
    FrontierResponse,
    FullAnalysisRequest,
    MethodInfo,
    MethodsResponse,
    MonteCarloRequest,
    MonteCarloResponse,
    OptimizeRequest,
    OptimizeResponse,
    RiskRequest,
    RiskResponse,
    StressRequest,
    StressResponse,
)
from services.portfolio_monte_carlo import MonteCarloConfig, run_portfolio_monte_carlo
from services.portfolio_optimizer import (
    AVAILABLE_METHODS,
    BUILTIN_STRESS_SCENARIOS,
    OptimizationConstraints,
    PortfolioOptimizationConfig,
    apply_stress_scenario,
    compare_methods,
    compute_risk_attribution,
    covariance_diagnostics,
    efficient_frontier,
    estimate_covariance,
    optimize,
    run_all_stress_scenarios,
    StressScenarioConfig,
)
from services.portfolio_risk_engine import compute_full_risk_report

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/portfolio-optimization",
    tags=["Portfolio Optimization"],
)

_METHOD_META: Dict[str, Dict[str, Any]] = {
    "equal_weight":          {"display_name": "Equal Weight",            "requires_returns": False, "requires_target": None},
    "inverse_volatility":    {"display_name": "Inverse Volatility",      "requires_returns": False, "requires_target": None},
    "min_variance":          {"display_name": "Minimum Variance",        "requires_returns": False, "requires_target": None},
    "max_sharpe":            {"display_name": "Maximum Sharpe",          "requires_returns": False, "requires_target": None},
    "mean_variance":         {"display_name": "Mean-Variance Utility",   "requires_returns": False, "requires_target": None},
    "target_return":         {"display_name": "Target Return",           "requires_returns": False, "requires_target": "target_return"},
    "target_volatility":     {"display_name": "Target Volatility",       "requires_returns": False, "requires_target": "target_volatility"},
    "risk_parity":           {"display_name": "Risk Parity",             "requires_returns": False, "requires_target": None},
    "max_diversification":   {"display_name": "Max Diversification",     "requires_returns": False, "requires_target": None},
    "hrp":                   {"display_name": "Hierarchical Risk Parity","requires_returns": False, "requires_target": None},
    "black_litterman":       {"display_name": "Black-Litterman",         "requires_returns": False, "requires_target": None},
    "kelly":                 {"display_name": "Kelly Criterion",         "requires_returns": False, "requires_target": None},
    "cvar_optimization":     {"display_name": "CVaR Optimisation",       "requires_returns": True,  "requires_target": None},
    "long_short_constrained":{"display_name": "Long/Short Constrained",  "requires_returns": False, "requires_target": None},
}


# ===========================================================================
# Helpers
# ===========================================================================

def _build_config(req: OptimizeRequest) -> PortfolioOptimizationConfig:
    c = OptimizationConstraints(
        long_only=req.constraints.long_only,
        max_weight=req.constraints.max_weight,
        min_weight=req.constraints.min_weight,
        leverage_cap=req.constraints.leverage_cap,
        gross_exposure_cap=req.constraints.gross_exposure_cap,
        net_exposure_min=req.constraints.net_exposure_min,
        net_exposure_max=req.constraints.net_exposure_max,
    )
    return PortfolioOptimizationConfig(
        tickers=req.tickers,
        mu=req.mu,
        cov=req.cov,
        risk_free_rate=req.risk_free_rate,
        constraints=c,
        target_return=req.target_return,
        target_volatility=req.target_volatility,
        gamma=req.gamma,
        kelly_fraction=req.kelly_fraction,
        views_P=req.views_P,
        views_q=req.views_q,
        market_weights=req.market_weights,
        returns_matrix=req.returns_matrix,
    )


def _result_to_response(r: Any) -> OptimizeResponse:
    return OptimizeResponse(
        method=r.method,
        tickers=r.tickers,
        weights=r.weights,
        expected_return=r.expected_return,
        expected_volatility=r.expected_volatility,
        sharpe_ratio=r.sharpe_ratio,
        diversification_ratio=r.diversification_ratio,
        concentration_score=r.concentration_score,
        effective_n=r.effective_n,
        gross_exposure=r.gross_exposure,
        net_exposure=r.net_exposure,
        leverage=r.leverage,
        risk_contributions=r.risk_contributions,
        warnings=r.warnings,
        converged=r.converged,
    )


# ===========================================================================
# Endpoints
# ===========================================================================

@router.get("/methods", response_model=MethodsResponse)
def list_methods() -> MethodsResponse:
    """List all available optimization methods."""
    items = [
        MethodInfo(
            key=k,
            display_name=v["display_name"],
            requires_returns=v["requires_returns"],
            requires_target=v["requires_target"],
        )
        for k, v in _METHOD_META.items()
    ]
    return MethodsResponse(methods=items)


@router.post("/optimize", response_model=OptimizeResponse)
def optimize_endpoint(req: OptimizeRequest) -> OptimizeResponse:
    """Run a single optimization method."""
    try:
        config = _build_config(req)
        result = optimize(config, req.method)
        return _result_to_response(result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        logger.exception("Optimization error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Optimization failed: {exc}")


@router.post("/compare", response_model=List[OptimizeResponse])
def compare_endpoint(req: CompareRequest) -> List[OptimizeResponse]:
    """Run multiple methods and return results for side-by-side comparison."""
    try:
        c = OptimizationConstraints(
            long_only=req.constraints.long_only,
            max_weight=req.constraints.max_weight,
            min_weight=req.constraints.min_weight,
            leverage_cap=req.constraints.leverage_cap,
            gross_exposure_cap=req.constraints.gross_exposure_cap,
        )
        config = PortfolioOptimizationConfig(
            tickers=req.tickers,
            mu=req.mu,
            cov=req.cov,
            risk_free_rate=req.risk_free_rate,
            constraints=c,
            gamma=req.gamma,
            kelly_fraction=req.kelly_fraction,
            returns_matrix=req.returns_matrix,
        )
        results = compare_methods(config, req.methods)
        return [_result_to_response(r) for r in results]
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        logger.exception("Comparison error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Comparison failed: {exc}")


@router.post("/frontier", response_model=FrontierResponse)
def frontier_endpoint(req: FrontierRequest) -> FrontierResponse:
    """Compute the mean-variance efficient frontier."""
    try:
        c = OptimizationConstraints(
            long_only=req.constraints.long_only,
            max_weight=req.constraints.max_weight,
            min_weight=req.constraints.min_weight,
        )
        config = PortfolioOptimizationConfig(
            tickers=req.tickers,
            mu=req.mu,
            cov=req.cov,
            risk_free_rate=req.risk_free_rate,
            constraints=c,
            n_frontier_points=req.n_points,
        )
        result = efficient_frontier(config)
        return FrontierResponse(
            points=[
                dict(expected_return=p.expected_return, expected_volatility=p.expected_volatility,
                     sharpe_ratio=p.sharpe_ratio, weights=p.weights, feasible=p.feasible)
                for p in result.points
            ],
            max_sharpe_idx=result.max_sharpe_idx,
            min_vol_idx=result.min_vol_idx,
            equal_weight_point=dict(
                expected_return=result.equal_weight_point.expected_return,
                expected_volatility=result.equal_weight_point.expected_volatility,
                sharpe_ratio=result.equal_weight_point.sharpe_ratio,
                weights=result.equal_weight_point.weights,
                feasible=result.equal_weight_point.feasible,
            ),
            n_feasible=result.n_feasible,
            n_infeasible=result.n_infeasible,
            warnings=result.warnings,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        logger.exception("Frontier error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Frontier computation failed: {exc}")


@router.post("/risk", response_model=RiskResponse)
def risk_endpoint(req: RiskRequest) -> RiskResponse:
    """Compute full institutional risk report from historical returns."""
    try:
        returns = pd.Series(req.returns, dtype=float)
        nav = pd.Series(req.nav, dtype=float)
        bench = pd.Series(req.benchmark_returns, dtype=float) if req.benchmark_returns else None
        report = compute_full_risk_report(returns, nav, bench, req.initial_capital)
        return RiskResponse(
            total_return_pct=report.total_return_pct,
            annual_return_pct=report.annual_return_pct,
            annual_volatility_pct=report.annual_volatility_pct,
            downside_volatility_pct=report.downside_volatility_pct,
            semi_variance_daily=report.semi_variance_daily,
            sharpe_ratio=report.sharpe_ratio,
            sortino_ratio=report.sortino_ratio,
            calmar_ratio=report.calmar_ratio,
            treynor_ratio=report.treynor_ratio,
            information_ratio=report.information_ratio,
            alpha=report.alpha,
            beta=report.beta,
            r_squared=report.r_squared,
            tracking_error_pct=report.tracking_error_pct,
            benchmark_return_pct=report.benchmark_return_pct,
            var=dict(
                var_90=report.var.var_90, var_95=report.var.var_95,
                var_975=report.var.var_975, var_99=report.var.var_99,
                cvar_90=report.var.cvar_90, cvar_95=report.var.cvar_95,
                cvar_975=report.var.cvar_975, cvar_99=report.var.cvar_99,
                method=report.var.method,
            ),
            drawdown=dict(
                max_drawdown_pct=report.drawdown.max_drawdown_pct,
                avg_drawdown_pct=report.drawdown.avg_drawdown_pct,
                max_drawdown_duration_days=report.drawdown.max_drawdown_duration_days,
                avg_drawdown_duration_days=report.drawdown.avg_drawdown_duration_days,
                current_drawdown_pct=report.drawdown.current_drawdown_pct,
                recovery_time_days=report.drawdown.recovery_time_days,
                ulcer_index=report.drawdown.ulcer_index,
                pain_index=report.drawdown.pain_index,
            ),
            distribution=dict(
                mean_daily=report.distribution.mean_daily,
                std_daily=report.distribution.std_daily,
                skewness=report.distribution.skewness,
                kurtosis=report.distribution.kurtosis,
                is_fat_tailed=report.distribution.is_fat_tailed,
                tail_ratio=report.distribution.tail_ratio,
                gain_to_pain=report.distribution.gain_to_pain,
                best_day_pct=report.distribution.best_day_pct,
                worst_day_pct=report.distribution.worst_day_pct,
                positive_days_pct=report.distribution.positive_days_pct,
            ),
            ulcer_index=report.ulcer_index,
            warnings=report.warnings,
        )
    except Exception as exc:
        logger.exception("Risk report error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Risk report failed: {exc}")


@router.post("/attribution", response_model=AttributionResponse)
def attribution_endpoint(req: AttributionRequest) -> AttributionResponse:
    """Compute risk attribution for a given set of portfolio weights."""
    try:
        config = PortfolioOptimizationConfig(
            tickers=req.tickers,
            mu=req.mu,
            cov=req.cov,
        )
        result = compute_risk_attribution(config, req.weights)
        return AttributionResponse(
            tickers=result.tickers,
            weights=result.weights,
            marginal_contributions=result.marginal_contributions,
            component_contributions=result.component_contributions,
            pct_contributions=result.pct_contributions,
            portfolio_volatility=result.portfolio_volatility,
            diversification_benefit=result.diversification_benefit,
            hhi=result.hhi,
            effective_n=result.effective_n,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        logger.exception("Attribution error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Attribution failed: {exc}")


@router.post("/stress", response_model=AllScenariosResponse)
def stress_endpoint(req: StressRequest) -> AllScenariosResponse:
    """Apply stress scenarios to a portfolio.

    If ``scenario_key`` is provided, run that single built-in scenario.
    If ``custom_shocks`` is provided, run a custom scenario.
    Otherwise run all built-in scenarios.
    """
    try:
        if req.custom_shocks:
            sc = StressScenarioConfig(
                name="Custom Scenario",
                description="User-defined per-asset shocks",
                asset_shocks=req.custom_shocks,
                market_shock=req.market_shock,
            )
            result = apply_stress_scenario(req.tickers, req.weights, sc)
            return AllScenariosResponse(scenarios=[
                StressResponse(**{k: v for k, v in asdict(result).items()})
            ])

        if req.scenario_key:
            if req.scenario_key not in BUILTIN_STRESS_SCENARIOS:
                raise ValueError(f"Unknown scenario '{req.scenario_key}'")
            sc = BUILTIN_STRESS_SCENARIOS[req.scenario_key]
            result = apply_stress_scenario(req.tickers, req.weights, sc)
            return AllScenariosResponse(scenarios=[
                StressResponse(**{k: v for k, v in asdict(result).items()})
            ])

        # Run all built-in scenarios
        results = run_all_stress_scenarios(req.tickers, req.weights)
        return AllScenariosResponse(scenarios=[
            StressResponse(**{k: v for k, v in asdict(r).items()}) for r in results
        ])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        logger.exception("Stress test error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Stress test failed: {exc}")


@router.post("/monte-carlo", response_model=MonteCarloResponse)
def monte_carlo_endpoint(req: MonteCarloRequest) -> MonteCarloResponse:
    """Run a multi-asset correlated Monte Carlo portfolio simulation."""
    try:
        hist = np.array(req.returns_matrix) if req.returns_matrix else None
        config = MonteCarloConfig(
            n_simulations=req.n_simulations,
            simulation_days=req.simulation_days,
            model=req.model,
            seed=req.seed,
            initial_value=req.initial_value,
            target_return=req.target_return,
        )
        result = run_portfolio_monte_carlo(req.weights, req.mu, req.cov, config, hist)
        return MonteCarloResponse(
            model=result.model,
            n_simulations=result.n_simulations,
            simulation_days=result.simulation_days,
            initial_value=result.initial_value,
            percentile_paths=result.percentile_paths,
            expected_terminal=result.expected_terminal,
            median_terminal=result.median_terminal,
            std_terminal=result.std_terminal,
            best_case=result.best_case,
            worst_case=result.worst_case,
            probability_of_loss=result.probability_of_loss,
            probability_of_target_return=result.probability_of_target_return,
            var_95=result.var_95,
            cvar_95=result.cvar_95,
            ruin_probability=result.ruin_probability,
            median_max_drawdown_pct=result.median_max_drawdown_pct,
            p95_max_drawdown_pct=result.p95_max_drawdown_pct,
            implied_annual_return=result.implied_annual_return,
            warnings=result.warnings,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        logger.exception("Monte Carlo error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Monte Carlo failed: {exc}")


@router.post("/covariance", response_model=CovResponse)
def covariance_endpoint(req: CovRequest) -> CovResponse:
    """Compute covariance matrix diagnostics and optionally estimate covariance."""
    try:
        returns_arr = np.array(req.returns_matrix, dtype=float)
        if returns_arr.ndim != 2 or returns_arr.shape[1] != len(req.tickers):
            raise ValueError("returns_matrix must be T × len(tickers)")

        diag = covariance_diagnostics(req.tickers, returns_arr, method=req.method)
        cov_est, _ = estimate_covariance(returns_arr, method=req.method)
        std = np.sqrt(np.maximum(np.diag(cov_est), 1e-12))
        corr = cov_est / np.outer(std, std)

        return CovResponse(
            n_assets=diag.n_assets,
            n_observations=diag.n_observations,
            method=diag.method,
            condition_number=diag.condition_number,
            is_positive_definite=diag.is_positive_definite,
            min_eigenvalue=diag.min_eigenvalue,
            max_eigenvalue=diag.max_eigenvalue,
            effective_rank=diag.effective_rank,
            highly_correlated_pairs=diag.highly_correlated_pairs,
            shrinkage_intensity=diag.shrinkage_intensity,
            repaired=diag.repaired,
            warnings=diag.warnings,
            covariance_matrix=cov_est.tolist(),
            correlation_matrix=corr.tolist(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        logger.exception("Covariance error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Covariance analysis failed: {exc}")


@router.post("/full-analysis")
def full_analysis_endpoint(req: FullAnalysisRequest) -> Dict[str, Any]:
    """Run optimize + frontier + stress + MC in a single call.

    Returns a combined JSON object with 'optimization', 'frontier',
    'stress_scenarios', 'monte_carlo' keys.
    """
    try:
        c = OptimizationConstraints(
            long_only=req.constraints.long_only,
            max_weight=req.constraints.max_weight,
            min_weight=req.constraints.min_weight,
            leverage_cap=req.constraints.leverage_cap,
        )
        config = PortfolioOptimizationConfig(
            tickers=req.tickers,
            mu=req.mu,
            cov=req.cov,
            risk_free_rate=req.risk_free_rate,
            constraints=c,
            gamma=req.gamma,
            kelly_fraction=req.kelly_fraction,
            views_P=req.views_P,
            views_q=req.views_q,
            market_weights=req.market_weights,
            returns_matrix=req.returns_matrix,
            n_frontier_points=req.n_frontier_points,
        )

        # Optimize
        opt_result = optimize(config, req.method)
        opt_resp = _result_to_response(opt_result).model_dump()

        # Frontier
        frontier_result = efficient_frontier(config)
        frontier_resp = {
            "points": [
                {"expected_return": p.expected_return, "expected_volatility": p.expected_volatility,
                 "sharpe_ratio": p.sharpe_ratio, "feasible": p.feasible}
                for p in frontier_result.points
            ],
            "max_sharpe_idx": frontier_result.max_sharpe_idx,
            "min_vol_idx": frontier_result.min_vol_idx,
            "n_feasible": frontier_result.n_feasible,
            "warnings": frontier_result.warnings,
        }

        # Attribution
        attr = compute_risk_attribution(config, opt_result.weights)

        # Stress
        stress_resp: List[Dict] = []
        if req.run_stress:
            stress_results = run_all_stress_scenarios(req.tickers, opt_result.weights)
            stress_resp = [
                {"scenario_name": r.scenario_name, "portfolio_impact_pct": r.portfolio_impact_pct,
                 "severity_score": r.severity_score, "worst_contributor": r.worst_contributor}
                for r in stress_results
            ]

        # Monte Carlo
        mc_resp: Optional[Dict] = None
        if req.run_mc:
            mc_config = MonteCarloConfig(
                n_simulations=req.mc_simulations,
                simulation_days=252,
                model="gbm",
                seed=42,
                initial_value=100_000.0,
            )
            hist = np.array(req.returns_matrix) if req.returns_matrix else None
            mc_result = run_portfolio_monte_carlo(
                list(opt_result.weights.values()), req.mu, req.cov, mc_config, hist
            )
            mc_resp = {
                "expected_terminal": mc_result.expected_terminal,
                "median_terminal": mc_result.median_terminal,
                "probability_of_loss": mc_result.probability_of_loss,
                "var_95": mc_result.var_95,
                "cvar_95": mc_result.cvar_95,
                "median_max_drawdown_pct": mc_result.median_max_drawdown_pct,
                "implied_annual_return": mc_result.implied_annual_return,
                "percentile_paths": mc_result.percentile_paths,
            }

        return {
            "optimization": opt_resp,
            "frontier": frontier_resp,
            "attribution": {
                "pct_contributions": attr.pct_contributions,
                "portfolio_volatility": attr.portfolio_volatility,
                "diversification_benefit": attr.diversification_benefit,
                "hhi": attr.hhi,
                "effective_n": attr.effective_n,
            },
            "stress_scenarios": stress_resp,
            "monte_carlo": mc_resp,
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        logger.exception("Full analysis error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Full analysis failed: {exc}")
