/**
 * BacktestHistory
 *
 * Compact sortable list of all stored backtests.
 * Clicking a row loads the full result into the parent.
 */

import { useBacktestList, useDeleteBacktest } from "../../hooks/useResearch";

function fmtPct(v) {
  if (v === null || v === undefined) return "—";
  const n = Number(v);
  return (n > 0 ? "+" : "") + n.toFixed(2) + "%";
}

function colorPct(v) {
  if (v === null || v === undefined) return "#64748b";
  return Number(v) >= 0 ? "#4ade80" : "#f87171";
}

export default function BacktestHistory({ onSelect }) {
  const { data: list = [], isLoading } = useBacktestList();
  const deleteBacktest = useDeleteBacktest();

  if (isLoading) return <div style={styles.empty}>Loading history…</div>;
  if (!list.length) return <div style={styles.empty}>No backtests yet. Run one above.</div>;

  const handleDelete = (e, id) => {
    e.stopPropagation();
    if (window.confirm("Delete this backtest record?")) {
      deleteBacktest.mutate(id);
    }
  };

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={styles.table}>
        <thead>
          <tr>
            {["Ticker", "Strategy", "Start", "End", "Return", "Sharpe", "Max DD", "Trades", "Win%", "Ran"].map((h) => (
              <th key={h} style={styles.th}>
                {h}
              </th>
            ))}
            <th style={styles.th} />
          </tr>
        </thead>
        <tbody>
          {list.map((bt, i) => (
            <tr
              key={bt.id}
              style={{ ...styles.row, background: i % 2 === 0 ? "transparent" : "#040609", cursor: "pointer" }}
              onClick={() => onSelect && onSelect(bt.id)}
            >
              <td style={{ ...styles.td, fontWeight: 600, color: "#93c5fd" }}>{bt.ticker}</td>
              <td style={styles.td}>{bt.strategy_name.replace(/_/g, " ")}</td>
              <td style={styles.td}>{bt.start_date}</td>
              <td style={styles.td}>{bt.end_date}</td>
              <td style={{ ...styles.td, color: colorPct(bt.total_return_pct), fontWeight: 600 }}>
                {fmtPct(bt.total_return_pct)}
              </td>
              <td style={styles.td}>{bt.sharpe_ratio !== null ? Number(bt.sharpe_ratio).toFixed(2) : "—"}</td>
              <td style={{ ...styles.td, color: "#f87171" }}>
                {bt.max_drawdown_pct !== null ? fmtPct(bt.max_drawdown_pct) : "—"}
              </td>
              <td style={styles.td}>{bt.total_trades ?? "—"}</td>
              <td style={styles.td}>
                {bt.win_rate_pct !== null ? Number(bt.win_rate_pct).toFixed(1) + "%" : "—"}
              </td>
              <td style={{ ...styles.td, color: "#334155", fontSize: 11 }}>
                {new Date(bt.created_at).toLocaleDateString()}
              </td>
              <td style={styles.td}>
                <button
                  style={styles.delBtn}
                  onClick={(e) => handleDelete(e, bt.id)}
                  title="Delete"
                >
                  ×
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const styles = {
  table: { width: "100%", borderCollapse: "collapse", fontSize: 12 },
  th: {
    textAlign: "left",
    padding: "6px 10px",
    color: "#475569",
    fontWeight: 600,
    fontSize: 10,
    letterSpacing: "0.06em",
    textTransform: "uppercase",
    borderBottom: "1px solid #1e2230",
  },
  td: { padding: "7px 10px", color: "#94a3b8", borderBottom: "1px solid #0d1117" },
  row: { transition: "background 0.1s" },
  delBtn: {
    background: "none",
    border: "1px solid #1e2230",
    borderRadius: 4,
    color: "#475569",
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 700,
    padding: "1px 6px",
    lineHeight: 1.4,
  },
  empty: { color: "#475569", fontSize: 13, padding: "12px 0" },
};
