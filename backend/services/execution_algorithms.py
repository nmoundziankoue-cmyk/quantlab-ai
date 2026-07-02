"""Execution Algorithms — pure math, no database, no network I/O.

Supported algorithms:
  TWAP  — Time Weighted Average Price: equal slices over equal time intervals
  VWAP  — Volume Weighted Average Price: slices proportional to volume profile
  POV   — Percentage of Volume: maintain target participation rate
  Iceberg — Display small quantity; refill until complete
  Adaptive — Adjust slice size based on remaining quantity and elapsed time
  ArrivalPrice — Minimize market impact relative to arrival price

Each algorithm returns an AlgoSchedule: a list of (slice_index, quantity,
delay_minutes, target_price, label) tuples plus metadata.
"""
from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class AlgoSlice:
    __slots__ = ("slice_index", "quantity", "delay_minutes", "target_price", "label")

    def __init__(
        self,
        slice_index: int,
        quantity: Decimal,
        delay_minutes: float,
        target_price: Optional[Decimal],
        label: str,
    ) -> None:
        self.slice_index = slice_index
        self.quantity = quantity
        self.delay_minutes = delay_minutes
        self.target_price = target_price
        self.label = label

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slice_index": self.slice_index,
            "quantity": self.quantity,
            "delay_minutes": self.delay_minutes,
            "target_price": self.target_price,
            "label": self.label,
        }


