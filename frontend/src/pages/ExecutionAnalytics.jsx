import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getExecutionAnalytics } from "../api/tradingApi";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";

function fmtUSD(v) {
  if (v == null) return "—";
  const n = Number(v);
  return (n < 0 ? "-$" : "$") + Math.abs(n).toFixed(4);
}

function fmtPct(v) {
  if (v == null) return "—";
  return Number(v).toFixed(2) + "%";
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: "#111318", border: "1px solid #1e2230", borderRadius: 6, padding: "8px 12px", fontSize: 12, color: "#e2e8f0" }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {typeof p.value === "number" ? p.value.toFixed(4) : p.value}
        </div>
      ))}
    </div>
  );
};

function MetricCard({ label, value, sub, color }) {
  return (
    <div style={styles.metricCard}>
      <div style={styles.metricLabel}>{label}</div>
      <div style={{ ...styles.metricValue, color: color || "#e2e8f0" }}>{value}</div>
      {sub && <div style={styles.metricSub}>{sub}</div>}
    </div>
  );
}

export default function ExecutionAnalytics() {
  const [since, setSince] = useState("");
  const [until, setUntil] = useState("");

  const params = { since: since || undefined, until: until || undefined };
  const { data, isLoading, error } = useQuery({
    queryKey: ["execution-analytics", params],
    queryFn: () => getExecutionAnalytics(params),
  });

  const metrics = data?.overall ?? null;
  const byTicker = data?.by_ticker ?? [];
  const slippageDist = data?.slippage_distribution ?? [];

  const slippageChartData = slippageDist.map((d) => ({
    name: d.bucket ?? d.label ?? String(d),
    slippage: typeof d === "object" ? (d.avg_slippage_bps ?? d.value ?? 0) : d,
  }));

  const tickerChartData = byTicker.slice(0, 20).map((t) => ({
    name: t.ticker,
    fill_ratio: Number(t.fill_ratio ?? 0) * 100,
    avg_slippage: Number(t.avg_slippage_bps ?? t.avg_slippage ?? 0),
    executions: t.execution_count ?? t.count ?? 0,
  }));

  return (
    <div style={styles.root}>
      <div style={styles.headerRow}>
        <div>
          <h1 style={styles.h1}>Execution Analytics</h1>
          <p style={styles.sub}>Fill quality, slippage analysis, and broker performance</p>
        </div>
        <div style={styles.dateRange}>
          <input type="date" style={styles.dateInput} value={since} onChange={(e) => setSince(e.target.value)} title="From" />
          <span style={{ color: "#475569", fontSize: 12 }}>to</span>
          <input type="date" style={styles.dateInput} value={until} onChange={(e) => setUntil(e.target.value)} title="To" />
        </div>
      </div>

      {error && <div style={styles.errorBox}>Failed to load analytics: {error.message}</div>}
      {isLoading && <div style={styles.loading}>Computing analytics…</div>}

      {metrics && (
        <div style={styles.metricsGrid}>
          <MetricCard label="Total Executions" value={metrics.total_executions ?? "—"} />
          <MetricCard label="Fill Ratio" value={fmtPct(metrics.fill_ratio ? metrics.fill_ratio * 100 : null)} color="#4ade80" />
          <MetricCard label="Avg Slippage (bps)" value={metrics.avg_slippage_bps != null ? Number(metrics.avg_slippage_bps).toFixed(2) : "—"} color="#fbbf24" />
          <MetricCard label="Total Commission" value={fmtUSD(metrics.total_commission)} color="#f87171" />
          <MetricCard label="Total Slippage Cost" value={fmtUSD(metrics.total_slippage_cost)} color="#f87171" />
          <MetricCard label="Avg Latency (ms)" value={metrics.avg_latency_ms != null ? Number(metrics.avg_latency_ms).toFixed(1) : "—"} />
          <MetricCard label="Win Rate" value={fmtPct(metrics.win_rate ? metrics.win_rate * 100 : null)} color="#4ade80" />
          <MetricCard label="Avg Fill Quality" value={metrics.avg_fill_quality != null ? Number(metrics.avg_fill_quality).toFixed(4) : "—"} color="#60a5fa" />
        </div>
      )}

      {tickerChartData.length > 0 && (
        <div style={styles.chartCard}>
          <div style={styles.chartTitle}>Fill Ratio by Ticker (%)</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={tickerChartData} margin={{ top: 4, right: 16, left: 0, bottom: 20 }}>
              <CartesianGrid stroke="#1e2230" vertical={false} />
              <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 11 }} angle={-30} textAnchor="end" interval={0} />
              <YAxis tick={{ fill: "#64748b", fontSize: 11 }} domain={[0, 100]} unit="%" />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="fill_ratio" name="Fill Ratio" radius={[3, 3, 0, 0]}>
                {tickerChartData.map((entry, index) => (
                  <Cell key={index} fill={entry.fill_ratio >= 95 ? "#16a34a" : entry.fill_ratio >= 80 ? "#d97706" : "#b91c1c"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {tickerChartData.length > 0 && (
        <div style={styles.chartCard}>
          <div style={styles.chartTitle}>Avg Slippage by Ticker (bps)</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={tickerChartData} margin={{ top: 4, right: 16, left: 0, bottom: 20 }}>
              <CartesianGrid stroke="#1e2230" vertical={false} />
              <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 11 }} angle={-30} textAnchor="end" interval={0} />
              <YAxis tick={{ fill: "#64748b", fontSize: 11 }} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="avg_slippage" name="Avg Slippage (bps)" fill="#f59e0b" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {byTicker.length > 0 && (
        <div style={styles.tableCard}>
          <div style={styles.tableTitle}>Per-Ticker Breakdown</div>
          <div style={styles.tableWrap}>
            <table style={styles.table}>
              <thead>
                <tr>
                  {["Ticker", "Executions", "Total Qty", "Fill Ratio", "Avg Slip (bps)", "Avg Commission", "Avg Latency (ms)"].map((h) => (
                    <th key={h} style={styles.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {byTicker.map((t) => (
                  <tr key={t.ticker} style={styles.tr}>
                    <td style={{ ...styles.td, fontWeight: 700, color: "#e2e8f0", textAlign: "left" }}>{t.ticker}</td>
                    <td style={styles.td}>{t.execution_count ?? t.count ?? "—"}</td>
                    <td style={styles.td}>{t.total_quantity ? Number(t.total_quantity).toLocaleString() : "—"}</td>
                    <td style={{ ...styles.td, color: "#4ade80" }}>{fmtPct(t.fill_ratio ? t.fill_ratio * 100 : null)}</td>
                    <td style={{ ...styles.td, color: "#fbbf24" }}>{t.avg_slippage_bps != null ? Number(t.avg_slippage_bps).toFixed(2) : "—"}</td>
                    <td style={{ ...styles.td, color: "#f87171" }}>{fmtUSD(t.avg_commission)}</td>
                    <td style={styles.td}>{t.avg_latency_ms != null ? Number(t.avg_latency_ms).toFixed(1) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!isLoading && !metrics && !error && (
        <div style={styles.noData}>No execution data available. Execute trades to see analytics.</div>
      )}
    </div>
  );
}

const styles = {
  root: { padding: "28px 32px", minHeight: "100vh" },
  headerRow: { display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 24 },
  h1: { fontSize: 22, fontWeight: 700, color: "#e2e8f0", margin: "0 0 4px" },
  sub: { fontSize: 13, color: "#475569", margin: 0 },
  dateRange: { display: "flex", gap: 8, alignItems: "center" },
  dateInput: {
    background: "#111318", border: "1px solid #1e2230", borderRadius: 6,
    color: "#e2e8f0", fontSize: 13, padding: "7px 10px", outline: "none",
  },
  errorBox: { background: "#2a1a1a", border: "1px solid #b91c1c", borderRadius: 6, color: "#f87171", fontSize: 13, padding: "10px 14px", marginBottom: 16 },
  loading: { color: "#475569", fontSize: 13, padding: "48px 0", textAlign: "center" },
  metricsGrid: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 24 },
  metricCard: { background: "#111318", border: "1px solid #1e2230", borderRadius: 8, padding: "14px 18px" },
  metricLabel: { fontSize: 10, fontWeight: 600, letterSpacing: "0.06em", color: "#475569", marginBottom: 6 },
  metricValue: { fontSize: 20, fontWeight: 700, fontVariantNumeric: "tabular-nums" },
  metricSub: { fontSize: 11, color: "#475569", marginTop: 2 },
  chartCard: { background: "#111318", border: "1px solid #1e2230", borderRadius: 8, padding: "16px 20px", marginBottom: 16 },
  chartTitle: { fontSize: 13, fontWeight: 600, color: "#94a3b8", marginBottom: 12 },
  tableCard: { background: "#111318", border: "1px solid #1e2230", borderRadius: 8, overflow: "hidden", marginBottom: 16 },
  tableTitle: { fontSize: 13, fontWeight: 600, color: "#94a3b8", padding: "14px 18px", borderBottom: "1px solid #1e2230" },
  tableWrap: { overflowX: "auto" },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 13 },
  th: { padding: "10px 14px", textAlign: "right", fontSize: 10, fontWeight: 600, letterSpacing: "0.06em", color: "#475569", borderBottom: "1px solid #1e2230", whiteSpace: "nowrap" },
  tr: { borderBottom: "1px solid #0d0f14" },
  td: { padding: "9px 14px", color: "#94a3b8", textAlign: "right", whiteSpace: "nowrap", fontVariantNumeric: "tabular-nums" },
  noData: { color: "#475569", fontSize: 13, textAlign: "center", padding: "60px 0" },
};
