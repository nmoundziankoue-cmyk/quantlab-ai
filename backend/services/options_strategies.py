"""M9 Phase 3/4 — Options strategy builder (8 strategies) + analytics.

Strategies: covered_call, protective_put, bull_call_spread, bear_put_spread,
straddle, strangle, iron_condor, butterfly.

All pricing uses Black-Scholes from services/options_analytics.py where available,
with a pure-stdlib fallback.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Pure-stdlib Black-Scholes helpers (no scipy dependency)
# ---------------------------------------------------------------------------

def _erf(x: float) -> float:
    """Abramowitz & Stegun approximation of erf, sufficient for option pricing."""
    sign = 1 if x >= 0 else -1
    x = abs(x)
    t = 1.0 / (1.0 + 0.3275911 * x)
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * math.exp(-x * x)
    return sign * y


def _norm_cdf(x: float) -> float:
    return 0.5 * (1 + _erf(x / math.sqrt(2)))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def bs_call(S: float, K: float, T: float, r: float, sigma: float) -> float:
    if T <= 0:
        return max(0.0, S - K)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)


def bs_put(S: float, K: float, T: float, r: float, sigma: float) -> float:
    if T <= 0:
        return max(0.0, K - S)
    return bs_call(S, K, T, r, sigma) - S + K * math.exp(-r * T)


def bs_greeks(S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call") -> dict:
    if T <= 1e-8:
        return {"delta": 1.0 if option_type == "call" else -1.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    phi_d1 = _norm_pdf(d1)
    Nd1 = _norm_cdf(d1)
    Nd2 = _norm_cdf(d2)
    gamma = phi_d1 / (S * sigma * math.sqrt(T))
    vega = S * phi_d1 * math.sqrt(T) / 100  # per 1% vol change
    if option_type == "call":
        delta = Nd1
        theta = (-S * phi_d1 * sigma / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * Nd2) / 365
        rho = K * T * math.exp(-r * T) * Nd2 / 100
    else:
        delta = Nd1 - 1
        theta = (-S * phi_d1 * sigma / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * _norm_cdf(-d2)) / 365
        rho = -K * T * math.exp(-r * T) * _norm_cdf(-d2) / 100
    return {
        "delta": round(delta, 4),
        "gamma": round(gamma, 6),
        "theta": round(theta, 4),
        "vega": round(vega, 4),
        "rho": round(rho, 4),
    }


# ---------------------------------------------------------------------------
# Binomial tree option pricer
# ---------------------------------------------------------------------------

def binomial_tree(S: float, K: float, T: float, r: float, sigma: float,
                  option_type: str = "call", american: bool = False,
                  steps: int = 100) -> float:
    """Cox-Ross-Rubinstein binomial tree pricing."""
    if T <= 0:
        if option_type == "call":
            return max(0.0, S - K)
        return max(0.0, K - S)

    dt = T / steps
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    q = (math.exp(r * dt) - d) / (u - d)
    disc = math.exp(-r * dt)

    # Terminal payoffs
    payoffs = []
    for j in range(steps + 1):
        ST = S * (u ** (steps - j)) * (d ** j)
        if option_type == "call":
            payoffs.append(max(0.0, ST - K))
        else:
            payoffs.append(max(0.0, K - ST))

    # Backward induction
    for i in range(steps - 1, -1, -1):
        for j in range(i + 1):
            payoffs[j] = disc * (q * payoffs[j] + (1 - q) * payoffs[j + 1])
            if american:
                ST = S * (u ** (i - j)) * (d ** j)
                intrinsic = max(0.0, ST - K) if option_type == "call" else max(0.0, K - ST)
                payoffs[j] = max(payoffs[j], intrinsic)

    return round(payoffs[0], 4)


# ---------------------------------------------------------------------------
# Strategy leg
# ---------------------------------------------------------------------------

@dataclass
class Leg:
    option_type: str        # "call" | "put" | "stock"
    action: str             # "buy" | "sell"
    strike: float
    expiry_T: float
    quantity: int = 1
    premium: float = 0.0    # filled by build_strategy

    def price(self, S: float, r: float, sigma: float) -> float:
        if self.option_type == "stock":
            return S * self.quantity
        fn = bs_call if self.option_type == "call" else bs_put
        return fn(S, self.strike, self.expiry_T, r, sigma) * self.quantity

    def payoff_at_expiry(self, ST: float) -> float:
        if self.option_type == "stock":
            pnl = (ST - self.strike) * self.quantity
        elif self.option_type == "call":
            pnl = max(0.0, ST - self.strike) * self.quantity
        else:
            pnl = max(0.0, self.strike - ST) * self.quantity
        mult = 1 if self.action == "buy" else -1
        return pnl * mult - (self.premium if self.action == "buy" else -self.premium)


# ---------------------------------------------------------------------------
# Strategy definitions
# ---------------------------------------------------------------------------

STRATEGY_REGISTRY: Dict[str, callable] = {}


def _strategy(name: str):
    def dec(fn):
        STRATEGY_REGISTRY[name] = fn
        return fn
    return dec


@_strategy("covered_call")
def covered_call(S: float, K: float, T: float, r: float, sigma: float) -> List[Leg]:
    stock_leg = Leg("stock", "buy", S, T, premium=S)
    short_call = Leg("call", "sell", K, T, premium=bs_call(S, K, T, r, sigma))
    return [stock_leg, short_call]


@_strategy("protective_put")
def protective_put(S: float, K: float, T: float, r: float, sigma: float) -> List[Leg]:
    stock_leg = Leg("stock", "buy", S, T, premium=S)
    long_put = Leg("put", "buy", K, T, premium=bs_put(S, K, T, r, sigma))
    return [stock_leg, long_put]


@_strategy("bull_call_spread")
def bull_call_spread(S: float, K: float, T: float, r: float, sigma: float,
                     K2: Optional[float] = None) -> List[Leg]:
    K2 = K2 or K * 1.05
    return [
        Leg("call", "buy", K, T, premium=bs_call(S, K, T, r, sigma)),
        Leg("call", "sell", K2, T, premium=bs_call(S, K2, T, r, sigma)),
    ]


@_strategy("bear_put_spread")
def bear_put_spread(S: float, K: float, T: float, r: float, sigma: float,
                    K2: Optional[float] = None) -> List[Leg]:
    K2 = K2 or K * 0.95
    return [
        Leg("put", "buy", K, T, premium=bs_put(S, K, T, r, sigma)),
        Leg("put", "sell", K2, T, premium=bs_put(S, K2, T, r, sigma)),
    ]


@_strategy("straddle")
def straddle(S: float, K: float, T: float, r: float, sigma: float) -> List[Leg]:
    return [
        Leg("call", "buy", K, T, premium=bs_call(S, K, T, r, sigma)),
        Leg("put", "buy", K, T, premium=bs_put(S, K, T, r, sigma)),
    ]


@_strategy("strangle")
def strangle(S: float, K: float, T: float, r: float, sigma: float,
             K_put: Optional[float] = None) -> List[Leg]:
    K_put = K_put or K * 0.95
    return [
        Leg("call", "buy", K, T, premium=bs_call(S, K, T, r, sigma)),
        Leg("put", "buy", K_put, T, premium=bs_put(S, K_put, T, r, sigma)),
    ]


@_strategy("iron_condor")
def iron_condor(S: float, K: float, T: float, r: float, sigma: float) -> List[Leg]:
    K_put_low = K * 0.90
    K_put_high = K * 0.95
    K_call_low = K * 1.05
    K_call_high = K * 1.10
    return [
        Leg("put", "buy", K_put_low, T, premium=bs_put(S, K_put_low, T, r, sigma)),
        Leg("put", "sell", K_put_high, T, premium=bs_put(S, K_put_high, T, r, sigma)),
        Leg("call", "sell", K_call_low, T, premium=bs_call(S, K_call_low, T, r, sigma)),
        Leg("call", "buy", K_call_high, T, premium=bs_call(S, K_call_high, T, r, sigma)),
    ]


@_strategy("butterfly")
def butterfly(S: float, K: float, T: float, r: float, sigma: float) -> List[Leg]:
    K_low = K * 0.95
    K_high = K * 1.05
    return [
        Leg("call", "buy", K_low, T, premium=bs_call(S, K_low, T, r, sigma)),
        Leg("call", "sell", K, T, quantity=2, premium=bs_call(S, K, T, r, sigma)),
        Leg("call", "buy", K_high, T, premium=bs_call(S, K_high, T, r, sigma)),
    ]


# ---------------------------------------------------------------------------
# Strategy analyzer
# ---------------------------------------------------------------------------

def build_strategy(
    strategy_name: str,
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    **kwargs,
) -> dict:
    if strategy_name not in STRATEGY_REGISTRY:
        raise ValueError(f"Unknown strategy '{strategy_name}'. Available: {list(STRATEGY_REGISTRY)}")

    # Drop None kwargs so strategies that don't accept optional args aren't broken
    filtered_kwargs = {k: v for k, v in kwargs.items() if v is not None}
    legs = STRATEGY_REGISTRY[strategy_name](S, K, T, r, sigma, **filtered_kwargs)

    # Net debit / credit
    net_cost = sum(
        (l.premium if l.action == "buy" else -l.premium) * l.quantity
        for l in legs
        if l.option_type != "stock"
    )

    # Payoff at a range of spot prices
    spot_range = [S * f for f in [0.70, 0.80, 0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15, 1.20, 1.30]]
    payoff_curve = [
        {"spot": round(st, 2), "payoff": round(sum(l.payoff_at_expiry(st) for l in legs), 4)}
        for st in spot_range
    ]

    # Max profit / loss from payoff curve
    payoffs = [p["payoff"] for p in payoff_curve]
    max_profit = max(payoffs)
    max_loss = min(payoffs)

    # Aggregate greeks
    total_greeks: Dict[str, float] = {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}
    for l in legs:
        if l.option_type == "stock":
            total_greeks["delta"] += (1.0 if l.action == "buy" else -1.0) * l.quantity
        else:
            g = bs_greeks(S, l.strike, l.expiry_T, r, sigma, l.option_type)
            mult = 1 if l.action == "buy" else -1
            for k, v in g.items():
                total_greeks[k] += v * mult * l.quantity

    return {
        "strategy": strategy_name,
        "spot": S,
        "net_cost": round(net_cost, 4),
        "max_profit": round(max_profit, 4),
        "max_loss": round(max_loss, 4),
        "greeks": {k: round(v, 4) for k, v in total_greeks.items()},
        "payoff_curve": payoff_curve,
        "legs": [
            {
                "type": l.option_type,
                "action": l.action,
                "strike": l.strike,
                "expiry_T": l.expiry_T,
                "quantity": l.quantity,
                "premium": round(l.premium, 4),
            }
            for l in legs
        ],
    }


def list_strategies() -> List[str]:
    return list(STRATEGY_REGISTRY.keys())