def _q(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# TWAP
# ---------------------------------------------------------------------------


def compute_twap(
    ticker: str,
    total_quantity: Decimal,
    duration_minutes: int = 60,
    n_slices: int = 12,
    current_price: Decimal = Decimal("100"),
) -> Dict[str, Any]:
    """Split total_quantity into n_slices equal parts over duration_minutes."""
    if n_slices < 2:
        raise ValueError("n_slices must be >= 2")
    if duration_minutes < 5:
        raise ValueError("duration_minutes must be >= 5")

    slice_duration = duration_minutes / n_slices
    base_qty = (total_quantity / Decimal(n_slices)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    # Remainder goes in the last slice
    remainder = total_quantity - base_qty * Decimal(n_slices - 1)

    schedule: List[AlgoSlice] = []
    for i in range(n_slices):
        qty = remainder if i == n_slices - 1 else base_qty
        delay = slice_duration * i
        schedule.append(AlgoSlice(
            slice_index=i,
            quantity=qty,
            delay_minutes=round(delay, 4),
            target_price=None,
            label=f"TWAP slice {i + 1}/{n_slices}",
        ))

    return {
        "algo": "TWAP",
        "ticker": ticker,
        "total_quantity": total_quantity,
        "total_slices": n_slices,
        "estimated_duration_minutes": float(duration_minutes),
        "schedule": [s.to_dict() for s in schedule],
        "params": {"duration_minutes": duration_minutes, "n_slices": n_slices},
    }


# ---------------------------------------------------------------------------
# VWAP
# ---------------------------------------------------------------------------


def compute_vwap(
    ticker: str,
    total_quantity: Decimal,
    volume_profile: List[float],
    duration_minutes: int = 60,
    current_price: Decimal = Decimal("100"),
) -> Dict[str, Any]:
    """Distribute total_quantity proportionally to a volume profile.

    volume_profile: list of N relative volume weights (e.g. intraday bins).
    """
    n = len(volume_profile)
    if n < 2:
        raise ValueError("volume_profile must have at least 2 elements")

    total_weight = sum(volume_profile)
    if total_weight <= 0:
        raise ValueError("volume_profile weights must sum to > 0")

    slice_duration = duration_minutes / n
    schedule: List[AlgoSlice] = []
    allocated = Decimal("0")

    for i, weight in enumerate(volume_profile):
        frac = Decimal(str(weight / total_weight))
        qty = (total_quantity * frac).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        if i == n - 1:
            qty = total_quantity - allocated  # absorb rounding residual
        else:
            allocated += qty
        schedule.append(AlgoSlice(
            slice_index=i,
            quantity=qty,
            delay_minutes=round(slice_duration * i, 4),
            target_price=None,
            label=f"VWAP slice {i + 1}/{n}",
        ))

    return {
        "algo": "VWAP",
        "ticker": ticker,
        "total_quantity": total_quantity,
        "total_slices": n,
        "estimated_duration_minutes": float(duration_minutes),
        "schedule": [s.to_dict() for s in schedule],
        "params": {"duration_minutes": duration_minutes, "n_slices": n, "profile_bins": n},
    }


# ---------------------------------------------------------------------------
# POV — Percentage of Volume
# ---------------------------------------------------------------------------


def compute_pov(
    ticker: str,
    total_quantity: Decimal,
    participation_rate: float = 0.10,
    avg_volume_per_minute: float = 10_000.0,
    current_price: Decimal = Decimal("100"),
) -> Dict[str, Any]:
    """Generate a POV schedule where each slice participates at `participation_rate`
    of the expected market volume per minute.
    """
    if participation_rate <= 0 or participation_rate > 0.50:
        raise ValueError("participation_rate must be in (0, 0.50]")
    if avg_volume_per_minute <= 0:
        raise ValueError("avg_volume_per_minute must be > 0")

    qty_per_minute = Decimal(str(avg_volume_per_minute * participation_rate))
    total_minutes = math.ceil(float(total_quantity) / float(qty_per_minute))
    total_minutes = max(total_minutes, 1)

    schedule: List[AlgoSlice] = []
    remaining = total_quantity
    for i in range(total_minutes):
        slice_qty = min(qty_per_minute, remaining).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        schedule.append(AlgoSlice(
            slice_index=i,
            quantity=slice_qty,
            delay_minutes=float(i),
            target_price=None,
            label=f"POV min {i + 1} ({participation_rate * 100:.0f}% of volume)",
        ))
        remaining -= slice_qty
        if remaining <= 0:
            break

    return {
        "algo": "POV",
        "ticker": ticker,
        "total_quantity": total_quantity,
        "total_slices": len(schedule),
        "estimated_duration_minutes": float(total_minutes),
        "schedule": [s.to_dict() for s in schedule],
        "params": {
            "participation_rate": participation_rate,
            "avg_volume_per_minute": avg_volume_per_minute,
        },
    }


# ---------------------------------------------------------------------------
# Iceberg
# ---------------------------------------------------------------------------


def compute_iceberg(
    ticker: str,
    total_quantity: Decimal,
    display_quantity: Decimal,
    limit_price: Decimal,
    refill_delay_minutes: float = 1.0,
) -> Dict[str, Any]:
    """Schedule iceberg slices.

    Only display_quantity is visible to the market at any time.
    When a display slice fills, a new one is placed after refill_delay_minutes.
    """
    if display_quantity >= total_quantity:
        raise ValueError("display_quantity must be less than total_quantity")
    if display_quantity <= 0:
        raise ValueError("display_quantity must be > 0")

    n_full = int(total_quantity // display_quantity)
    remainder = total_quantity - display_quantity * Decimal(n_full)
    n_slices = n_full + (1 if remainder > 0 else 0)

    schedule: List[AlgoSlice] = []
    for i in range(n_slices):
        qty = display_quantity if i < n_full else remainder
        schedule.append(AlgoSlice(
            slice_index=i,
            quantity=qty,
            delay_minutes=round(refill_delay_minutes * i, 4),
            target_price=limit_price,
            label=f"Iceberg refill {i + 1}/{n_slices} (display {display_quantity})",
        ))

    total_duration = refill_delay_minutes * (n_slices - 1)

    return {
        "algo": "ICEBERG",
        "ticker": ticker,
        "total_quantity": total_quantity,
        "total_slices": n_slices,
        "estimated_duration_minutes": total_duration,
        "schedule": [s.to_dict() for s in schedule],
        "params": {
            "display_quantity": display_quantity,
            "limit_price": limit_price,
            "refill_delay_minutes": refill_delay_minutes,
        },
    }


# ---------------------------------------------------------------------------
# Adaptive
# ---------------------------------------------------------------------------


def compute_adaptive(
    ticker: str,
    total_quantity: Decimal,
    duration_minutes: int = 60,
    urgency: float = 0.5,
    current_price: Decimal = Decimal("100"),
) -> Dict[str, Any]:
    """Adaptive algorithm: front-loads or back-loads based on urgency.

    urgency in [0, 1]:
      0.0 = fully back-loaded (minimize impact, execute at end)
      0.5 = balanced (similar to TWAP)
      1.0 = fully front-loaded (minimize timing risk, execute at start)

    Uses a power law: weight(t) ∝ t^exponent where:
      exponent < 1 → front-loaded
      exponent > 1 → back-loaded
    """
    if not 0.0 <= urgency <= 1.0:
        raise ValueError("urgency must be in [0, 1]")

    n_slices = max(10, duration_minutes // 5)
    slice_duration = duration_minutes / n_slices

    # exponent: 0.2 (front) → 5.0 (back)
    exponent = 5.0 * (1.0 - urgency) + 0.2 * urgency

    weights = [(i + 1) ** exponent for i in range(n_slices)]
    if urgency >= 0.5:
        # Front-load: reverse so earlier slices get more
        weights = list(reversed(weights))

    total_weight = sum(weights)
    schedule: List[AlgoSlice] = []
    allocated = Decimal("0")

    for i, w in enumerate(weights):
        frac = Decimal(str(w / total_weight))
        qty = (total_quantity * frac).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        if i == n_slices - 1:
            qty = total_quantity - allocated
        else:
            allocated += qty
        schedule.append(AlgoSlice(
            slice_index=i,
            quantity=qty,
            delay_minutes=round(slice_duration * i, 4),
            target_price=None,
            label=f"Adaptive slice {i + 1}/{n_slices}",
        ))

    return {
        "algo": "ADAPTIVE",
        "ticker": ticker,
        "total_quantity": total_quantity,
        "total_slices": n_slices,
        "estimated_duration_minutes": float(duration_minutes),
        "schedule": [s.to_dict() for s in schedule],
        "params": {"duration_minutes": duration_minutes, "urgency": urgency, "exponent": exponent},
    }


# ---------------------------------------------------------------------------
# Arrival Price / Implementation Shortfall
# ---------------------------------------------------------------------------


def compute_arrival_price(
    ticker: str,
    total_quantity: Decimal,
    arrival_price: Decimal,
    duration_minutes: int = 30,
    volatility_daily: float = 0.02,
    spread_bps: float = 5.0,
) -> Dict[str, Any]:
    """Implementation Shortfall / Arrival Price minimizer.

    Balances timing risk (volatility × time) against market impact (sqrt of qty).
    Optimal trade rate is front-loaded to reduce timing risk exposure.

    The analytic solution under Almgren-Chriss (simplified) is an exponential
    decay in trade rate:
      x(t) = X * λ * exp(-λ * t)
    where λ controls front-loading aggressiveness based on risk aversion.

    Here we use a discrete approximation with 5-minute slices.
    """
    if duration_minutes < 5:
        raise ValueError("duration_minutes must be >= 5")

    n_slices = max(1, duration_minutes // 5)
    slice_duration = duration_minutes / n_slices

    # Risk aversion parameter: higher vol → higher λ → more front-loading
    lambda_param = volatility_daily * math.sqrt(1.0 / 252.0) * 10  # scaled

    # Exponential weights
    weights = [math.exp(-lambda_param * i) for i in range(n_slices)]
    total_weight = sum(weights)

    schedule: List[AlgoSlice] = []
    allocated = Decimal("0")
    for i, w in enumerate(weights):
        frac = Decimal(str(w / total_weight))
        qty = (total_quantity * frac).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        if i == n_slices - 1:
            qty = total_quantity - allocated
        else:
            allocated += qty
        schedule.append(AlgoSlice(
            slice_index=i,
            quantity=qty,
            delay_minutes=round(slice_duration * i, 4),
            target_price=arrival_price,
            label=f"IS slice {i + 1}/{n_slices}",
        ))

    return {
        "algo": "ARRIVAL_PRICE",
        "ticker": ticker,
        "total_quantity": total_quantity,
        "total_slices": n_slices,
        "estimated_duration_minutes": float(duration_minutes),
        "schedule": [s.to_dict() for s in schedule],
        "params": {
            "arrival_price": arrival_price,
            "duration_minutes": duration_minutes,
            "volatility_daily": volatility_daily,
            "spread_bps": spread_bps,
            "lambda_param": lambda_param,
        },
    }


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

ALGO_FUNCTIONS = {
    "TWAP": compute_twap,
    "VWAP": compute_vwap,
    "POV": compute_pov,
    "ICEBERG": compute_iceberg,
    "ADAPTIVE": compute_adaptive,
    "ARRIVAL_PRICE": compute_arrival_price,
}


def run_algorithm(algo: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch to the appropriate algorithm function."""
    fn = ALGO_FUNCTIONS.get(algo.upper())
    if fn is None:
        raise ValueError(f"Unknown execution algorithm: {algo}. Available: {list(ALGO_FUNCTIONS)}")
    return fn(**params)
