"""M16 Phase 5 — Bond Analytics Engine.

Duration, modified duration, convexity, yield-to-maturity, DV01, spread
analysis, and yield/credit bucket classification — pure Python, in-memory.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class BondType(str, Enum):
    GOVERNMENT = "government"
    CORPORATE = "corporate"
    MUNICIPAL = "municipal"
    AGENCY = "agency"
    CONVERTIBLE = "convertible"
    HIGH_YIELD = "high_yield"
    INFLATION_LINKED = "inflation_linked"


class YieldBucket(str, Enum):
    VERY_LOW = "very_low"       # < 2%
    LOW = "low"                  # 2–3%
    MODERATE = "moderate"        # 3–4%
    HIGH = "high"                # 4–6%
    VERY_HIGH = "very_high"      # > 6%


class CreditBucket(str, Enum):
    AAA = "AAA"
    AA = "AA"
    A = "A"
    BBB = "BBB"
    BB = "BB"
    B = "B"
    CCC_AND_BELOW = "CCC_and_below"
    NOT_RATED = "not_rated"


class MaturityBucket(str, Enum):
    SHORT = "short"        # 0–2 years
    MEDIUM = "medium"      # 2–7 years
    LONG = "long"          # 7–15 years
    ULTRA_LONG = "ultra_long"  # > 15 years


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class BondSpec:
    """Specification of a fixed-income instrument.

    Attributes:
        isin: ISIN identifier.
        ticker: Optional issuer ticker.
        face_value: Par / face value.
        coupon_rate: Annual coupon rate as fraction (e.g. 0.05 = 5%).
        coupon_frequency: Number of coupon payments per year.
        maturity_years: Years to maturity from today.
        bond_type: Bond classification.
        credit_rating: Moody's/S&P style rating string.
        callable: Whether the bond is callable.
    """
    isin: str
    ticker: str
    face_value: float
    coupon_rate: float
    coupon_frequency: int
    maturity_years: float
    bond_type: BondType
    credit_rating: str = "BBB"
    callable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "isin": self.isin,
            "ticker": self.ticker,
            "face_value": self.face_value,
            "coupon_rate": self.coupon_rate,
            "coupon_frequency": self.coupon_frequency,
            "maturity_years": self.maturity_years,
            "bond_type": self.bond_type.value,
            "credit_rating": self.credit_rating,
            "callable": self.callable,
        }


@dataclass
class BondAnalytics:
    """Comprehensive analytics for a single bond.

    Attributes:
        isin: ISIN identifier.
        price: Clean price.
        ytm: Yield to maturity.
        duration: Macaulay duration in years.
        modified_duration: Modified duration.
        convexity: Convexity.
        dv01: Dollar value of a 1bp shift (per 100 face).
        spread: Yield spread over risk-free rate.
        accrued_interest: Accrued coupon since last payment.
        dirty_price: Clean price + accrued interest.
        yield_bucket: YieldBucket classification.
        credit_bucket: CreditBucket classification.
        maturity_bucket: MaturityBucket classification.
    """
    isin: str
    price: float
    ytm: float
    duration: float
    modified_duration: float
    convexity: float
    dv01: float
    spread: float
    accrued_interest: float
    dirty_price: float
    yield_bucket: YieldBucket
    credit_bucket: CreditBucket
    maturity_bucket: MaturityBucket

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "isin": self.isin,
            "price": round(self.price, 6),
            "ytm": round(self.ytm, 6),
            "duration": round(self.duration, 6),
            "modified_duration": round(self.modified_duration, 6),
            "convexity": round(self.convexity, 6),
            "dv01": round(self.dv01, 6),
            "spread": round(self.spread, 6),
            "accrued_interest": round(self.accrued_interest, 6),
            "dirty_price": round(self.dirty_price, 6),
            "yield_bucket": self.yield_bucket.value,
            "credit_bucket": self.credit_bucket.value,
            "maturity_bucket": self.maturity_bucket.value,
        }


@dataclass
class YieldCurvePoint:
    """A single point on a yield curve.

    Attributes:
        maturity_years: Time to maturity.
        yield_rate: Annualised yield.
        label: Human-readable label (e.g. '10Y').
    """
    maturity_years: float
    yield_rate: float
    label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "maturity_years": self.maturity_years,
            "yield_rate": round(self.yield_rate, 6),
            "label": self.label,
        }


@dataclass
class YieldCurve:
    """Interpolatable yield curve.

    Attributes:
        name: Curve name (e.g. 'US Treasury').
        points: Sorted list of YieldCurvePoint.
        as_of: Date string.
    """
    name: str
    points: List[YieldCurvePoint] = field(default_factory=list)
    as_of: str = ""

    def interpolate(self, maturity_years: float) -> float:
        """Linear interpolation for a target maturity.

        Args:
            maturity_years: Target maturity in years.

        Returns:
            Interpolated yield rate.
        """
        pts = sorted(self.points, key=lambda p: p.maturity_years)
        if not pts:
            return 0.0
        if maturity_years <= pts[0].maturity_years:
            return pts[0].yield_rate
        if maturity_years >= pts[-1].maturity_years:
            return pts[-1].yield_rate
        for i in range(len(pts) - 1):
            if pts[i].maturity_years <= maturity_years <= pts[i + 1].maturity_years:
                t0, t1 = pts[i].maturity_years, pts[i + 1].maturity_years
                y0, y1 = pts[i].yield_rate, pts[i + 1].yield_rate
                frac = (maturity_years - t0) / (t1 - t0)
                return round(y0 + frac * (y1 - y0), 6)
        return pts[-1].yield_rate

    def spread(self) -> float:
        """Yield spread between longest and shortest point.

        Returns:
            Spread in rate units.
        """
        pts = sorted(self.points, key=lambda p: p.maturity_years)
        if len(pts) < 2:
            return 0.0
        return round(pts[-1].yield_rate - pts[0].yield_rate, 6)

    def is_inverted(self) -> bool:
        """Whether the curve is inverted (short > long yield).

        Returns:
            True if spread is negative.
        """
        return self.spread() < 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "name": self.name,
            "points": [p.to_dict() for p in self.points],
            "as_of": self.as_of,
            "spread": self.spread(),
            "inverted": self.is_inverted(),
        }


# ---------------------------------------------------------------------------
# BondEngine
# ---------------------------------------------------------------------------

class BondEngine:
    """Bond Analytics Engine.

    Computes bond pricing, duration, convexity, DV01, YTM, spreads, and
    yield curve operations using pure Python.
    """

    # ------------------------------------------------------------------
    # Present value of cash flows
    # ------------------------------------------------------------------

    def _cash_flows(self, bond: BondSpec) -> List[Tuple[float, float]]:
        """Generate (time_years, cash_flow) tuples for a bond.

        Args:
            bond: BondSpec to generate cash flows for.

        Returns:
            List of (t, cf) where t is time in years.
        """
        freq = bond.coupon_frequency
        coupon = bond.face_value * bond.coupon_rate / freq
        n_periods = int(round(bond.maturity_years * freq))
        flows = []
        for i in range(1, n_periods + 1):
            t = i / freq
            cf = coupon + (bond.face_value if i == n_periods else 0.0)
            flows.append((t, cf))
        return flows

    def price(self, bond: BondSpec, ytm: float) -> float:
        """Compute bond clean price given YTM.

        Args:
            bond: BondSpec.
            ytm: Annual yield to maturity.

        Returns:
            Clean price.
        """
        flows = self._cash_flows(bond)
        freq = bond.coupon_frequency
        pv = sum(cf / (1 + ytm / freq) ** (t * freq) for t, cf in flows)
        return round(pv, 6)

    def ytm(self, bond: BondSpec, market_price: float, tol: float = 1e-8, max_iter: int = 200) -> float:
        """Compute YTM via Newton-Raphson bisection hybrid.

        Args:
            bond: BondSpec.
            market_price: Observed market price.
            tol: Convergence tolerance.
            max_iter: Maximum iterations.

        Returns:
            Yield to maturity as annual rate.
        """
        lo, hi = 0.0001, 5.0
        for _ in range(max_iter):
            mid = (lo + hi) / 2
            p = self.price(bond, mid)
            if abs(p - market_price) < tol:
                return round(mid, 8)
            if p > market_price:
                lo = mid
            else:
                hi = mid
        return round((lo + hi) / 2, 8)

    def macaulay_duration(self, bond: BondSpec, ytm: float) -> float:
        """Macaulay duration — weighted average time to cash flow.

        Args:
            bond: BondSpec.
            ytm: Annual yield.

        Returns:
            Duration in years.
        """
        flows = self._cash_flows(bond)
        freq = bond.coupon_frequency
        pv_total = 0.0
        weighted = 0.0
        for t, cf in flows:
            pv = cf / (1 + ytm / freq) ** (t * freq)
            pv_total += pv
            weighted += t * pv
        return round(weighted / pv_total if pv_total > 0 else 0.0, 6)

    def modified_duration(self, bond: BondSpec, ytm: float) -> float:
        """Modified duration = Macaulay duration / (1 + ytm/freq).

        Args:
            bond: BondSpec.
            ytm: Annual yield.

        Returns:
            Modified duration.
        """
        mac = self.macaulay_duration(bond, ytm)
        return round(mac / (1 + ytm / bond.coupon_frequency), 6)

    def convexity(self, bond: BondSpec, ytm: float) -> float:
        """Bond convexity — second derivative of price w.r.t. yield.

        Args:
            bond: BondSpec.
            ytm: Annual yield.

        Returns:
            Convexity.
        """
        flows = self._cash_flows(bond)
        freq = bond.coupon_frequency
        pv_total = sum(cf / (1 + ytm / freq) ** (t * freq) for t, cf in flows)
        if pv_total == 0:
            return 0.0
        conv = 0.0
        for t, cf in flows:
            n = t * freq
            pv = cf / (1 + ytm / freq) ** n
            conv += pv * n * (n + 1)
        conv /= pv_total * (1 + ytm / freq) ** 2 * freq ** 2
        return round(conv, 6)

    def dv01(self, bond: BondSpec, ytm: float) -> float:
        """DV01 — price change for 1bp yield increase.

        Args:
            bond: BondSpec.
            ytm: Annual yield.

        Returns:
            DV01 per face value.
        """
        p_up = self.price(bond, ytm + 0.0001)
        p_dn = self.price(bond, ytm - 0.0001)
        return round((p_dn - p_up) / 2, 6)

    def accrued_interest(self, bond: BondSpec, fraction_of_period: float = 0.0) -> float:
        """Accrued coupon interest.

        Args:
            bond: BondSpec.
            fraction_of_period: Fraction through the current coupon period (0–1).

        Returns:
            Accrued interest amount.
        """
        period_coupon = bond.face_value * bond.coupon_rate / bond.coupon_frequency
        return round(period_coupon * fraction_of_period, 6)

    # ------------------------------------------------------------------
    # Bucket classification
    # ------------------------------------------------------------------

    def yield_bucket(self, ytm: float) -> YieldBucket:
        """Classify YTM into yield bucket.

        Args:
            ytm: Annual yield.

        Returns:
            YieldBucket enum member.
        """
        if ytm < 0.02:
            return YieldBucket.VERY_LOW
        if ytm < 0.03:
            return YieldBucket.LOW
        if ytm < 0.04:
            return YieldBucket.MODERATE
        if ytm < 0.06:
            return YieldBucket.HIGH
        return YieldBucket.VERY_HIGH

    def credit_bucket(self, rating: str) -> CreditBucket:
        """Map rating string to CreditBucket.

        Args:
            rating: Rating string (e.g. 'Aaa', 'AA+', 'B3').

        Returns:
            CreditBucket enum member.
        """
        r = rating.strip().upper()
        if r.startswith("AAA") or r.startswith("AAA"):
            return CreditBucket.AAA
        if r.startswith("AA"):
            return CreditBucket.AA
        if r.startswith("A") and not r.startswith("AA"):
            return CreditBucket.A
        if r.startswith("BBB") or r.startswith("BAA"):
            return CreditBucket.BBB
        if r.startswith("BB") or r.startswith("BA"):
            return CreditBucket.BB
        if r.startswith("B") and not r.startswith("BB"):
            return CreditBucket.B
        if any(r.startswith(p) for p in ("CCC", "CC", "C", "D", "CA", "CAA")):
            return CreditBucket.CCC_AND_BELOW
        return CreditBucket.NOT_RATED

    def maturity_bucket(self, maturity_years: float) -> MaturityBucket:
        """Classify maturity in years into bucket.

        Args:
            maturity_years: Years to maturity.

        Returns:
            MaturityBucket enum member.
        """
        if maturity_years <= 2:
            return MaturityBucket.SHORT
        if maturity_years <= 7:
            return MaturityBucket.MEDIUM
        if maturity_years <= 15:
            return MaturityBucket.LONG
        return MaturityBucket.ULTRA_LONG

    # ------------------------------------------------------------------
    # Full analytics object
    # ------------------------------------------------------------------

    def analyze(
        self,
        bond: BondSpec,
        market_price: float,
        risk_free_rate: float = 0.0,
        accrual_fraction: float = 0.0,
    ) -> BondAnalytics:
        """Compute comprehensive analytics for a bond.

        Args:
            bond: BondSpec.
            market_price: Observed clean price.
            risk_free_rate: Risk-free benchmark rate for spread.
            accrual_fraction: Fraction through current coupon period.

        Returns:
            BondAnalytics with all computed metrics.
        """
        y = self.ytm(bond, market_price)
        mac = self.macaulay_duration(bond, y)
        mod = self.modified_duration(bond, y)
        conv = self.convexity(bond, y)
        dv = self.dv01(bond, y)
        ai = self.accrued_interest(bond, accrual_fraction)
        spread = y - risk_free_rate
        return BondAnalytics(
            isin=bond.isin,
            price=market_price,
            ytm=round(y, 6),
            duration=mac,
            modified_duration=mod,
            convexity=conv,
            dv01=dv,
            spread=round(spread, 6),
            accrued_interest=ai,
            dirty_price=round(market_price + ai, 6),
            yield_bucket=self.yield_bucket(y),
            credit_bucket=self.credit_bucket(bond.credit_rating),
            maturity_bucket=self.maturity_bucket(bond.maturity_years),
        )

    # ------------------------------------------------------------------
    # Portfolio bond analytics
    # ------------------------------------------------------------------

    def portfolio_duration(
        self,
        bonds: List[BondSpec],
        prices: List[float],
        weights: List[float],
    ) -> float:
        """Weighted average modified duration for a bond portfolio.

        Args:
            bonds: List of BondSpec.
            prices: Market prices corresponding to bonds.
            weights: Portfolio weights summing to 1.

        Returns:
            Portfolio modified duration.
        """
        n = min(len(bonds), len(prices), len(weights))
        total = 0.0
        for i in range(n):
            y = self.ytm(bonds[i], prices[i])
            mod = self.modified_duration(bonds[i], y)
            total += weights[i] * mod
        return round(total, 6)

    def yield_bucket_breakdown(
        self,
        bonds: List[BondSpec],
        prices: List[float],
        weights: List[float],
    ) -> Dict[str, float]:
        """Aggregate portfolio weight by yield bucket.

        Args:
            bonds: List of BondSpec.
            prices: Market prices.
            weights: Portfolio weights.

        Returns:
            Dict mapping YieldBucket.value -> total weight.
        """
        n = min(len(bonds), len(prices), len(weights))
        buckets: Dict[str, float] = {}
        for i in range(n):
            y = self.ytm(bonds[i], prices[i])
            bucket = self.yield_bucket(y).value
            buckets[bucket] = round(buckets.get(bucket, 0.0) + weights[i], 8)
        return {k: round(v, 6) for k, v in buckets.items()}

    def credit_bucket_breakdown(
        self,
        bonds: List[BondSpec],
        weights: List[float],
    ) -> Dict[str, float]:
        """Aggregate portfolio weight by credit quality bucket.

        Args:
            bonds: List of BondSpec.
            weights: Portfolio weights.

        Returns:
            Dict mapping CreditBucket.value -> total weight.
        """
        n = min(len(bonds), len(weights))
        buckets: Dict[str, float] = {}
        for i in range(n):
            bucket = self.credit_bucket(bonds[i].credit_rating).value
            buckets[bucket] = round(buckets.get(bucket, 0.0) + weights[i], 8)
        return {k: round(v, 6) for k, v in buckets.items()}


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_bond_engine: Optional[BondEngine] = None


def get_bond_engine() -> BondEngine:
    """Return the singleton BondEngine instance.

    Returns:
        Shared BondEngine instance.
    """
    global _default_bond_engine
    if _default_bond_engine is None:
        _default_bond_engine = BondEngine()
    return _default_bond_engine
