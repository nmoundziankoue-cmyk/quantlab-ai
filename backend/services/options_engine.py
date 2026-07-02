"""M16 Phase 6 — Options Analytics Engine.

Pure Python Black-Scholes Greeks, IV estimation, IV rank/percentile,
max pain, gamma exposure, and options chain analytics.
No scipy or external libraries.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Pure Python normal distribution (Abramowitz & Stegun approximation)
# ---------------------------------------------------------------------------

def _norm_pdf(x: float) -> float:
    """Standard normal probability density function."""
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def _norm_cdf(x: float) -> float:
    """Standard normal CDF via A&S rational approximation (error < 7.5e-8)."""
    sign = 1.0 if x >= 0 else -1.0
    x = abs(x)
    t = 1.0 / (1.0 + 0.2316419 * x)
    poly = t * (0.319381530
                + t * (-0.356563782
                       + t * (1.781477937
                              + t * (-1.821255978
                                     + t * 1.330274429))))
    cdf = 1.0 - _norm_pdf(x) * poly
    return cdf if sign > 0 else 1.0 - cdf


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class OptionType(str, Enum):
    CALL = "call"
    PUT = "put"


class OptionStyle(str, Enum):
    EUROPEAN = "european"
    AMERICAN = "american"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class OptionSpec:
    """Specification for a single option contract.

    Attributes:
        ticker: Underlying ticker.
        option_type: Call or put.
        strike: Strike price.
        expiry_years: Time to expiry in years.
        style: European or American.
        multiplier: Contract multiplier (default 100).
        open_interest: Open interest in contracts.
        volume: Daily trading volume.
    """
    ticker: str
    option_type: OptionType
    strike: float
    expiry_years: float
    style: OptionStyle = OptionStyle.EUROPEAN
    multiplier: int = 100
    open_interest: int = 0
    volume: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "ticker": self.ticker,
            "option_type": self.option_type.value,
            "strike": self.strike,
            "expiry_years": self.expiry_years,
            "style": self.style.value,
            "multiplier": self.multiplier,
            "open_interest": self.open_interest,
            "volume": self.volume,
        }


@dataclass
class Greeks:
    """Black-Scholes Greeks for a single option.

    Attributes:
        delta: Rate of price change vs underlying.
        gamma: Rate of delta change vs underlying.
        theta: Daily time decay.
        vega: Sensitivity to 1% change in IV.
        rho: Sensitivity to 1% change in risk-free rate.
        vanna: Cross-partial ∂²V / ∂S∂σ.
        charm: Daily decay of delta (∂²V / ∂S∂t).
    """
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    vanna: float
    charm: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "delta": round(self.delta, 6),
            "gamma": round(self.gamma, 6),
            "theta": round(self.theta, 6),
            "vega": round(self.vega, 6),
            "rho": round(self.rho, 6),
            "vanna": round(self.vanna, 6),
            "charm": round(self.charm, 6),
        }


@dataclass
class OptionAnalytics:
    """Full analytics for a single option.

    Attributes:
        spec: Original OptionSpec.
        underlying_price: Current spot price.
        iv: Implied volatility.
        theoretical_price: BS theoretical price.
        greeks: Greeks dataclass.
        intrinsic_value: Max(0, S-K) for call / Max(0, K-S) for put.
        time_value: Price minus intrinsic.
        moneyness: S/K for call, K/S for put.
        is_itm: Whether the option is in the money.
    """
    spec: OptionSpec
    underlying_price: float
    iv: float
    theoretical_price: float
    greeks: Greeks
    intrinsic_value: float
    time_value: float
    moneyness: float
    is_itm: bool

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "spec": self.spec.to_dict(),
            "underlying_price": self.underlying_price,
            "iv": round(self.iv, 6),
            "theoretical_price": round(self.theoretical_price, 6),
            "greeks": self.greeks.to_dict(),
            "intrinsic_value": round(self.intrinsic_value, 6),
            "time_value": round(self.time_value, 6),
            "moneyness": round(self.moneyness, 6),
            "is_itm": self.is_itm,
        }


@dataclass
class IVSurface:
    """Implied volatility surface for a single underlying.

    Attributes:
        ticker: Underlying ticker.
        strikes: Strike price list.
        expiries: Expiry (years) list.
        iv_matrix: iv_matrix[i][j] = IV at strike i, expiry j.
        atm_iv: At-the-money IV for each expiry.
        term_structure: Dict expiry_label -> ATM IV.
    """
    ticker: str
    strikes: List[float]
    expiries: List[float]
    iv_matrix: List[List[float]]
    atm_iv: List[float]
    term_structure: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "ticker": self.ticker,
            "strikes": self.strikes,
            "expiries": self.expiries,
            "iv_matrix": [[round(v, 6) for v in row] for row in self.iv_matrix],
            "atm_iv": [round(v, 6) for v in self.atm_iv],
            "term_structure": {k: round(v, 6) for k, v in self.term_structure.items()},
        }


@dataclass
class MaxPainResult:
    """Max pain analysis — strike where total option value is minimised.

    Attributes:
        ticker: Underlying ticker.
        expiry_years: Expiry analysed.
        max_pain_strike: Strike at maximum pain (minimum total pain for writer).
        total_pain_by_strike: Dict strike -> total pain value.
        call_pain_by_strike: Dict strike -> call pain.
        put_pain_by_strike: Dict strike -> put pain.
    """
    ticker: str
    expiry_years: float
    max_pain_strike: float
    total_pain_by_strike: Dict[float, float]
    call_pain_by_strike: Dict[float, float]
    put_pain_by_strike: Dict[float, float]

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "ticker": self.ticker,
            "expiry_years": self.expiry_years,
            "max_pain_strike": self.max_pain_strike,
            "total_pain_by_strike": {str(k): round(v, 2) for k, v in self.total_pain_by_strike.items()},
        }


@dataclass
class GammaExposure:
    """Dealer gamma exposure at a given underlying price.

    Attributes:
        ticker: Underlying ticker.
        underlying_price: Spot price.
        net_gamma_exposure: Dollar gamma (positive = long gamma).
        call_gamma: Gamma from call positions.
        put_gamma: Gamma from put positions.
        gamma_by_strike: Dict strike -> net gamma exposure.
        flip_point: Strike where net gamma crosses zero (approx).
    """
    ticker: str
    underlying_price: float
    net_gamma_exposure: float
    call_gamma: float
    put_gamma: float
    gamma_by_strike: Dict[float, float]
    flip_point: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "ticker": self.ticker,
            "underlying_price": self.underlying_price,
            "net_gamma_exposure": round(self.net_gamma_exposure, 2),
            "call_gamma": round(self.call_gamma, 2),
            "put_gamma": round(self.put_gamma, 2),
            "gamma_by_strike": {str(k): round(v, 2) for k, v in self.gamma_by_strike.items()},
            "flip_point": self.flip_point,
        }


# ---------------------------------------------------------------------------
# OptionsEngine
# ---------------------------------------------------------------------------

class OptionsEngine:
    """Pure Python Options Analytics Engine.

    Implements Black-Scholes pricing and Greeks, implied volatility
    via bisection, IV rank/percentile, max pain, and gamma exposure.
    No scipy or external numerical libraries.
    """

    # ------------------------------------------------------------------
    # Black-Scholes core
    # ------------------------------------------------------------------

    def _d1_d2(
        self, S: float, K: float, T: float, r: float, sigma: float
    ) -> Tuple[float, float]:
        """Compute d1 and d2 for Black-Scholes.

        Args:
            S: Spot price.
            K: Strike price.
            T: Time to expiry in years.
            r: Risk-free rate.
            sigma: Implied volatility.

        Returns:
            (d1, d2) tuple.
        """
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
            return 0.0, 0.0
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        return d1, d2

    def bs_price(
        self,
        S: float,
        K: float,
        T: float,
        r: float,
        sigma: float,
        option_type: OptionType,
    ) -> float:
        """Black-Scholes option price.

        Args:
            S: Spot price.
            K: Strike.
            T: Time to expiry (years).
            r: Risk-free rate.
            sigma: Volatility.
            option_type: Call or put.

        Returns:
            Theoretical option price.
        """
        if T <= 0:
            if option_type == OptionType.CALL:
                return max(0.0, S - K)
            return max(0.0, K - S)
        d1, d2 = self._d1_d2(S, K, T, r, sigma)
        disc = math.exp(-r * T)
        if option_type == OptionType.CALL:
            return round(S * _norm_cdf(d1) - K * disc * _norm_cdf(d2), 6)
        return round(K * disc * _norm_cdf(-d2) - S * _norm_cdf(-d1), 6)

    def bs_greeks(
        self,
        S: float,
        K: float,
        T: float,
        r: float,
        sigma: float,
        option_type: OptionType,
    ) -> Greeks:
        """Compute full set of BS Greeks.

        Args:
            S: Spot price.
            K: Strike.
            T: Time to expiry (years).
            r: Risk-free rate.
            sigma: Volatility.
            option_type: Call or put.

        Returns:
            Greeks dataclass.
        """
        if T <= 0 or sigma <= 0:
            sgn = 1.0 if option_type == OptionType.CALL else -1.0
            itm = (S > K) if option_type == OptionType.CALL else (K > S)
            return Greeks(
                delta=sgn if itm else 0.0,
                gamma=0.0, theta=0.0, vega=0.0, rho=0.0, vanna=0.0, charm=0.0
            )
        d1, d2 = self._d1_d2(S, K, T, r, sigma)
        sqrt_T = math.sqrt(T)
        pdf_d1 = _norm_pdf(d1)
        disc = math.exp(-r * T)

        # Delta
        if option_type == OptionType.CALL:
            delta = _norm_cdf(d1)
        else:
            delta = _norm_cdf(d1) - 1.0

        # Gamma (same for call and put)
        gamma = pdf_d1 / (S * sigma * sqrt_T)

        # Theta (per day)
        theta_common = -(S * pdf_d1 * sigma) / (2 * sqrt_T)
        if option_type == OptionType.CALL:
            theta = (theta_common - r * K * disc * _norm_cdf(d2)) / 365
        else:
            theta = (theta_common + r * K * disc * _norm_cdf(-d2)) / 365

        # Vega (per 1% move in vol)
        vega = S * pdf_d1 * sqrt_T / 100

        # Rho (per 1% move in rate)
        if option_type == OptionType.CALL:
            rho = K * T * disc * _norm_cdf(d2) / 100
        else:
            rho = -K * T * disc * _norm_cdf(-d2) / 100

        # Vanna = ∂delta/∂sigma = vega/S × (1 - d1/(sigma√T))
        if sigma * sqrt_T != 0:
            vanna = (vega * 100 / S) * (1 - d1 / (sigma * sqrt_T))
        else:
            vanna = 0.0

        # Charm = ∂delta/∂t (daily)
        if T > 0:
            if option_type == OptionType.CALL:
                charm = -pdf_d1 * (2 * r * T - d2 * sigma * sqrt_T) / (2 * T * sigma * sqrt_T) / 365
            else:
                charm = -pdf_d1 * (2 * r * T - d2 * sigma * sqrt_T) / (2 * T * sigma * sqrt_T) / 365
        else:
            charm = 0.0

        return Greeks(
            delta=round(delta, 6),
            gamma=round(gamma, 6),
            theta=round(theta, 6),
            vega=round(vega, 6),
            rho=round(rho, 6),
            vanna=round(vanna, 6),
            charm=round(charm, 6),
        )

    # ------------------------------------------------------------------
    # Implied Volatility via bisection
    # ------------------------------------------------------------------

    def implied_volatility(
        self,
        market_price: float,
        S: float,
        K: float,
        T: float,
        r: float,
        option_type: OptionType,
        tol: float = 1e-6,
        max_iter: int = 200,
    ) -> float:
        """Compute implied volatility via bisection.

        Args:
            market_price: Observed option market price.
            S: Spot price.
            K: Strike.
            T: Time to expiry (years).
            r: Risk-free rate.
            option_type: Call or put.
            tol: Convergence tolerance.
            max_iter: Maximum iterations.

        Returns:
            Implied volatility as annual fraction.
        """
        lo, hi = 1e-6, 10.0
        for _ in range(max_iter):
            mid = (lo + hi) / 2
            p = self.bs_price(S, K, T, r, mid, option_type)
            if abs(p - market_price) < tol:
                return round(mid, 6)
            if p < market_price:
                lo = mid
            else:
                hi = mid
        return round((lo + hi) / 2, 6)

    # ------------------------------------------------------------------
    # IV Rank / Percentile
    # ------------------------------------------------------------------

    def iv_rank(self, current_iv: float, iv_history: List[float]) -> float:
        """IV Rank: (current - 52w_low) / (52w_high - 52w_low).

        Args:
            current_iv: Current implied volatility.
            iv_history: Historical IV values (52-week window).

        Returns:
            IV Rank in [0, 100].
        """
        if not iv_history:
            return 50.0
        lo, hi = min(iv_history), max(iv_history)
        if hi == lo:
            return 50.0
        return round(100 * (current_iv - lo) / (hi - lo), 2)

    def iv_percentile(self, current_iv: float, iv_history: List[float]) -> float:
        """IV Percentile: fraction of history below current IV.

        Args:
            current_iv: Current implied volatility.
            iv_history: Historical IV values.

        Returns:
            IV Percentile in [0, 100].
        """
        if not iv_history:
            return 50.0
        below = sum(1 for v in iv_history if v < current_iv)
        return round(100 * below / len(iv_history), 2)

    # ------------------------------------------------------------------
    # Full analytics for a single option
    # ------------------------------------------------------------------

    def analyze(
        self,
        spec: OptionSpec,
        underlying_price: float,
        iv: float,
        risk_free_rate: float = 0.0,
    ) -> OptionAnalytics:
        """Compute full analytics for a single option.

        Args:
            spec: OptionSpec.
            underlying_price: Current spot price.
            iv: Implied volatility to use.
            risk_free_rate: Risk-free rate.

        Returns:
            OptionAnalytics.
        """
        S, K, T, r, sigma = underlying_price, spec.strike, spec.expiry_years, risk_free_rate, iv
        th_price = self.bs_price(S, K, T, r, sigma, spec.option_type)
        greeks = self.bs_greeks(S, K, T, r, sigma, spec.option_type)

        if spec.option_type == OptionType.CALL:
            intrinsic = max(0.0, S - K)
            moneyness = S / K
            is_itm = S > K
        else:
            intrinsic = max(0.0, K - S)
            moneyness = K / S
            is_itm = K > S
        time_value = max(0.0, th_price - intrinsic)

        return OptionAnalytics(
            spec=spec,
            underlying_price=S,
            iv=iv,
            theoretical_price=th_price,
            greeks=greeks,
            intrinsic_value=round(intrinsic, 6),
            time_value=round(time_value, 6),
            moneyness=round(moneyness, 6),
            is_itm=is_itm,
        )

    # ------------------------------------------------------------------
    # Max Pain
    # ------------------------------------------------------------------

    def max_pain(
        self,
        ticker: str,
        expiry_years: float,
        calls: List[OptionSpec],
        puts: List[OptionSpec],
    ) -> MaxPainResult:
        """Compute max pain strike for a given expiry.

        Max pain = strike where total writer's pain (total intrinsic value of
        all in-the-money options at expiry) is minimised.

        Args:
            ticker: Underlying ticker.
            expiry_years: Target expiry.
            calls: List of call OptionSpec with open_interest populated.
            puts: List of put OptionSpec with open_interest populated.

        Returns:
            MaxPainResult with per-strike pain values.
        """
        all_strikes = sorted(set(o.strike for o in calls + puts))
        call_pain: Dict[float, float] = {}
        put_pain: Dict[float, float] = {}
        total_pain: Dict[float, float] = {}

        for S in all_strikes:
            cp = sum(max(0.0, S - c.strike) * c.open_interest * c.multiplier
                     for c in calls)
            pp = sum(max(0.0, p.strike - S) * p.open_interest * p.multiplier
                     for p in puts)
            call_pain[S] = round(cp, 2)
            put_pain[S] = round(pp, 2)
            total_pain[S] = round(cp + pp, 2)

        if not total_pain:
            return MaxPainResult(
                ticker=ticker, expiry_years=expiry_years, max_pain_strike=0.0,
                total_pain_by_strike={}, call_pain_by_strike={}, put_pain_by_strike={}
            )

        mp_strike = min(total_pain, key=lambda s: total_pain[s])
        return MaxPainResult(
            ticker=ticker,
            expiry_years=expiry_years,
            max_pain_strike=mp_strike,
            total_pain_by_strike=total_pain,
            call_pain_by_strike=call_pain,
            put_pain_by_strike=put_pain,
        )

    # ------------------------------------------------------------------
    # Gamma Exposure
    # ------------------------------------------------------------------

    def gamma_exposure(
        self,
        ticker: str,
        underlying_price: float,
        calls: List[OptionSpec],
        puts: List[OptionSpec],
        iv_map: Dict[float, float],
        risk_free_rate: float = 0.0,
    ) -> GammaExposure:
        """Compute net dealer gamma exposure (GEX) across all strikes.

        Assumes dealers are short calls and long puts (typical MM position).
        Dollar gamma = gamma × OI × multiplier × S².

        Args:
            ticker: Underlying ticker.
            underlying_price: Spot price.
            calls: Call option specs.
            puts: Put option specs.
            iv_map: Dict mapping strike -> IV (shared for calls/puts at same strike).
            risk_free_rate: Risk-free rate.

        Returns:
            GammaExposure with net GEX and per-strike breakdown.
        """
        S = underlying_price
        gex_by_strike: Dict[float, float] = {}
        total_call_gamma = 0.0
        total_put_gamma = 0.0

        for opt in calls:
            iv = iv_map.get(opt.strike, 0.3)
            g = self.bs_greeks(S, opt.strike, opt.expiry_years, risk_free_rate, iv, OptionType.CALL)
            dollar_gamma = g.gamma * opt.open_interest * opt.multiplier * S * S / 100
            gex_by_strike[opt.strike] = gex_by_strike.get(opt.strike, 0.0) + dollar_gamma
            total_call_gamma += dollar_gamma

        for opt in puts:
            iv = iv_map.get(opt.strike, 0.3)
            g = self.bs_greeks(S, opt.strike, opt.expiry_years, risk_free_rate, iv, OptionType.PUT)
            dollar_gamma = -g.gamma * opt.open_interest * opt.multiplier * S * S / 100
            gex_by_strike[opt.strike] = gex_by_strike.get(opt.strike, 0.0) + dollar_gamma
            total_put_gamma += dollar_gamma

        net_gex = total_call_gamma + total_put_gamma

        # Find gamma flip point (zero crossing in sorted strikes)
        sorted_strikes = sorted(gex_by_strike)
        flip = None
        for i in range(len(sorted_strikes) - 1):
            g1 = gex_by_strike[sorted_strikes[i]]
            g2 = gex_by_strike[sorted_strikes[i + 1]]
            if g1 * g2 < 0:
                flip = round((sorted_strikes[i] + sorted_strikes[i + 1]) / 2, 2)
                break

        return GammaExposure(
            ticker=ticker,
            underlying_price=S,
            net_gamma_exposure=round(net_gex, 2),
            call_gamma=round(total_call_gamma, 2),
            put_gamma=round(total_put_gamma, 2),
            gamma_by_strike={k: round(v, 2) for k, v in gex_by_strike.items()},
            flip_point=flip,
        )

    # ------------------------------------------------------------------
    # IV Surface
    # ------------------------------------------------------------------

    def build_iv_surface(
        self,
        ticker: str,
        market_prices: Dict[Tuple[float, float], Tuple[float, OptionType]],
        S: float,
        r: float = 0.0,
    ) -> IVSurface:
        """Build an IV surface from market option prices.

        Args:
            ticker: Underlying ticker.
            market_prices: Dict mapping (strike, expiry) -> (market_price, OptionType).
            S: Spot price.
            r: Risk-free rate.

        Returns:
            IVSurface with per-strike-expiry IVs.
        """
        strikes_set = sorted(set(k for k, _ in market_prices))
        expiries_set = sorted(set(e for _, e in market_prices))

        iv_mat = []
        for K in strikes_set:
            row = []
            for T in expiries_set:
                mp, opt_type = market_prices.get((K, T), (0.0, OptionType.CALL))
                if mp <= 0 or T <= 0:
                    row.append(0.0)
                else:
                    iv = self.implied_volatility(mp, S, K, T, r, opt_type)
                    row.append(iv)
            iv_mat.append(row)

        # ATM IVs: pick strike closest to S for each expiry
        atm_iv = []
        for j, T in enumerate(expiries_set):
            closest_k = min(strikes_set, key=lambda k: abs(k - S))
            idx = strikes_set.index(closest_k)
            atm_iv.append(iv_mat[idx][j])

        term_structure = {}
        for j, T in enumerate(expiries_set):
            label = f"{round(T * 12)}M" if T < 1 else f"{round(T)}Y"
            term_structure[label] = atm_iv[j]

        return IVSurface(
            ticker=ticker,
            strikes=strikes_set,
            expiries=expiries_set,
            iv_matrix=iv_mat,
            atm_iv=atm_iv,
            term_structure=term_structure,
        )

    # ------------------------------------------------------------------
    # Put-Call Ratio
    # ------------------------------------------------------------------

    def put_call_ratio(
        self,
        calls: List[OptionSpec],
        puts: List[OptionSpec],
        by: str = "volume",
    ) -> float:
        """Compute put-call ratio by volume or open interest.

        Args:
            calls: List of call OptionSpec.
            puts: List of put OptionSpec.
            by: 'volume' or 'open_interest'.

        Returns:
            Put-call ratio.
        """
        if by == "open_interest":
            call_total = sum(o.open_interest for o in calls)
            put_total = sum(o.open_interest for o in puts)
        else:
            call_total = sum(o.volume for o in calls)
            put_total = sum(o.volume for o in puts)
        return round(put_total / call_total, 4) if call_total > 0 else 0.0


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_options_engine: Optional[OptionsEngine] = None


def get_options_engine() -> OptionsEngine:
    """Return the singleton OptionsEngine instance.

    Returns:
        Shared OptionsEngine instance.
    """
    global _default_options_engine
    if _default_options_engine is None:
        _default_options_engine = OptionsEngine()
    return _default_options_engine
