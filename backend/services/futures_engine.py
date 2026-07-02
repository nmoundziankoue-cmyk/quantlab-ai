"""M16 Phase 7 — Futures Analytics Engine.

Term structure analysis, contango/backwardation detection, roll yield,
carry calculation, basis, and futures curve analytics — pure Python.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class MarketStructure(str, Enum):
    CONTANGO = "contango"
    BACKWARDATION = "backwardation"
    FLAT = "flat"


class RollStrategy(str, Enum):
    FRONT_ROLL = "front_roll"          # roll to next front month
    CALENDAR_SPREAD = "calendar_spread"
    DYNAMIC = "dynamic"


class AssetClass(str, Enum):
    COMMODITY = "commodity"
    EQUITY_INDEX = "equity_index"
    INTEREST_RATE = "interest_rate"
    CURRENCY = "currency"
    CRYPTO = "crypto"
    ENERGY = "energy"
    METALS = "metals"
    AGRICULTURE = "agriculture"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class FuturesContract:
    """A single futures contract in a term structure.

    Attributes:
        ticker: Root ticker (e.g. 'CL' for WTI crude).
        contract_code: Specific contract month code (e.g. 'CLZ24').
        expiry_years: Years to expiry from today.
        price: Settlement/last price.
        open_interest: Open interest (contracts).
        volume: Daily volume.
        asset_class: Futures asset class.
    """
    ticker: str
    contract_code: str
    expiry_years: float
    price: float
    open_interest: int = 0
    volume: int = 0
    asset_class: AssetClass = AssetClass.COMMODITY

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "ticker": self.ticker,
            "contract_code": self.contract_code,
            "expiry_years": self.expiry_years,
            "price": round(self.price, 6),
            "open_interest": self.open_interest,
            "volume": self.volume,
            "asset_class": self.asset_class.value,
        }


@dataclass
class TermStructure:
    """Futures term structure for a single underlying.

    Attributes:
        ticker: Root ticker.
        contracts: List of FuturesContract sorted by expiry.
        structure: Contango / backwardation / flat.
        slope_percent: Annualised % slope from front to back.
        front_price: Front month price.
        back_price: Furthest month price.
        curve_points: List of (expiry_years, price) for charting.
    """
    ticker: str
    contracts: List[FuturesContract]
    structure: MarketStructure
    slope_percent: float
    front_price: float
    back_price: float
    curve_points: List[Tuple[float, float]]

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "ticker": self.ticker,
            "contracts": [c.to_dict() for c in self.contracts],
            "structure": self.structure.value,
            "slope_percent": round(self.slope_percent, 4),
            "front_price": round(self.front_price, 6),
            "back_price": round(self.back_price, 6),
            "curve_points": [[round(t, 4), round(p, 6)] for t, p in self.curve_points],
        }


@dataclass
class RollYield:
    """Roll yield from rolling a futures position forward.

    Attributes:
        ticker: Root ticker.
        near_contract: Near-month contract code.
        far_contract: Far-month contract code.
        near_price: Near-month price.
        far_price: Far-month price.
        roll_yield_annualised: Annualised roll yield (fraction).
        time_between: Years between contracts.
        structure: Contango (negative roll) or backwardation (positive roll).
    """
    ticker: str
    near_contract: str
    far_contract: str
    near_price: float
    far_price: float
    roll_yield_annualised: float
    time_between: float
    structure: MarketStructure

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "ticker": self.ticker,
            "near_contract": self.near_contract,
            "far_contract": self.far_contract,
            "near_price": round(self.near_price, 6),
            "far_price": round(self.far_price, 6),
            "roll_yield_annualised": round(self.roll_yield_annualised, 6),
            "time_between": round(self.time_between, 4),
            "structure": self.structure.value,
        }


@dataclass
class FuturesBasis:
    """Basis = spot price minus futures price.

    Attributes:
        ticker: Ticker.
        spot_price: Spot / cash price.
        futures_price: Nearest futures price.
        basis: spot - futures.
        basis_percent: basis / spot.
        cost_of_carry: Implied cost of carry rate.
        convergence_days: Estimated days to expiry.
    """
    ticker: str
    spot_price: float
    futures_price: float
    basis: float
    basis_percent: float
    cost_of_carry: float
    convergence_days: int

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "ticker": self.ticker,
            "spot_price": round(self.spot_price, 6),
            "futures_price": round(self.futures_price, 6),
            "basis": round(self.basis, 6),
            "basis_percent": round(self.basis_percent, 6),
            "cost_of_carry": round(self.cost_of_carry, 6),
            "convergence_days": self.convergence_days,
        }


@dataclass
class CarryScore:
    """Carry signal for cross-sectional ranking.

    Attributes:
        ticker: Ticker.
        carry: Raw carry estimate (roll yield %).
        carry_zscore: Z-score in cross-section.
        rank: Rank in universe (1 = highest carry).
        signal: 'long', 'short', or 'neutral'.
    """
    ticker: str
    carry: float
    carry_zscore: float
    rank: int
    signal: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "ticker": self.ticker,
            "carry": round(self.carry, 6),
            "carry_zscore": round(self.carry_zscore, 6),
            "rank": self.rank,
            "signal": self.signal,
        }


# ---------------------------------------------------------------------------
# FuturesEngine
# ---------------------------------------------------------------------------

class FuturesEngine:
    """Futures Analytics Engine.

    Provides term structure analysis, roll yield, basis computation,
    and cross-sectional carry ranking — pure Python, in-memory.
    """

    # ------------------------------------------------------------------
    # Term structure
    # ------------------------------------------------------------------

    def term_structure(self, contracts: List[FuturesContract]) -> TermStructure:
        """Build and classify a futures term structure.

        Args:
            contracts: List of FuturesContract (any order).

        Returns:
            TermStructure sorted by expiry with structure classification.
        """
        if not contracts:
            raise ValueError("contracts must be non-empty")
        sorted_c = sorted(contracts, key=lambda c: c.expiry_years)
        front = sorted_c[0]
        back = sorted_c[-1]
        curve_pts = [(c.expiry_years, c.price) for c in sorted_c]

        t_diff = back.expiry_years - front.expiry_years
        if t_diff > 0:
            slope = (back.price - front.price) / front.price / t_diff * 100
        else:
            slope = 0.0

        if slope > 0.1:
            structure = MarketStructure.CONTANGO
        elif slope < -0.1:
            structure = MarketStructure.BACKWARDATION
        else:
            structure = MarketStructure.FLAT

        return TermStructure(
            ticker=front.ticker,
            contracts=sorted_c,
            structure=structure,
            slope_percent=round(slope, 4),
            front_price=front.price,
            back_price=back.price,
            curve_points=curve_pts,
        )

    # ------------------------------------------------------------------
    # Roll yield
    # ------------------------------------------------------------------

    def roll_yield(
        self, near: FuturesContract, far: FuturesContract
    ) -> RollYield:
        """Compute annualised roll yield between two contracts.

        Roll yield = (near_price - far_price) / far_price / time_between (annualised).
        Positive = backwardation; negative = contango.

        Args:
            near: Near-month contract.
            far: Far-month contract.

        Returns:
            RollYield.
        """
        time_between = far.expiry_years - near.expiry_years
        if time_between <= 0:
            time_between = 1 / 12
        raw = (near.price - far.price) / far.price
        ann = raw / time_between

        if ann > 0.001:
            structure = MarketStructure.BACKWARDATION
        elif ann < -0.001:
            structure = MarketStructure.CONTANGO
        else:
            structure = MarketStructure.FLAT

        return RollYield(
            ticker=near.ticker,
            near_contract=near.contract_code,
            far_contract=far.contract_code,
            near_price=near.price,
            far_price=far.price,
            roll_yield_annualised=round(ann, 6),
            time_between=round(time_between, 4),
            structure=structure,
        )

    def roll_yield_curve(self, ts: TermStructure) -> List[RollYield]:
        """Compute consecutive roll yields across a term structure.

        Args:
            ts: TermStructure with sorted contracts.

        Returns:
            List of RollYield for each consecutive pair.
        """
        contracts = ts.contracts
        return [
            self.roll_yield(contracts[i], contracts[i + 1])
            for i in range(len(contracts) - 1)
        ]

    # ------------------------------------------------------------------
    # Basis
    # ------------------------------------------------------------------

    def basis(
        self,
        ticker: str,
        spot_price: float,
        near_contract: FuturesContract,
    ) -> FuturesBasis:
        """Compute basis between spot and nearest futures.

        Args:
            ticker: Ticker symbol.
            spot_price: Spot/cash price.
            near_contract: Nearest FuturesContract.

        Returns:
            FuturesBasis.
        """
        b = spot_price - near_contract.price
        b_pct = b / spot_price if spot_price != 0 else 0.0
        T = max(near_contract.expiry_years, 1 / 365)
        if spot_price > 0 and near_contract.price > 0:
            coc = math.log(near_contract.price / spot_price) / T
        else:
            coc = 0.0
        conv_days = int(round(near_contract.expiry_years * 365))
        return FuturesBasis(
            ticker=ticker,
            spot_price=spot_price,
            futures_price=near_contract.price,
            basis=round(b, 6),
            basis_percent=round(b_pct, 6),
            cost_of_carry=round(coc, 6),
            convergence_days=conv_days,
        )

    # ------------------------------------------------------------------
    # Fair value (cost-of-carry model)
    # ------------------------------------------------------------------

    def fair_value(
        self,
        spot: float,
        risk_free_rate: float,
        dividend_yield: float,
        storage_cost: float,
        convenience_yield: float,
        expiry_years: float,
    ) -> float:
        """Futures fair value via cost-of-carry model.

        F = S × exp((r - q + u - c) × T)

        Args:
            spot: Spot price.
            risk_free_rate: Continuous risk-free rate.
            dividend_yield: Continuous dividend yield (equity) or 0.
            storage_cost: Annual storage cost rate (commodities).
            convenience_yield: Annual convenience yield (commodities).
            expiry_years: Time to expiry.

        Returns:
            Fair value futures price.
        """
        carry = risk_free_rate - dividend_yield + storage_cost - convenience_yield
        return round(spot * math.exp(carry * expiry_years), 6)

    # ------------------------------------------------------------------
    # Carry cross-section
    # ------------------------------------------------------------------

    def carry_scores(
        self,
        carry_map: Dict[str, float],
    ) -> List[CarryScore]:
        """Rank a universe of futures by carry (roll yield).

        Args:
            carry_map: Dict mapping ticker -> annualised carry (roll yield).

        Returns:
            List of CarryScore sorted from highest to lowest carry.
        """
        if not carry_map:
            return []
        values = list(carry_map.values())
        m = sum(values) / len(values)
        s = (sum((v - m) ** 2 for v in values) / max(len(values) - 1, 1)) ** 0.5
        sorted_items = sorted(carry_map.items(), key=lambda x: x[1], reverse=True)
        results = []
        for rank, (ticker, carry) in enumerate(sorted_items, start=1):
            z = (carry - m) / s if s > 0 else 0.0
            if z > 0.5:
                signal = "long"
            elif z < -0.5:
                signal = "short"
            else:
                signal = "neutral"
            results.append(CarryScore(
                ticker=ticker,
                carry=round(carry, 6),
                carry_zscore=round(z, 6),
                rank=rank,
                signal=signal,
            ))
        return results

    # ------------------------------------------------------------------
    # Open interest analysis
    # ------------------------------------------------------------------

    def open_interest_summary(self, contracts: List[FuturesContract]) -> Dict[str, Any]:
        """Summarise open interest distribution across contracts.

        Args:
            contracts: List of FuturesContract.

        Returns:
            Dict with total OI, per-contract breakdown, and dominant contract.
        """
        if not contracts:
            return {"total_oi": 0, "dominant_contract": "", "contracts": []}
        total_oi = sum(c.open_interest for c in contracts)
        dominant = max(contracts, key=lambda c: c.open_interest)
        return {
            "total_oi": total_oi,
            "dominant_contract": dominant.contract_code,
            "contracts": [
                {
                    "code": c.contract_code,
                    "expiry_years": c.expiry_years,
                    "oi": c.open_interest,
                    "oi_pct": round(c.open_interest / total_oi * 100, 2) if total_oi else 0.0,
                }
                for c in sorted(contracts, key=lambda c: c.expiry_years)
            ],
        }

    # ------------------------------------------------------------------
    # Seasonality bucket
    # ------------------------------------------------------------------

    def seasonality_bucket(self, month: int) -> str:
        """Classify a calendar month into commodity seasonality bucket.

        Args:
            month: Calendar month (1–12).

        Returns:
            Season label.
        """
        if month in (12, 1, 2):
            return "winter"
        if month in (3, 4, 5):
            return "spring"
        if month in (6, 7, 8):
            return "summer"
        return "autumn"


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_futures_engine: Optional[FuturesEngine] = None


def get_futures_engine() -> FuturesEngine:
    """Return the singleton FuturesEngine instance.

    Returns:
        Shared FuturesEngine instance.
    """
    global _default_futures_engine
    if _default_futures_engine is None:
        _default_futures_engine = FuturesEngine()
    return _default_futures_engine
