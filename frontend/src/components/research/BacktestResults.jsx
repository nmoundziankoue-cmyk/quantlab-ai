/**
 * BacktestResults
 *
 * Renders the full output of a completed backtest:
 *   - Equity curve (lightweight-charts area series) vs benchmark shading
 *   - Key metrics panel (Sharpe, Sortino, max drawdown, win-rate, profit factor…)
 *   - Trade journal table
 *   - Monthly returns heatmap
 */

import { useEffect, useRef } from "react";
import { createChart, CrosshairMode } from "lightweight-charts";
import MonthlyReturnsHeatmap from "./MonthlyReturnsHeatmap";

// ---------------------------------------------------------------------------
// Equity curve chart
// ---------------------------------------------------------------------------

function EquityCurveChart({ equityCurve = [], initialCapital = 100_000, height = 260 }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current || !equityCurve.length) return;

    const chart = createChart(ref.current, {
      width: ref.current.clientWidth,
      height,
      layout: { background: { color: "#080c14" }, textColor: "#64748b", fontSize: 11 },
      grid: { vertLines: { color: "#0f1520" }, horzLines: { color: "#0f1520" } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: "#1e2230" },
      timeScale: { borderColor: "#1e2230", timeVisible: true, secondsVisible: false },
    });

    const equitySeries = chart.addAreaSeries({
      lineColor: "#3b82f6",
      topColor: "rgba(59,130,246,0.2)",
      bottomColor: "rgba(59,130,246,0.01)",
      lineWidth: 2,
      title: "Portfolio",
    });

    equitySeries.setData(
      equityCurve.map((pt) => ({ time: pt.date, value: pt.equity }))
    );

    // Flat "initial capital" reference line
    const refLine = chart.addLineSeries({
      color: "#334155",
      lineWidth: 1,
      lineStyle: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    refLine.setData([
      { time: equityCurve[0].date, value: initialCapital },
      { time: equityCurve[equityCurve.length - 1].date, value: initialCapital },
    ]);

    chart.timeScale().fitContent();

    const ro = new ResizeObserver(() => chart.applyOptions({ width: ref.current?.clientWidth ?? 0 }));
    ro.observe(ref.current);

    return () => {
      ro.disconnect();
      chart.remove();
    };
  }, [equityCurve, initialCapital, height]);

  return <div ref={ref} style={{ width: "100%", height }} />;
}

// ---------------------------------------------------------------------------
// Metrics panel
// ---------------------------------------------------------------------------

function MetricBadge({ label, value, sub, positive }) {
  const color = positive === undefined ? "#cbd5e1" : positive ? "#4ade80" : "#f87171";
  return (
    <div style={mbStyles.card}>
      <div style={mbStyles.label}>{label}</div>
      <div style={{ ...mbStyles.value, color }}>{value}</div>
      {sub && <div style={mbStyles.sub}>{sub}</div>}
    </div>
  );
}

const mbStyles = {
  card: {
    background: "#0d1117",
    border: "1px solid #1e2230",
    borderRadius: 8,
    padding: "10px 14px",
    minWidth: 110,
    flex: "1 1 110px",
  },
  label: { fontSize: 10, fontWeight: 600, color: "#475569", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 4 },
  value: { fontSize: 18, fontWeight: 700 },
  sub: { fontSize: 10, color: "#334155", marginTop: 2 },
};

