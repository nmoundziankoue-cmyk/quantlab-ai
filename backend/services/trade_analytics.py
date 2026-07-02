"""M17 — Trade Analytics Engine (pure Python, in-memory).

Institutional trade-level analytics: win rate, profit factor, expectancy,
Kelly fraction, holding-period analysis, Sharpe / Sortino / Calmar / IR,
tracking error, capacity estimation, and sector / symbol attribution.

No SQLAlchemy, no external libraries — stdlib + math only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TradeRecord:
    """A single closed trade for analytics purposes.

    Args:
        trade_id: Unique identifier.
        ticker: Instrument symbol.
        side: "BUY" or "SELL_SHORT" (entry side).
        quantity: Closed quantity.
        entry_price: Average entry price.
        exit_price: Average exit price.
        entry_datetime: UTC entry datetime.
        exit_datetime: UTC exit datetime.
        commission: Total commission paid (both legs).
        pnl: Net realised P&L including commission.
        sector: Instrument sector (optional, for attribution).
        strategy_tag: Strategy / algo label (optional).
    """

    trade_id: str
    ticker: str
    side: str
    quantity: float
    entry_price: float
    exit_price: float
    entry_datetime: datetime
    exit_datetime: datetime
    commission: float = 0.0
    pnl: float = 0.0
    sector: Optional[str] = None
    strategy_tag: Optional[str] = None

    @property
    def holding_days(self) -> float:
        """Calendar days held (float to support sub-day trades)."""
        delta = self.exit_datetime - self.entry_datetime
        return delta.total_seconds() / 86_400.0

    @property
    def return_pct(self) -> float:
        """Trade return as percentage of entry value."""
        entry_value = self.entry_price * self.quantity
        if entry_value == 0:
            return 0.0
        return self.pnl / entry_value

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "trade_id": self.trade_id,
            "ticker": self.ticker,
            "side": self.side,
            "quantity": self.quantity,
            "entry_price": round(self.entry_price, 6),
            "exit_price": round(self.exit_price, 6),
            "entry_datetime": self.entry_datetime.isoformat(),
            "exit_datetime": self.exit_datetime.isoformat(),
            "commission": round(self.commission, 4),
            "pnl": round(self.pnl, 4),
            "return_pct": round(self.return_pct, 6),
            "holding_days": round(self.holding_days, 4),
            "sector": self.sector,
            "strategy_tag": self.strategy_tag,
        }


@dataclass
class TradeStatistics:
    """Aggregate statistics over a set of closed trades.

    Args:
        total_trades: Total number of closed trades.
        winning_trades: Trades with positive net P&L.
        losing_trades: Trades with negative or zero net P&L.
        win_rate: winning_trades / total_trades.
        avg_win: Average P&L of winning trades.
        avg_loss: Average P&L (absolute) of losing trades.
        avg_pnl: Average P&L across all trades.
        profit_factor: gross_profit / gross_loss.
        expectancy: Expected P&L per trade = win_rate*avg_win - loss_rate*avg_loss.
        kelly_fraction: Optimal bet fraction per Kelly criterion.
        avg_holding_days: Average holding period in calendar days.
        max_win: Largest single-trade gain.
        max_loss: Largest single-trade loss (most negative P&L).
        total_pnl: Sum of all net P&L.
        total_commission: Sum of all commissions.
        sharpe_ratio: Sharpe ratio of trade returns (assumes 0 risk-free).
        sortino_ratio: Sortino ratio (downside deviation denominator).
    """

    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    avg_pnl: float
    profit_factor: float
    expectancy: float
    kelly_fraction: float
    avg_holding_days: float
    max_win: float
    max_loss: float
    total_pnl: float
    total_commission: float
    sharpe_ratio: float
    sortino_ratio: float

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": round(self.win_rate, 6),
            "avg_win": round(self.avg_win, 4),
            "avg_loss": round(self.avg_loss, 4),
            "avg_pnl": round(self.avg_pnl, 4),
            "profit_factor": round(self.profit_factor, 4),
            "expectancy": round(self.expectancy, 4),
            "kelly_fraction": round(self.kelly_fraction, 6),
            "avg_holding_days": round(self.avg_holding_days, 4),
            "max_win": round(self.max_win, 4),
            "max_loss": round(self.max_loss, 4),
            "total_pnl": round(self.total_pnl, 4),
            "total_commission": round(self.total_commission, 4),
            "sharpe_ratio": round(self.sharpe_ratio, 6),
            "sortino_ratio": round(self.sortino_ratio, 6),
        }


@dataclass
class PortfolioPerformanceMetrics:
    """Time-series based portfolio performance metrics.

    Args:
        sharpe_ratio: Annualised Sharpe ratio.
        sortino_ratio: Annualised Sortino ratio.
        calmar_ratio: Annualised return / max drawdown.
        information_ratio: Active return / tracking error.
        tracking_error: Annualised std dev of active returns.
        max_drawdown: Maximum peak-to-trough drawdown.
        annualised_return: Compound annualised return.
        annualised_volatility: Annualised standard deviation of returns.
        total_return: Cumulative simple return.
        n_periods: Number of return observations.
    """

    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    information_ratio: float
    tracking_error: float
    max_drawdown: float
    annualised_return: float
    annualised_volatility: float
    total_return: float
    n_periods: int

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "sharpe_ratio": round(self.sharpe_ratio, 6),
            "sortino_ratio": round(self.sortino_ratio, 6),
            "calmar_ratio": round(self.calmar_ratio, 6),
            "information_ratio": round(self.information_ratio, 6),
            "tracking_error": round(self.tracking_error, 6),
            "max_drawdown": round(self.max_drawdown, 6),
            "annualised_return": round(self.annualised_return, 6),
            "annualised_volatility": round(self.annualised_volatility, 6),
            "total_return": round(self.total_return, 6),
            "n_periods": self.n_periods,
        }


@dataclass
class SectorAttribution:
    """Trade-level P&L attribution by sector.

    Args:
        sector: Sector name.
        trade_count: Number of trades in this sector.
        total_pnl: Net P&L for this sector.
        win_rate: Win rate for this sector.
        avg_pnl_per_trade: Average P&L per trade.
        pnl_contribution_pct: This sector's share of total absolute P&L.
    """

    sector: str
    trade_count: int
    total_pnl: float
    win_rate: float
    avg_pnl_per_trade: float
    pnl_contribution_pct: float

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "sector": self.sector,
            "trade_count": self.trade_count,
            "total_pnl": round(self.total_pnl, 4),
            "win_rate": round(self.win_rate, 6),
            "avg_pnl_per_trade": round(self.avg_pnl_per_trade, 4),
            "pnl_contribution_pct": round(self.pnl_contribution_pct, 4),
        }


# ---------------------------------------------------------------------------
# Trade Analytics Engine
# ---------------------------------------------------------------------------

class TradeAnalyticsEngine:
    """Institutional trade analytics engine (pure Python).

    Ingests closed TradeRecord objects and produces comprehensive statistics:
    win rate, profit factor, Kelly fraction, Sharpe/Sortino, and attribution.
    """

    # Annualisation factor: daily periods → annual
    PERIODS_PER_YEAR = 252

    def __init__(self) -> None:
        self._trades: List[TradeRecord] = []

    # ------------------------------------------------------------------
    # Trade ingestion
    # ------------------------------------------------------------------

    def add_trade(self, trade: TradeRecord) -> None:
        """Add a completed trade to the analytics store.

        Args:
            trade: Closed TradeRecord to add.
        """
        self._trades.append(trade)

    def add_trades(self, trades: List[TradeRecord]) -> None:
        """Bulk-add multiple completed trades.

        Args:
            trades: List of closed TradeRecord objects.
        """
        self._trades.extend(trades)

    def clear(self) -> None:
        """Remove all stored trades."""
        self._trades.clear()

    # ------------------------------------------------------------------
    # Trade statistics
    # ------------------------------------------------------------------

    def compute_statistics(
        self,
        trades: Optional[List[TradeRecord]] = None,
    ) -> TradeStatistics:
        """Compute aggregate statistics over a set of trades.

        Args:
            trades: Explicit trade list; if None uses all stored trades.

        Returns:
            TradeStatistics with all metrics.

        Raises:
            ValueError: If trades list is empty.
        """
        tlist = trades if trades is not None else self._trades
        if not tlist:
            raise ValueError("No trades to compute statistics from")

        wins = [t for t in tlist if t.pnl > 0]
        losses = [t for t in tlist if t.pnl <= 0]

        n = len(tlist)
        nw = len(wins)
        nl = len(losses)
        win_rate = nw / n

        avg_win = sum(t.pnl for t in wins) / nw if nw else 0.0
        avg_loss = abs(sum(t.pnl for t in losses) / nl) if nl else 0.0
        avg_pnl = sum(t.pnl for t in tlist) / n
        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        loss_rate = 1.0 - win_rate
        expectancy = win_rate * avg_win - loss_rate * avg_loss

        # Kelly fraction: W - (1-W)*(avg_loss/avg_win)
        kelly = win_rate - (loss_rate * avg_loss / avg_win) if avg_win > 0 else 0.0
        kelly = max(0.0, kelly)

        avg_holding = sum(t.holding_days for t in tlist) / n
        max_win = max(t.pnl for t in tlist)
        max_loss = min(t.pnl for t in tlist)
        total_pnl = sum(t.pnl for t in tlist)
        total_comm = sum(t.commission for t in tlist)

        returns = [t.return_pct for t in tlist]
        sharpe = self._sharpe(returns, risk_free=0.0, periods_per_year=self.PERIODS_PER_YEAR)
        sortino = self._sortino(returns, risk_free=0.0, periods_per_year=self.PERIODS_PER_YEAR)

        return TradeStatistics(
            total_trades=n,
            winning_trades=nw,
            losing_trades=nl,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            avg_pnl=avg_pnl,
            profit_factor=profit_factor,
            expectancy=expectancy,
            kelly_fraction=kelly,
            avg_holding_days=avg_holding,
            max_win=max_win,
            max_loss=max_loss,
            total_pnl=total_pnl,
            total_commission=total_comm,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
        )

    # ------------------------------------------------------------------
    # Portfolio performance (time-series)
    # ------------------------------------------------------------------

    def portfolio_performance(
        self,
        returns: List[float],
        benchmark_returns: Optional[List[float]] = None,
        risk_free: float = 0.0,
        periods_per_year: int = 252,
    ) -> PortfolioPerformanceMetrics:
        """Compute institutional portfolio performance metrics.

        Args:
            returns: List of period returns (e.g. daily; as decimal, e.g. 0.01 = 1%).
            benchmark_returns: Optional benchmark return series for IR/TE.
            risk_free: Risk-free rate per period (annualised, as decimal).
            periods_per_year: Number of periods in a year (252 for daily).

        Returns:
            PortfolioPerformanceMetrics.

        Raises:
            ValueError: If returns is empty.
        """
        if not returns:
            raise ValueError("returns cannot be empty")

        n = len(returns)
        rf_per_period = risk_free / periods_per_year
        excess = [r - rf_per_period for r in returns]
        mean_excess = sum(excess) / n
        std_excess = self._std(excess)

        sharpe = (mean_excess / std_excess * math.sqrt(periods_per_year)) if std_excess > 0 else 0.0
        sortino = self._sortino(returns, risk_free=rf_per_period, periods_per_year=periods_per_year)

        ann_return = (math.prod(1.0 + r for r in returns) ** (periods_per_year / n)) - 1.0
        ann_vol = std_excess * math.sqrt(periods_per_year)

        max_dd = self._max_drawdown(returns)
        calmar = ann_return / abs(max_dd) if max_dd != 0 else 0.0

        total_return = math.prod(1.0 + r for r in returns) - 1.0

        ir = 0.0
        te = 0.0
        if benchmark_returns and len(benchmark_returns) == n:
            active = [r - b for r, b in zip(returns, benchmark_returns)]
            mean_active = sum(active) / n
            te_period = self._std(active)
            te = te_period * math.sqrt(periods_per_year)
            ir = (mean_active * periods_per_year) / te if te > 0 else 0.0

        return PortfolioPerformanceMetrics(
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            information_ratio=ir,
            tracking_error=te,
            max_drawdown=max_dd,
            annualised_return=ann_return,
            annualised_volatility=ann_vol,
            total_return=total_return,
            n_periods=n,
        )

    # ------------------------------------------------------------------
    # Attribution
    # ------------------------------------------------------------------

    def sector_attribution(
        self,
        trades: Optional[List[TradeRecord]] = None,
    ) -> List[SectorAttribution]:
        """Compute P&L attribution by sector.

        Args:
            trades: Trade list; if None uses all stored trades.

        Returns:
            List of SectorAttribution sorted by total_pnl descending.

        Raises:
            ValueError: If no trades have sector labels.
        """
        tlist = trades if trades is not None else self._trades
        sectored = [t for t in tlist if t.sector]
        if not sectored:
            raise ValueError("No trades with sector labels")

        by_sector: Dict[str, List[TradeRecord]] = {}
        for t in sectored:
            by_sector.setdefault(t.sector, []).append(t)

        total_abs_pnl = sum(abs(t.pnl) for t in sectored) or 1.0
        result: List[SectorAttribution] = []
        for sector, sector_trades in by_sector.items():
            sector_pnl = sum(t.pnl for t in sector_trades)
            wins = sum(1 for t in sector_trades if t.pnl > 0)
            wr = wins / len(sector_trades)
            avg_pnl = sector_pnl / len(sector_trades)
            pct = abs(sector_pnl) / total_abs_pnl
            result.append(SectorAttribution(
                sector=sector,
                trade_count=len(sector_trades),
                total_pnl=sector_pnl,
                win_rate=wr,
                avg_pnl_per_trade=avg_pnl,
                pnl_contribution_pct=pct,
            ))

        return sorted(result, key=lambda s: s.total_pnl, reverse=True)

    def symbol_attribution(
        self,
        trades: Optional[List[TradeRecord]] = None,
        top_n: int = 10,
    ) -> List[Dict]:
        """Compute P&L attribution by instrument.

        Args:
            trades: Trade list; if None uses all stored trades.
            top_n: Return only the top N contributors (by abs P&L).

        Returns:
            List of dicts sorted by abs P&L descending.
        """
        tlist = trades if trades is not None else self._trades
        if not tlist:
            raise ValueError("No trades to attribute")

        by_ticker: Dict[str, List[TradeRecord]] = {}
        for t in tlist:
            by_ticker.setdefault(t.ticker, []).append(t)

        total_abs = sum(abs(t.pnl) for t in tlist) or 1.0
        result = []
        for ticker, tt in by_ticker.items():
            pnl = sum(t.pnl for t in tt)
            result.append({
                "ticker": ticker,
                "trade_count": len(tt),
                "total_pnl": round(pnl, 4),
                "win_rate": round(sum(1 for t in tt if t.pnl > 0) / len(tt), 6),
                "pnl_contribution_pct": round(abs(pnl) / total_abs, 6),
            })

        result.sort(key=lambda x: abs(x["total_pnl"]), reverse=True)
        return result[:top_n]

    # ------------------------------------------------------------------
    # Turnover and capacity
    # ------------------------------------------------------------------

    def compute_turnover(self, nav: float, trades: Optional[List[TradeRecord]] = None) -> float:
        """Compute annualised turnover as a fraction of NAV.

        Turnover = sum(abs(trade_value)) / nav.

        Args:
            nav: Net asset value.
            trades: Trade list; if None uses all stored trades.

        Returns:
            Annualised turnover fraction.
        """
        tlist = trades if trades is not None else self._trades
        if not tlist or nav <= 0:
            return 0.0
        total_traded = sum(t.quantity * t.entry_price for t in tlist)
        return total_traded / nav

    def kelly_fraction(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """Compute Kelly optimal fraction.

        Kelly = W - (1-W) * (avg_loss / avg_win)

        Args:
            win_rate: Fraction of winning trades (0–1).
            avg_win: Average gain per winning trade (positive).
            avg_loss: Average loss per losing trade (positive).

        Returns:
            Kelly fraction (clamped to [0, 1]).
        """
        if avg_win <= 0:
            return 0.0
        loss_rate = 1.0 - win_rate
        k = win_rate - loss_rate * (avg_loss / avg_win)
        return max(0.0, min(1.0, k))

    # ------------------------------------------------------------------
    # Internal math helpers
    # ------------------------------------------------------------------

    def _mean(self, values: List[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    def _std(self, values: List[float]) -> float:
        if len(values) < 2:
            return 0.0
        m = self._mean(values)
        variance = sum((v - m) ** 2 for v in values) / (len(values) - 1)
        return math.sqrt(variance)

    def _downside_std(self, values: List[float], threshold: float = 0.0) -> float:
        neg = [(v - threshold) ** 2 for v in values if v < threshold]
        if not neg:
            return 0.0
        return math.sqrt(sum(neg) / len(values))

    def _sharpe(self, returns: List[float], risk_free: float = 0.0, periods_per_year: int = 252) -> float:
        if not returns:
            return 0.0
        excess = [r - risk_free / periods_per_year for r in returns]
        std = self._std(excess)
        if std == 0:
            return 0.0
        return (self._mean(excess) / std) * math.sqrt(periods_per_year)

    def _sortino(self, returns: List[float], risk_free: float = 0.0, periods_per_year: int = 252) -> float:
        if not returns:
            return 0.0
        excess = [r - risk_free / periods_per_year for r in returns]
        downside = self._downside_std(excess)
        if downside == 0:
            return 0.0
        return (self._mean(excess) / downside) * math.sqrt(periods_per_year)

    def _max_drawdown(self, returns: List[float]) -> float:
        if not returns:
            return 0.0
        peak = 1.0
        hwm = 1.0
        max_dd = 0.0
        cumulative = 1.0
        for r in returns:
            cumulative *= (1.0 + r)
            if cumulative > hwm:
                hwm = cumulative
            dd = (cumulative - hwm) / hwm
            if dd < max_dd:
                max_dd = dd
        return max_dd

    # ------------------------------------------------------------------
    # Stored trades accessors
    # ------------------------------------------------------------------

    def get_trades(
        self,
        ticker: Optional[str] = None,
        sector: Optional[str] = None,
        strategy_tag: Optional[str] = None,
    ) -> List[TradeRecord]:
        """Query stored trades with optional filters.

        Args:
            ticker: Filter by instrument.
            sector: Filter by sector.
            strategy_tag: Filter by strategy label.

        Returns:
            Filtered list of TradeRecord sorted by exit_datetime.
        """
        result = list(self._trades)
        if ticker:
            result = [t for t in result if t.ticker == ticker.upper()]
        if sector:
            result = [t for t in result if t.sector == sector]
        if strategy_tag:
            result = [t for t in result if t.strategy_tag == strategy_tag]
        return sorted(result, key=lambda t: t.exit_datetime)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_trade_analytics: Optional[TradeAnalyticsEngine] = None


def get_trade_analytics_engine() -> TradeAnalyticsEngine:
    """Return the singleton TradeAnalyticsEngine instance.

    Returns:
        Shared TradeAnalyticsEngine instance.
    """
    global _default_trade_analytics
    if _default_trade_analytics is None:
        _default_trade_analytics = TradeAnalyticsEngine()
    return _default_trade_analytics
