"""M16 Phase 8 — Crypto Intelligence Engine.

Dominance metrics, on-chain proxies, sector classification, breadth
analysis, stablecoin ratios, and cycle indicators — pure Python, in-memory.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class CryptoSector(str, Enum):
    LAYER1 = "layer1"
    LAYER2 = "layer2"
    DEFI = "defi"
    NFT = "nft"
    STABLECOIN = "stablecoin"
    EXCHANGE = "exchange"
    GAMING = "gaming"
    INFRASTRUCTURE = "infrastructure"
    PRIVACY = "privacy"
    ORACLE = "oracle"
    STORAGE = "storage"
    OTHER = "other"


class CyclePhase(str, Enum):
    ACCUMULATION = "accumulation"
    MARKUP = "markup"
    DISTRIBUTION = "distribution"
    MARKDOWN = "markdown"


class MarketSentiment(str, Enum):
    EXTREME_FEAR = "extreme_fear"
    FEAR = "fear"
    NEUTRAL = "neutral"
    GREED = "greed"
    EXTREME_GREED = "extreme_greed"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CryptoAsset:
    """Metadata for a single crypto asset.

    Attributes:
        ticker: Ticker symbol (e.g. 'BTC').
        name: Full name.
        sector: CryptoSector classification.
        market_cap_usd: Market capitalisation in USD millions.
        circulating_supply: Number of tokens in circulation.
        total_supply: Total supply (or max supply if capped).
        is_stablecoin: Whether the asset is a stablecoin.
        chain: Underlying L1 chain (e.g. 'ethereum', 'solana').
        consensus: Consensus mechanism ('pow', 'pos', 'dpos', etc.).
    """
    ticker: str
    name: str
    sector: CryptoSector
    market_cap_usd: float
    circulating_supply: float
    total_supply: float
    is_stablecoin: bool = False
    chain: str = "native"
    consensus: str = "pos"

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "ticker": self.ticker,
            "name": self.name,
            "sector": self.sector.value,
            "market_cap_usd": round(self.market_cap_usd, 2),
            "circulating_supply": self.circulating_supply,
            "total_supply": self.total_supply,
            "is_stablecoin": self.is_stablecoin,
            "chain": self.chain,
            "consensus": self.consensus,
        }


@dataclass
class DominanceSnapshot:
    """Market dominance snapshot.

    Attributes:
        btc_dominance: Bitcoin market cap / total market cap.
        eth_dominance: Ethereum market cap / total market cap.
        stablecoin_dominance: Stablecoin market cap / total.
        altcoin_dominance: Remaining share.
        total_market_cap_usd: Total crypto market cap (USD millions).
        sector_dominance: Dict mapping CryptoSector -> dominance fraction.
    """
    btc_dominance: float
    eth_dominance: float
    stablecoin_dominance: float
    altcoin_dominance: float
    total_market_cap_usd: float
    sector_dominance: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "btc_dominance": round(self.btc_dominance, 6),
            "eth_dominance": round(self.eth_dominance, 6),
            "stablecoin_dominance": round(self.stablecoin_dominance, 6),
            "altcoin_dominance": round(self.altcoin_dominance, 6),
            "total_market_cap_usd": round(self.total_market_cap_usd, 2),
            "sector_dominance": {k: round(v, 6) for k, v in self.sector_dominance.items()},
        }


@dataclass
class OnChainProxy:
    """On-chain activity proxy computed from observable price/volume data.

    Attributes:
        ticker: Asset ticker.
        nvt_proxy: NVT proxy — market_cap / (volume × price).
        mvrv_proxy: MVRV proxy — current price / estimated realised price.
        active_address_proxy: Volume-based proxy for network activity.
        nvt_signal: 'overvalued', 'fair', or 'undervalued'.
    """
    ticker: str
    nvt_proxy: float
    mvrv_proxy: float
    active_address_proxy: float
    nvt_signal: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "ticker": self.ticker,
            "nvt_proxy": round(self.nvt_proxy, 4),
            "mvrv_proxy": round(self.mvrv_proxy, 4),
            "active_address_proxy": round(self.active_address_proxy, 4),
            "nvt_signal": self.nvt_signal,
        }


@dataclass
class MarketBreadth:
    """Market breadth metrics for the crypto universe.

    Attributes:
        n_assets: Total assets analysed.
        n_advancing: Assets with positive return.
        n_declining: Assets with negative return.
        advance_decline_ratio: n_advancing / n_declining.
        advance_decline_line: Cumulative A/D line value.
        pct_above_sma20: Fraction above 20-period SMA.
        pct_above_sma50: Fraction above 50-period SMA.
        new_highs: Assets at 52-week high.
        new_lows: Assets at 52-week low.
    """
    n_assets: int
    n_advancing: int
    n_declining: int
    advance_decline_ratio: float
    advance_decline_line: float
    pct_above_sma20: float
    pct_above_sma50: float
    new_highs: int
    new_lows: int

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "n_assets": self.n_assets,
            "n_advancing": self.n_advancing,
            "n_declining": self.n_declining,
            "advance_decline_ratio": round(self.advance_decline_ratio, 4),
            "advance_decline_line": round(self.advance_decline_line, 4),
            "pct_above_sma20": round(self.pct_above_sma20, 4),
            "pct_above_sma50": round(self.pct_above_sma50, 4),
            "new_highs": self.new_highs,
            "new_lows": self.new_lows,
        }


@dataclass
class StablecoinRatio:
    """Stablecoin market ratio and risk-off signal.

    Attributes:
        stablecoin_market_cap: Total stablecoin market cap (USD millions).
        total_market_cap: Total crypto market cap (USD millions).
        ratio: stablecoin_market_cap / total_market_cap.
        signal: 'risk_off' if ratio > threshold, else 'risk_on'.
        threshold: Classification threshold used.
    """
    stablecoin_market_cap: float
    total_market_cap: float
    ratio: float
    signal: str
    threshold: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "stablecoin_market_cap": round(self.stablecoin_market_cap, 2),
            "total_market_cap": round(self.total_market_cap, 2),
            "ratio": round(self.ratio, 6),
            "signal": self.signal,
            "threshold": self.threshold,
        }


@dataclass
class CycleIndicator:
    """Crypto market cycle phase indicator.

    Attributes:
        cycle_phase: Current estimated cycle phase.
        btc_drawdown_from_ath: Current BTC drawdown from all-time high.
        fear_greed_score: Composite fear/greed score [0, 100].
        sentiment: MarketSentiment classification.
        risk_level: 'low', 'medium', or 'high'.
    """
    cycle_phase: CyclePhase
    btc_drawdown_from_ath: float
    fear_greed_score: float
    sentiment: MarketSentiment
    risk_level: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "cycle_phase": self.cycle_phase.value,
            "btc_drawdown_from_ath": round(self.btc_drawdown_from_ath, 4),
            "fear_greed_score": round(self.fear_greed_score, 2),
            "sentiment": self.sentiment.value,
            "risk_level": self.risk_level,
        }


# ---------------------------------------------------------------------------
# CryptoEngine
# ---------------------------------------------------------------------------

class CryptoEngine:
    """Crypto Intelligence Engine.

    Provides dominance metrics, on-chain proxies, sector classification,
    breadth analysis, stablecoin ratios, and cycle indicators.
    Pure Python, deterministic, in-memory.
    """

    # ------------------------------------------------------------------
    # Dominance
    # ------------------------------------------------------------------

    def dominance_snapshot(self, assets: List[CryptoAsset]) -> DominanceSnapshot:
        """Compute market dominance snapshot.

        Args:
            assets: Universe of CryptoAsset objects.

        Returns:
            DominanceSnapshot with BTC, ETH, stablecoin, and sector shares.
        """
        total_mc = sum(a.market_cap_usd for a in assets)
        if total_mc == 0:
            return DominanceSnapshot(0, 0, 0, 0, 0, {})

        btc_mc = sum(a.market_cap_usd for a in assets if a.ticker.upper() == "BTC")
        eth_mc = sum(a.market_cap_usd for a in assets if a.ticker.upper() == "ETH")
        stable_mc = sum(a.market_cap_usd for a in assets if a.is_stablecoin)
        btc_dom = btc_mc / total_mc
        eth_dom = eth_mc / total_mc
        stable_dom = stable_mc / total_mc
        alt_dom = max(0.0, 1.0 - btc_dom - eth_dom - stable_dom)

        sector_dom: Dict[str, float] = {}
        for a in assets:
            key = a.sector.value
            sector_dom[key] = sector_dom.get(key, 0.0) + a.market_cap_usd / total_mc

        return DominanceSnapshot(
            btc_dominance=round(btc_dom, 6),
            eth_dominance=round(eth_dom, 6),
            stablecoin_dominance=round(stable_dom, 6),
            altcoin_dominance=round(alt_dom, 6),
            total_market_cap_usd=round(total_mc, 2),
            sector_dominance={k: round(v, 6) for k, v in sector_dom.items()},
        )

    # ------------------------------------------------------------------
    # On-chain proxies
    # ------------------------------------------------------------------

    def on_chain_proxy(
        self,
        asset: CryptoAsset,
        price_series: List[float],
        volume_series: List[float],
    ) -> OnChainProxy:
        """Compute on-chain proxy metrics from price/volume data.

        NVT proxy = (market_cap_usd / usd_volume_30d_avg).
        MVRV proxy = current_price / realised_price_proxy (200d avg).
        Active address proxy = volume / market_cap_usd (normalised activity).

        Args:
            asset: CryptoAsset.
            price_series: Daily price series (most recent last).
            volume_series: Daily USD volume series (most recent last).

        Returns:
            OnChainProxy with NVT, MVRV, and activity proxies.
        """
        n_vol = min(len(volume_series), 30)
        avg_vol_30 = sum(volume_series[-n_vol:]) / n_vol if n_vol > 0 else 1.0
        nvt = asset.market_cap_usd / avg_vol_30 if avg_vol_30 > 0 else 0.0

        n_price = min(len(price_series), 200)
        realised_proxy = sum(price_series[-n_price:]) / n_price if n_price > 0 else 1.0
        current_price = price_series[-1] if price_series else 0.0
        mvrv = current_price / realised_proxy if realised_proxy > 0 else 0.0

        last_vol = volume_series[-1] if volume_series else 0.0
        activity_proxy = last_vol / asset.market_cap_usd if asset.market_cap_usd > 0 else 0.0

        if nvt > 100:
            nvt_signal = "overvalued"
        elif nvt < 20:
            nvt_signal = "undervalued"
        else:
            nvt_signal = "fair"

        return OnChainProxy(
            ticker=asset.ticker,
            nvt_proxy=round(nvt, 4),
            mvrv_proxy=round(mvrv, 4),
            active_address_proxy=round(activity_proxy, 6),
            nvt_signal=nvt_signal,
        )

    # ------------------------------------------------------------------
    # Market breadth
    # ------------------------------------------------------------------

    def market_breadth(
        self,
        assets: List[CryptoAsset],
        returns: Dict[str, float],
        price_series_map: Dict[str, List[float]],
        prior_ad_line: float = 0.0,
    ) -> MarketBreadth:
        """Compute crypto market breadth indicators.

        Args:
            assets: Universe of CryptoAsset.
            returns: Dict mapping ticker -> latest period return.
            price_series_map: Dict mapping ticker -> price series (oldest first).
            prior_ad_line: Prior advance-decline line value for continuity.

        Returns:
            MarketBreadth.
        """
        n = len(assets)
        n_adv = sum(1 for a in assets if returns.get(a.ticker, 0) > 0)
        n_dec = sum(1 for a in assets if returns.get(a.ticker, 0) < 0)
        ad_ratio = n_adv / n_dec if n_dec > 0 else float(n_adv)
        ad_line = prior_ad_line + (n_adv - n_dec)

        above_20, above_50, new_highs, new_lows = 0, 0, 0, 0
        for a in assets:
            ps = price_series_map.get(a.ticker, [])
            if not ps:
                continue
            cur = ps[-1]
            if len(ps) >= 20:
                sma20 = sum(ps[-20:]) / 20
                if cur > sma20:
                    above_20 += 1
            if len(ps) >= 50:
                sma50 = sum(ps[-50:]) / 50
                if cur > sma50:
                    above_50 += 1
            if len(ps) >= 252:
                hi52 = max(ps[-252:])
                lo52 = min(ps[-252:])
                if cur >= hi52:
                    new_highs += 1
                if cur <= lo52:
                    new_lows += 1

        counted_20 = sum(1 for a in assets if len(price_series_map.get(a.ticker, [])) >= 20)
        counted_50 = sum(1 for a in assets if len(price_series_map.get(a.ticker, [])) >= 50)
        pct_20 = above_20 / counted_20 if counted_20 > 0 else 0.0
        pct_50 = above_50 / counted_50 if counted_50 > 0 else 0.0

        return MarketBreadth(
            n_assets=n,
            n_advancing=n_adv,
            n_declining=n_dec,
            advance_decline_ratio=round(ad_ratio, 4),
            advance_decline_line=round(ad_line, 2),
            pct_above_sma20=round(pct_20, 4),
            pct_above_sma50=round(pct_50, 4),
            new_highs=new_highs,
            new_lows=new_lows,
        )

    # ------------------------------------------------------------------
    # Stablecoin ratio
    # ------------------------------------------------------------------

    def stablecoin_ratio(
        self,
        assets: List[CryptoAsset],
        risk_off_threshold: float = 0.12,
    ) -> StablecoinRatio:
        """Compute stablecoin market ratio and risk signal.

        Args:
            assets: Universe of CryptoAsset.
            risk_off_threshold: Ratio above which market is 'risk_off'.

        Returns:
            StablecoinRatio.
        """
        total_mc = sum(a.market_cap_usd for a in assets)
        stable_mc = sum(a.market_cap_usd for a in assets if a.is_stablecoin)
        ratio = stable_mc / total_mc if total_mc > 0 else 0.0
        signal = "risk_off" if ratio >= risk_off_threshold else "risk_on"
        return StablecoinRatio(
            stablecoin_market_cap=round(stable_mc, 2),
            total_market_cap=round(total_mc, 2),
            ratio=round(ratio, 6),
            signal=signal,
            threshold=risk_off_threshold,
        )

    # ------------------------------------------------------------------
    # Cycle indicator
    # ------------------------------------------------------------------

    def cycle_indicator(
        self,
        btc_current_price: float,
        btc_ath: float,
        btc_returns_90d: List[float],
        altcoin_dominance: float,
        stablecoin_ratio_val: float,
    ) -> CycleIndicator:
        """Estimate crypto market cycle phase from observable metrics.

        Args:
            btc_current_price: Current BTC price.
            btc_ath: BTC all-time high price.
            btc_returns_90d: BTC daily returns over past 90 days.
            altcoin_dominance: Altcoin share of total market cap.
            stablecoin_ratio_val: Current stablecoin ratio.

        Returns:
            CycleIndicator with phase, sentiment, and risk.
        """
        drawdown = (btc_ath - btc_current_price) / btc_ath if btc_ath > 0 else 0.0
        momentum_90 = sum(btc_returns_90d[-90:]) if btc_returns_90d else 0.0
        vol_90 = (sum((r - (momentum_90 / max(len(btc_returns_90d), 1))) ** 2
                      for r in btc_returns_90d) / max(len(btc_returns_90d) - 1, 1)) ** 0.5

        # Fear-greed composite [0, 100]
        momentum_score = min(100, max(0, 50 + momentum_90 * 500))
        drawdown_score = max(0, 100 - drawdown * 200)
        dom_score = min(100, altcoin_dominance * 200)  # high altcoin dom = greed
        stable_score = max(0, 100 - stablecoin_ratio_val * 500)  # high stable = fear
        fg = (momentum_score * 0.3 + drawdown_score * 0.3 + dom_score * 0.2 + stable_score * 0.2)
        fg = round(max(0.0, min(100.0, fg)), 2)

        if fg <= 20:
            sentiment = MarketSentiment.EXTREME_FEAR
        elif fg <= 40:
            sentiment = MarketSentiment.FEAR
        elif fg <= 60:
            sentiment = MarketSentiment.NEUTRAL
        elif fg <= 80:
            sentiment = MarketSentiment.GREED
        else:
            sentiment = MarketSentiment.EXTREME_GREED

        if drawdown > 0.7:
            phase = CyclePhase.MARKDOWN
        elif drawdown > 0.4:
            phase = CyclePhase.ACCUMULATION
        elif momentum_90 > 0.1 and drawdown < 0.3:
            phase = CyclePhase.MARKUP
        else:
            phase = CyclePhase.DISTRIBUTION

        if fg < 30:
            risk_level = "low"
        elif fg < 70:
            risk_level = "medium"
        else:
            risk_level = "high"

        return CycleIndicator(
            cycle_phase=phase,
            btc_drawdown_from_ath=round(drawdown, 4),
            fear_greed_score=fg,
            sentiment=sentiment,
            risk_level=risk_level,
        )

    # ------------------------------------------------------------------
    # Sector performance
    # ------------------------------------------------------------------

    def sector_performance(
        self,
        assets: List[CryptoAsset],
        returns: Dict[str, float],
    ) -> Dict[str, Any]:
        """Compute market-cap-weighted performance by crypto sector.

        Args:
            assets: Universe of CryptoAsset.
            returns: Dict ticker -> period return.

        Returns:
            Dict mapping sector -> {'return': float, 'weight': float}.
        """
        sector_mc: Dict[str, float] = {}
        sector_ret: Dict[str, float] = {}
        total_mc = sum(a.market_cap_usd for a in assets)

        for a in assets:
            sec = a.sector.value
            sector_mc[sec] = sector_mc.get(sec, 0.0) + a.market_cap_usd
            w = a.market_cap_usd / total_mc if total_mc > 0 else 0.0
            r = returns.get(a.ticker, 0.0)
            sector_ret[sec] = sector_ret.get(sec, 0.0) + w * r

        result: Dict[str, Any] = {}
        for sec in sector_mc:
            sec_weight = sector_mc[sec] / total_mc if total_mc > 0 else 0.0
            result[sec] = {
                "return": round(sector_ret.get(sec, 0.0), 6),
                "weight": round(sec_weight, 6),
            }
        return result

    # ------------------------------------------------------------------
    # Classify asset
    # ------------------------------------------------------------------

    def classify_asset(self, ticker: str, name: str, chain: str = "") -> CryptoSector:
        """Heuristic sector classification based on name and chain keywords.

        Args:
            ticker: Asset ticker.
            name: Asset full name.
            chain: Underlying chain string.

        Returns:
            CryptoSector best match.
        """
        text = f"{ticker} {name} {chain}".lower()
        if any(k in text for k in ("usdt", "usdc", "dai", "busd", "stable", "tusd", "frax")):
            return CryptoSector.STABLECOIN
        if any(k in text for k in ("nft", "art", "collectible", "rare")):
            return CryptoSector.NFT
        if any(k in text for k in ("defi", "swap", "yield", "lend", "borrow", "amm", "dex")):
            return CryptoSector.DEFI
        if any(k in text for k in ("exchange", "binance", "kraken", "ftx", "okex", "huobi")):
            return CryptoSector.EXCHANGE
        if any(k in text for k in ("game", "gaming", "play", "metaverse", "axie")):
            return CryptoSector.GAMING
        if any(k in text for k in ("oracle", "chainlink", "band", "api3")):
            return CryptoSector.ORACLE
        if any(k in text for k in ("storage", "filecoin", "arweave", "sia")):
            return CryptoSector.STORAGE
        if any(k in text for k in ("privacy", "monero", "zcash", "dash", "secret")):
            return CryptoSector.PRIVACY
        if any(k in text for k in ("layer2", "l2", "rollup", "polygon", "optimism", "arbitrum", "zk")):
            return CryptoSector.LAYER2
        if any(k in text for k in ("bitcoin", "btc", "ethereum", "eth", "solana", "sol", "avalanche",
                                    "avax", "cardano", "ada", "polkadot", "dot", "cosmos", "atom")):
            return CryptoSector.LAYER1
        if any(k in text for k in ("infra", "node", "validator", "bridge", "cross-chain")):
            return CryptoSector.INFRASTRUCTURE
        return CryptoSector.OTHER


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_crypto_engine: Optional[CryptoEngine] = None


def get_crypto_engine() -> CryptoEngine:
    """Return the singleton CryptoEngine instance.

    Returns:
        Shared CryptoEngine instance.
    """
    global _default_crypto_engine
    if _default_crypto_engine is None:
        _default_crypto_engine = CryptoEngine()
    return _default_crypto_engine
