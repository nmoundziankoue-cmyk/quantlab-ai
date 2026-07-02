import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getBlotter, exportBlotterCsv } from "../api/tradingApi";
import useTradingStore from "../store/useTradingStore";

function fmtUSD(v) {
  if (v == null) return "—";
  const n = Number(v);
  return (n < 0 ? "-$" : "$") + Math.abs(n).toFixed(2);
}

function fmtDate(v) {
  if (!v) return "—";
  return new Date(v).toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function fmtQty(v) {
  if (v == null) return "—";
  return Number(v).toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 4 });
}

export default function TradeBlotter() {
  const filters = useTradingStore((s) => s.blotterFilters);
  const setFilter = useTradingStore((s) => s.setBlotterFilter);
  const addNotification = useTradingStore((s) => s.addNotification);

  const [localTicker, setLocalTicker] = useState(filters.ticker || "");
  const [localSide, setLocalSide] = useState(filters.side || "");
  const [localSince, setLocalSince] = useState(filters.since || "");
  const [localUntil, setLocalUntil] = useState(filters.until || "");
  const [exportLoading, setExportLoading] = useState(false);

  const params = {
    ticker: localTicker || undefined,
    side: localSide || undefined,
    since: localSince || undefined,
    until: localUntil || undefined,
    page_size: 500,
  };

  const { data, isLoading, error } = useQuery({
    queryKey: ["blotter", params],
    queryFn: () => getBlotter(params),
  });

  const blotter = data?.executions ?? data ?? [];
  const summary = data?.summary ?? null;

  const handleExport = async () => {
    setExportLoading(true);
    try {
      const csv = await exportBlotterCsv(params);
      const blob = new Blob([csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `trade_blotter_${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      addNotification({ type: "success", message: `Exported ${Array.isArray(blotter) ? blotter.length : 0} trades` });
    } catch (err) {
      addNotification({ type: "error", message: "Export failed: " + err.message });
    } finally {
      setExportLoading(false);
    }
  };

  return (
    <div style={styles.root}>
      <div style={styles.headerRow}>
        <div>
          <h1 style={styles.h1}>Trade Blotter</h1>
          <p style={styles.sub}>Institutional execution journal — all fills</p>
        </div>
        <button style={styles.exportBtn} onClick={handleExport} disabled={exportLoading}>
          {exportLoading ? "Exporting…" : "Export CSV"}
        </button>
      </div>

      {summary && (
        <div style={styles.summaryGrid}>
          {[
            { label: "Total Fills", value: summary.total_executions ?? "—" },
            { label: "Total Shares", value: summary.total_quantity ? Number(summary.total_quantity).toLocaleString() : "—" },
            { label: "Total Value", value: fmtUSD(summary.total_gross_value) },
            { label: "Total Commission", value: fmtUSD(summary.total_commission) },
            { label: "Total Slippage", value: fmtUSD(summary.total_slippage) },
            { label: "Avg Fill Quality", value: summary.avg_fill_quality != null ? Number(summary.avg_fill_quality).toFixed(4) : "—" },
          ].map(({ label, value }) => (
            <div key={label} style={styles.summaryCard}>
              <div style={styles.summaryLabel}>{label}</div>
              <div style={styles.summaryValue}>{value}</div>
            </div>
          ))}
        </div>
      )}

      <div style={styles.filterBar}>
        <input
          style={styles.filterInput}
          placeholder="Ticker…"
          value={localTicker}
          onChange={(e) => setLocalTicker(e.target.value.toUpperCase())}
        />
        <select style={styles.filterSelect} value={localSide} onChange={(e) => setLocalSide(e.target.value)}>
          <option value="">All Sides</option>
          <option value="BUY">BUY</option>
          <option value="SELL">SELL</option>
          <option value="SELL_SHORT">SHORT</option>
          <option value="BUY_TO_COVER">COVER</option>
        </select>
        <input type="date" style={styles.filterInput} value={localSince} onChange={(e) => setLocalSince(e.target.value)} title="From date" />
        <input type="date" style={styles.filterInput} value={localUntil} onChange={(e) => setLocalUntil(e.target.value)} title="To date" />
        <span style={styles.count}>
          {isLoading ? "Loading…" : `${Array.isArray(blotter) ? blotter.length : 0} fills`}
        </span>
      </div>

      {error && <div style={styles.errorBox}>Failed to load blotter: {error.message}</div>}

      <div style={styles.tableWrap}>
        <table style={styles.table}>
          <thead>
            <tr>
              {["Time", "Ticker", "Side", "Qty", "Fill Price", "Gross Value", "Commission", "Slippage", "Net Cost", "Venue", "Latency (ms)", "Strategy"].map((h) => (
                <th key={h} style={styles.th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.isArray(blotter) && blotter.map((e) => (
              <tr key={e.id} style={styles.tr}>
                <td style={styles.tdTime}>{fmtDate(e.executed_at)}</td>
                <td style={{ ...styles.td, fontWeight: 700, color: "#e2e8f0" }}>{e.ticker}</td>
                <td style={{ ...styles.td, color: e.side?.startsWith("BUY") ? "#4ade80" : "#f87171", fontWeight: 600 }}>{e.side}</td>
                <td style={styles.td}>{fmtQty(e.quantity)}</td>
                <td style={{ ...styles.td, color: "#60a5fa" }}>{fmtUSD(e.fill_price)}</td>
                <td style={styles.td}>{fmtUSD(e.gross_value)}</td>
                <td style={{ ...styles.td, color: "#fbbf24" }}>{fmtUSD(e.commission)}</td>
                <td style={{ ...styles.td, color: "#f87171" }}>{fmtUSD(e.slippage_cost)}</td>
                <td style={{ ...styles.td, fontWeight: 600 }}>{fmtUSD(e.net_value)}</td>
                <td style={styles.td}>{e.exchange_venue || "—"}</td>
                <td style={styles.td}>{e.latency_ms != null ? Number(e.latency_ms).toFixed(1) : "—"}</td>
                <td style={{ ...styles.td, color: "#64748b" }}>{e.strategy_tag || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!isLoading && Array.isArray(blotter) && blotter.length === 0 && (
          <div style={styles.empty}>No executions in the current date range</div>
        )}
      </div>
    </div>
  );
}

const styles = {
  root: { padding: "28px 32px", minHeight: "100vh" },
  headerRow: { display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 20 },
  h1: { fontSize: 22, fontWeight: 700, color: "#e2e8f0", margin: "0 0 4px" },
  sub: { fontSize: 13, color: "#475569", margin: 0 },
  exportBtn: {
    background: "#1e2230", border: "1px solid #2d3748", borderRadius: 6,
    color: "#94a3b8", fontSize: 13, fontWeight: 600, padding: "8px 16px", cursor: "pointer",
  },
  summaryGrid: { display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 12, marginBottom: 20 },
  summaryCard: { background: "#111318", border: "1px solid #1e2230", borderRadius: 8, padding: "12px 16px" },
  summaryLabel: { fontSize: 10, fontWeight: 600, letterSpacing: "0.06em", color: "#475569", marginBottom: 4 },
  summaryValue: { fontSize: 16, fontWeight: 700, color: "#e2e8f0", fontVariantNumeric: "tabular-nums" },
  filterBar: { display: "flex", gap: 10, alignItems: "center", marginBottom: 14, flexWrap: "wrap" },
  filterInput: {
    background: "#111318", border: "1px solid #1e2230", borderRadius: 6,
    color: "#e2e8f0", fontSize: 13, padding: "7px 12px", outline: "none",
  },
  filterSelect: {
    background: "#111318", border: "1px solid #1e2230", borderRadius: 6,
    color: "#e2e8f0", fontSize: 13, padding: "7px 12px", outline: "none", cursor: "pointer",
  },
  count: { fontSize: 12, color: "#475569", marginLeft: "auto" },
  errorBox: { background: "#2a1a1a", border: "1px solid #b91c1c", borderRadius: 6, color: "#f87171", fontSize: 13, padding: "10px 14px", marginBottom: 16 },
  tableWrap: { overflowX: "auto", background: "#111318", border: "1px solid #1e2230", borderRadius: 8 },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 12 },
  th: { padding: "10px 12px", textAlign: "right", fontSize: 10, fontWeight: 600, letterSpacing: "0.06em", color: "#475569", borderBottom: "1px solid #1e2230", whiteSpace: "nowrap" },
  tr: { borderBottom: "1px solid #0d0f14" },
  td: { padding: "8px 12px", color: "#94a3b8", textAlign: "right", whiteSpace: "nowrap", fontVariantNumeric: "tabular-nums" },
  tdTime: { padding: "8px 12px", color: "#64748b", textAlign: "left", whiteSpace: "nowrap", fontSize: 11 },
  empty: { padding: "40px 0", textAlign: "center", color: "#475569", fontSize: 13 },
};