function MetricsPanel({ metrics, ticker, benchmark }) {
  if (!metrics) return null;

  const fmt = (v, d = 2) => (v === undefined || v === null ? "—" : Number(v).toFixed(d));
  const pct = (v) => fmt(v) + "%";
  const sign = (v) => (v > 0 ? "+" : "") + fmt(v) + "%";

  return (
    <div>
      <div style={styles.metricsRow}>
        <MetricBadge
          label="Total Return"
          value={sign(metrics.total_return_pct)}
          sub={`vs ${benchmark} ${sign(metrics.benchmark_return_pct)}`}
          positive={metrics.total_return_pct >= 0}
        />
        <MetricBadge
          label="Annual Return"
          value={sign(metrics.annual_return_pct)}
          positive={metrics.annual_return_pct >= 0}
        />
        <MetricBadge label="Sharpe" value={fmt(metrics.sharpe_ratio)} positive={metrics.sharpe_ratio >= 1} />
        <MetricBadge label="Sortino" value={fmt(metrics.sortino_ratio)} positive={metrics.sortino_ratio >= 1} />
        <MetricBadge label="Calmar" value={fmt(metrics.calmar_ratio)} positive={metrics.calmar_ratio >= 0.5} />
        <MetricBadge
          label="Max Drawdown"
          value={pct(metrics.max_drawdown_pct)}
          sub={`${metrics.max_drawdown_duration_days}d duration`}
          positive={false}
        />
        <MetricBadge label="Volatility" value={pct(metrics.volatility_pct)} />
        <MetricBadge label="Alpha" value={sign(metrics.alpha)} positive={metrics.alpha >= 0} />
        <MetricBadge label="Beta" value={fmt(metrics.beta)} />
        <MetricBadge label="Win Rate" value={pct(metrics.win_rate_pct)} positive={metrics.win_rate_pct >= 50} />
        <MetricBadge label="Profit Factor" value={fmt(metrics.profit_factor)} positive={metrics.profit_factor >= 1} />
        <MetricBadge label="Avg Win" value={sign(metrics.avg_win_pct)} positive={true} />
        <MetricBadge label="Avg Loss" value={sign(metrics.avg_loss_pct)} positive={false} />
        <MetricBadge label="Trades" value={metrics.total_trades} sub={`${metrics.winning_trades}W / ${metrics.losing_trades}L`} />
        <MetricBadge label="Avg Duration" value={`${fmt(metrics.avg_trade_duration_days, 0)}d`} />
        <MetricBadge label="Time in Market" value={pct(metrics.time_in_market_pct)} />
        <MetricBadge label="Final Equity" value={`$${Number(metrics.final_equity).toLocaleString()}`} positive={metrics.final_equity >= 0} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Trade journal
// ---------------------------------------------------------------------------

function TradeTable({ trades = [] }) {
  if (!trades.length) return <div style={styles.empty}>No completed trades.</div>;

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={styles.table}>
        <thead>
          <tr>
            {["Entry", "Exit", "Dir", "Entry $", "Exit $", "Shares", "Net P&L", "P&L %", "Days", "Commission"].map((h) => (
              <th key={h} style={styles.th}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {trades.map((t, i) => {
            const pos = t.net_pnl >= 0;
            return (
              <tr key={i} style={{ background: i % 2 === 0 ? "transparent" : "#040609" }}>
                <td style={styles.td}>{t.entry_date}</td>
                <td style={styles.td}>{t.exit_date}</td>
                <td style={{ ...styles.td, color: "#60a5fa" }}>{t.direction}</td>
                <td style={styles.td}>${Number(t.entry_price).toFixed(2)}</td>
                <td style={styles.td}>${Number(t.exit_price).toFixed(2)}</td>
                <td style={styles.td}>{Number(t.shares).toFixed(0)}</td>
                <td style={{ ...styles.td, color: pos ? "#4ade80" : "#f87171", fontWeight: 600 }}>
                  {pos ? "+" : ""}${Number(t.net_pnl).toFixed(0)}
                </td>
                <td style={{ ...styles.td, color: pos ? "#4ade80" : "#f87171" }}>
                  {pos ? "+" : ""}{Number(t.pnl_pct).toFixed(2)}%
                </td>
                <td style={styles.td}>{t.duration_days}d</td>
                <td style={{ ...styles.td, color: "#475569" }}>${Number(t.commissions_paid).toFixed(2)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function BacktestResults({ result }) {
  if (!result) return null;

  const { metrics, equity_curve, trades, monthly_returns, ticker, benchmark, strategy_name, strategy_params, initial_capital, start_date, end_date } = result;

  const paramStr = Object.entries(strategy_params || {})
    .map(([k, v]) => `${k}=${v}`)
    .join(", ");

  return (
    <div>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <div style={styles.stratTitle}>
            {strategy_name.replace(/_/g, " ").toUpperCase()}
            {paramStr && <span style={styles.params}> ({paramStr})</span>}
          </div>
          <div style={styles.meta}>
            {ticker} vs {benchmark} · {start_date} → {end_date} · Initial capital: ${Number(initial_capital).toLocaleString()}
          </div>
        </div>
        <div style={{ ...styles.statusBadge, background: result.status === "completed" ? "#14532d" : "#7f1d1d", color: result.status === "completed" ? "#4ade80" : "#fca5a5" }}>
          {result.status.toUpperCase()}
        </div>
      </div>

      {/* Equity curve */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>Equity Curve</div>
        <EquityCurveChart equityCurve={equity_curve} initialCapital={initial_capital} />
      </div>

      {/* Metrics */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>Performance Metrics</div>
        <MetricsPanel metrics={metrics} ticker={ticker} benchmark={benchmark} />
      </div>

      {/* Monthly returns */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>Monthly Returns</div>
        <MonthlyReturnsHeatmap monthlyReturns={monthly_returns} />
      </div>

      {/* Trade journal */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>Trade Journal · {trades.length} trades</div>
        <TradeTable trades={trades} />
      </div>
    </div>
  );
}

const styles = {
  header: {
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "space-between",
    marginBottom: 20,
    gap: 12,
  },
  stratTitle: { fontSize: 14, fontWeight: 700, color: "#e2e8f0", letterSpacing: "0.04em" },
  params: { fontSize: 12, fontWeight: 400, color: "#64748b" },
  meta: { fontSize: 12, color: "#475569", marginTop: 4 },
  statusBadge: { fontSize: 10, fontWeight: 700, padding: "4px 10px", borderRadius: 20, flexShrink: 0, letterSpacing: "0.06em" },
  section: { marginBottom: 24 },
  sectionTitle: { fontSize: 11, fontWeight: 700, color: "#475569", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 12 },
  metricsRow: { display: "flex", flexWrap: "wrap", gap: 8 },
  empty: { color: "#475569", fontSize: 13, padding: "12px 0" },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 12 },
  th: { textAlign: "left", padding: "6px 12px", color: "#475569", fontWeight: 600, fontSize: 10, letterSpacing: "0.06em", textTransform: "uppercase", borderBottom: "1px solid #1e2230" },
  td: { padding: "7px 12px", color: "#94a3b8", borderBottom: "1px solid #0d1117" },
};
