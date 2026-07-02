"""M16 Phase 1 — Institutional Asset Registry.

Canonical multi-asset registry supporting equities, ETFs, bonds, futures, options,
crypto, commodities, FX, and indices.  Pure Python, in-memory, fully deterministic.
No external network calls.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class AssetType(str, Enum):
    """Broad asset classification."""
    EQUITY = "equity"
    ETF = "etf"
    INDEX = "index"
    BOND = "bond"
    FUTURE = "future"
    OPTION = "option"
    CRYPTO = "crypto"
    COMMODITY = "commodity"
    FX = "fx"
    CASH = "cash"


class Exchange(str, Enum):
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    AMEX = "AMEX"
    LSE = "LSE"
    XETRA = "XETRA"
    EURONEXT = "EURONEXT"
    TSX = "TSX"
    ASX = "ASX"
    TSE = "TSE"
    HKEX = "HKEX"
    SSE = "SSE"
    SZSE = "SZSE"
    NSE = "NSE"
    BSE = "BSE"
    CBOE = "CBOE"
    CME = "CME"
    ICE = "ICE"
    CRYPTO_GLOBAL = "CRYPTO_GLOBAL"
    OTC = "OTC"
    UNKNOWN = "UNKNOWN"


class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CAD = "CAD"
    AUD = "AUD"
    CHF = "CHF"
    CNY = "CNY"
    HKD = "HKD"
    SEK = "SEK"
    NOK = "NOK"
    BTC = "BTC"
    ETH = "ETH"


class Country(str, Enum):
    US = "US"
    GB = "GB"
    DE = "DE"
    FR = "FR"
    JP = "JP"
    CA = "CA"
    AU = "AU"
    CH = "CH"
    CN = "CN"
    HK = "HK"
    IN = "IN"
    BR = "BR"
    KR = "KR"
    TW = "TW"
    SG = "SG"
    GLOBAL = "GLOBAL"


class Sector(str, Enum):
    TECHNOLOGY = "technology"
    HEALTHCARE = "healthcare"
    FINANCIALS = "financials"
    CONSUMER_DISCRETIONARY = "consumer_discretionary"
    CONSUMER_STAPLES = "consumer_staples"
    INDUSTRIALS = "industrials"
    ENERGY = "energy"
    MATERIALS = "materials"
    UTILITIES = "utilities"
    REAL_ESTATE = "real_estate"
    COMMUNICATION_SERVICES = "communication_services"
    CRYPTO = "crypto"
    FIXED_INCOME = "fixed_income"
    COMMODITIES = "commodities"
    FX = "fx"
    MULTI_SECTOR = "multi_sector"
    UNKNOWN = "unknown"


class Industry(str, Enum):
    SOFTWARE = "software"
    SEMICONDUCTORS = "semiconductors"
    HARDWARE = "hardware"
    INTERNET = "internet"
    BIOTECH = "biotech"
    PHARMA = "pharma"
    MEDICAL_DEVICES = "medical_devices"
    BANKS = "banks"
    INSURANCE = "insurance"
    ASSET_MANAGEMENT = "asset_management"
    DIVERSIFIED = "diversified"
    RETAIL = "retail"
    AUTOS = "autos"
    MEDIA = "media"
    TELECOM = "telecom"
    OIL_GAS = "oil_gas"
    RENEWABLES = "renewables"
    CHEMICALS = "chemicals"
    METALS = "metals"
    AGRICULTURE = "agriculture"
    REITS = "reits"
    AEROSPACE = "aerospace"
    DEFENSE = "defense"
    TRANSPORT = "transport"
    CONSTRUCTION = "construction"
    UTILITIES = "utilities"
    UNKNOWN = "unknown"


class MarketCapBucket(str, Enum):
    MEGA = "mega"          # > $200B
    LARGE = "large"        # $10B–$200B
    MID = "mid"            # $2B–$10B
    SMALL = "small"        # $300M–$2B
    MICRO = "micro"        # $50M–$300M
    NANO = "nano"          # < $50M
    NA = "na"


class CreditRating(str, Enum):
    AAA = "AAA"
    AA_PLUS = "AA+"
    AA = "AA"
    AA_MINUS = "AA-"
    A_PLUS = "A+"
    A = "A"
    A_MINUS = "A-"
    BBB_PLUS = "BBB+"
    BBB = "BBB"
    BBB_MINUS = "BBB-"
    BB_PLUS = "BB+"
    BB = "BB"
    BB_MINUS = "BB-"
    B_PLUS = "B+"
    B = "B"
    B_MINUS = "B-"
    CCC = "CCC"
    CC = "CC"
    C = "C"
    D = "D"
    NR = "NR"


# ---------------------------------------------------------------------------
# AssetMetadata dataclass
# ---------------------------------------------------------------------------

@dataclass
class AssetMetadata:
    """Complete metadata record for a multi-asset instrument.

    Attributes:
        asset_id: Internal UUID identifier.
        ticker: Primary ticker symbol (e.g. AAPL, BTC-USD).
        name: Full instrument name.
        asset_type: AssetType classification.
        exchange: Primary listing exchange.
        currency: Trading currency.
        country: Domicile country.
        sector: GICS-style sector.
        industry: Sub-sector industry.
        market_cap_bucket: Size bucket for equities.
        isin: ISIN identifier (12-char).
        cusip: CUSIP identifier (9-char).
        sedol: SEDOL identifier (7-char).
        figi: Bloomberg FIGI.
        description: Free-text description.
        is_active: Whether the instrument is actively trading.
        credit_rating: For bonds — S&P-style credit rating.
        maturity_date: For bonds/options/futures — ISO date string.
        underlying: For derivatives — underlying asset ticker.
        metadata: Arbitrary key-value bag for additional properties.
    """
    asset_id: str
    ticker: str
    name: str
    asset_type: AssetType
    exchange: Exchange = Exchange.UNKNOWN
    currency: Currency = Currency.USD
    country: Country = Country.US
    sector: Sector = Sector.UNKNOWN
    industry: Industry = Industry.UNKNOWN
    market_cap_bucket: MarketCapBucket = MarketCapBucket.NA
    isin: Optional[str] = None
    cusip: Optional[str] = None
    sedol: Optional[str] = None
    figi: Optional[str] = None
    description: str = ""
    is_active: bool = True
    credit_rating: Optional[CreditRating] = None
    maturity_date: Optional[str] = None
    underlying: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "asset_id": self.asset_id,
            "ticker": self.ticker,
            "name": self.name,
            "asset_type": self.asset_type.value,
            "exchange": self.exchange.value,
            "currency": self.currency.value,
            "country": self.country.value,
            "sector": self.sector.value,
            "industry": self.industry.value,
            "market_cap_bucket": self.market_cap_bucket.value,
            "isin": self.isin,
            "cusip": self.cusip,
            "sedol": self.sedol,
            "figi": self.figi,
            "description": self.description,
            "is_active": self.is_active,
            "credit_rating": self.credit_rating.value if self.credit_rating else None,
            "maturity_date": self.maturity_date,
            "underlying": self.underlying,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# AssetRegistry
# ---------------------------------------------------------------------------

class AssetRegistry:
    """Institutional multi-asset instrument registry.

    Provides O(1) ticker/ISIN/CUSIP lookup and filtered list queries.
    All mutations are in-memory and thread-safe for single-threaded use.
    """

    def __init__(self) -> None:
        self._by_id: Dict[str, AssetMetadata] = {}
        self._by_ticker: Dict[str, str] = {}      # ticker -> asset_id
        self._by_isin: Dict[str, str] = {}         # isin -> asset_id
        self._by_cusip: Dict[str, str] = {}        # cusip -> asset_id
        self._by_sedol: Dict[str, str] = {}        # sedol -> asset_id
        self._by_figi: Dict[str, str] = {}         # figi -> asset_id

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        ticker: str,
        name: str,
        asset_type: AssetType,
        *,
        exchange: Exchange = Exchange.UNKNOWN,
        currency: Currency = Currency.USD,
        country: Country = Country.US,
        sector: Sector = Sector.UNKNOWN,
        industry: Industry = Industry.UNKNOWN,
        market_cap_bucket: MarketCapBucket = MarketCapBucket.NA,
        isin: Optional[str] = None,
        cusip: Optional[str] = None,
        sedol: Optional[str] = None,
        figi: Optional[str] = None,
        description: str = "",
        is_active: bool = True,
        credit_rating: Optional[CreditRating] = None,
        maturity_date: Optional[str] = None,
        underlying: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        asset_id: Optional[str] = None,
    ) -> AssetMetadata:
        """Register a new instrument in the registry.

        Args:
            ticker: Primary ticker symbol.
            name: Full instrument name.
            asset_type: Asset classification.
            exchange: Primary listing exchange.
            currency: Trading currency.
            country: Domicile country.
            sector: GICS sector.
            industry: Sub-sector industry.
            market_cap_bucket: Market cap size bucket.
            isin: ISIN identifier.
            cusip: CUSIP identifier.
            sedol: SEDOL identifier.
            figi: Bloomberg FIGI.
            description: Free-text description.
            is_active: Whether actively trading.
            credit_rating: Credit rating (bonds).
            maturity_date: Maturity/expiry ISO date.
            underlying: Underlying ticker (derivatives).
            metadata: Additional key-value properties.
            asset_id: Explicit ID (auto-generated if None).

        Returns:
            Registered AssetMetadata instance.
        """
        aid = asset_id or str(uuid.uuid4())
        asset = AssetMetadata(
            asset_id=aid,
            ticker=ticker.upper(),
            name=name,
            asset_type=asset_type,
            exchange=exchange,
            currency=currency,
            country=country,
            sector=sector,
            industry=industry,
            market_cap_bucket=market_cap_bucket,
            isin=isin,
            cusip=cusip,
            sedol=sedol,
            figi=figi,
            description=description,
            is_active=is_active,
            credit_rating=credit_rating,
            maturity_date=maturity_date,
            underlying=underlying,
            metadata=metadata or {},
        )
        self._by_id[aid] = asset
        self._by_ticker[ticker.upper()] = aid
        if isin:
            self._by_isin[isin.upper()] = aid
        if cusip:
            self._by_cusip[cusip.upper()] = aid
        if sedol:
            self._by_sedol[sedol.upper()] = aid
        if figi:
            self._by_figi[figi.upper()] = aid
        return asset

    def update(self, asset_id: str, **fields: Any) -> Optional[AssetMetadata]:
        """Update mutable fields on a registered asset.

        Args:
            asset_id: Target asset UUID.
            **fields: Field name -> new value mappings.

        Returns:
            Updated AssetMetadata, or None if not found.
        """
        asset = self._by_id.get(asset_id)
        if asset is None:
            return None
        for k, v in fields.items():
            if hasattr(asset, k):
                object.__setattr__(asset, k, v)
        return asset

    def deactivate(self, ticker: str) -> bool:
        """Mark an asset as inactive.

        Args:
            ticker: Ticker symbol to deactivate.

        Returns:
            True if found and deactivated, False otherwise.
        """
        aid = self._by_ticker.get(ticker.upper())
        if aid is None:
            return False
        self._by_id[aid].is_active = False
        return True

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get_by_ticker(self, ticker: str) -> Optional[AssetMetadata]:
        """Return asset by ticker symbol (case-insensitive).

        Args:
            ticker: Ticker symbol.

        Returns:
            AssetMetadata or None.
        """
        aid = self._by_ticker.get(ticker.upper())
        return self._by_id.get(aid) if aid else None

    def get_by_id(self, asset_id: str) -> Optional[AssetMetadata]:
        """Return asset by internal UUID.

        Args:
            asset_id: Asset UUID.

        Returns:
            AssetMetadata or None.
        """
        return self._by_id.get(asset_id)

    def get_by_isin(self, isin: str) -> Optional[AssetMetadata]:
        """Return asset by ISIN.

        Args:
            isin: 12-character ISIN.

        Returns:
            AssetMetadata or None.
        """
        aid = self._by_isin.get(isin.upper())
        return self._by_id.get(aid) if aid else None

    def get_by_cusip(self, cusip: str) -> Optional[AssetMetadata]:
        """Return asset by CUSIP.

        Args:
            cusip: 9-character CUSIP.

        Returns:
            AssetMetadata or None.
        """
        aid = self._by_cusip.get(cusip.upper())
        return self._by_id.get(aid) if aid else None

    def get_by_sedol(self, sedol: str) -> Optional[AssetMetadata]:
        """Return asset by SEDOL.

        Args:
            sedol: 7-character SEDOL.

        Returns:
            AssetMetadata or None.
        """
        aid = self._by_sedol.get(sedol.upper())
        return self._by_id.get(aid) if aid else None

    # ------------------------------------------------------------------
    # Filtered queries
    # ------------------------------------------------------------------

    def filter(
        self,
        *,
        asset_type: Optional[AssetType] = None,
        exchange: Optional[Exchange] = None,
        sector: Optional[Sector] = None,
        country: Optional[Country] = None,
        currency: Optional[Currency] = None,
        industry: Optional[Industry] = None,
        market_cap_bucket: Optional[MarketCapBucket] = None,
        is_active: Optional[bool] = None,
        credit_rating: Optional[CreditRating] = None,
    ) -> List[AssetMetadata]:
        """Return filtered list of assets.

        Args:
            asset_type: Filter by asset type.
            exchange: Filter by exchange.
            sector: Filter by sector.
            country: Filter by country.
            currency: Filter by currency.
            industry: Filter by industry.
            market_cap_bucket: Filter by market cap bucket.
            is_active: Filter by active status.
            credit_rating: Filter by credit rating.

        Returns:
            Matching AssetMetadata records.
        """
        result = list(self._by_id.values())
        if asset_type is not None:
            result = [a for a in result if a.asset_type == asset_type]
        if exchange is not None:
            result = [a for a in result if a.exchange == exchange]
        if sector is not None:
            result = [a for a in result if a.sector == sector]
        if country is not None:
            result = [a for a in result if a.country == country]
        if currency is not None:
            result = [a for a in result if a.currency == currency]
        if industry is not None:
            result = [a for a in result if a.industry == industry]
        if market_cap_bucket is not None:
            result = [a for a in result if a.market_cap_bucket == market_cap_bucket]
        if is_active is not None:
            result = [a for a in result if a.is_active == is_active]
        if credit_rating is not None:
            result = [a for a in result if a.credit_rating == credit_rating]
        return result

    def search(self, query: str, limit: int = 20) -> List[AssetMetadata]:
        """Full-text search across ticker, name, ISIN, and description.

        Args:
            query: Case-insensitive search string.
            limit: Maximum results.

        Returns:
            Matching assets sorted by ticker.
        """
        q = query.lower()
        matches = [
            a for a in self._by_id.values()
            if q in a.ticker.lower()
            or q in a.name.lower()
            or (a.isin and q in a.isin.lower())
            or q in a.description.lower()
        ]
        return sorted(matches, key=lambda a: a.ticker)[:limit]

    def all_assets(self) -> List[AssetMetadata]:
        """Return all registered assets.

        Returns:
            List of all AssetMetadata records.
        """
        return list(self._by_id.values())

    def statistics(self) -> Dict[str, Any]:
        """Aggregate statistics across the registry.

        Returns:
            Dict with totals by asset type, sector, country, exchange, and activity.
        """
        assets = list(self._by_id.values())
        by_type: Dict[str, int] = {}
        by_sector: Dict[str, int] = {}
        by_country: Dict[str, int] = {}
        by_exchange: Dict[str, int] = {}
        active = 0
        for a in assets:
            by_type[a.asset_type.value] = by_type.get(a.asset_type.value, 0) + 1
            by_sector[a.sector.value] = by_sector.get(a.sector.value, 0) + 1
            by_country[a.country.value] = by_country.get(a.country.value, 0) + 1
            by_exchange[a.exchange.value] = by_exchange.get(a.exchange.value, 0) + 1
            if a.is_active:
                active += 1
        return {
            "total": len(assets),
            "active": active,
            "inactive": len(assets) - active,
            "by_type": by_type,
            "by_sector": by_sector,
            "by_country": by_country,
            "by_exchange": by_exchange,
        }

    def tickers(self, asset_type: Optional[AssetType] = None) -> List[str]:
        """Return sorted list of tickers, optionally filtered by type.

        Args:
            asset_type: Optional filter.

        Returns:
            Sorted ticker list.
        """
        assets = self.filter(asset_type=asset_type) if asset_type else self.all_assets()
        return sorted(a.ticker for a in assets)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_registry: Optional[AssetRegistry] = None


def get_asset_registry() -> AssetRegistry:
    """Return the process-level singleton AssetRegistry.

    Returns:
        Shared AssetRegistry instance.
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = AssetRegistry()
    return _default_registry
