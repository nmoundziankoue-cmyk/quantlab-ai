import { useState } from "react";

const COL = [
  { key: "ticker", label: "Ticker" },
  { key: "quantity", label: "Qty", align: "right" },
  { key: "avg_cost", label: "Avg Cost", align: "right" },
  { key: "current_price", label: "Price", align: "right" },
  { key: "market_value", label: "Mkt Value", align: "right" },
  { key: "unrealized_pnl", label: "Unr. P&L", align: "right" },
  { key: "unrealized_pnl_pct", label: "P&L %", align: "right" },
  { key: "weight_pct", label: "Weight", align: "right" },
];

function fmt(val, key) {
  if (val == null) return "—";
  if (["market_value", "avg_cost", "current_price", "unrealized_pnl"].includes(key))
    return "$" + val.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (["unrealized_pnl_pct", "weight_pct"].includes(key))
    return (val >= 0 ? "+" : "") + val.toFixed(2) + "%";
  if (key === "quantity") return val.toLocaleString("en-US", { maximumFractionDigits: 4 });
  return val;
}

export default function HoldingsTable({ holdings = [] }) {
  const [sortKey, setSortKey] = useState("market_value");
  const [sortDir, setSortDir] = useState("desc");

  const handleSort = (key) => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(key); setSortDir("desc"); }
  };

  const sorted = [...holdings].sort((a, b) => {
    const av = a[sortKey] ?? 0;
    const bv = b[sortKey] ?? 0;
    return sortDir === "asc" ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1);
  });

  if (holdings.length === 0)
    return <div style={styles.empty}>No open positions</div>;

  return (
    <div style={styles.wrapper}>
      <table style={styles.table}>
        <thead>
          <tr>
            {COL.map((c) => (
              <th
                key={c.key}
                style={{ ...styles.th, textAlign: c.align ?? "left", cursor: "pointer" }}
                onClick={() => handleSort(c.key)}
              >
                {c.label}
                {sortKey === c.key ? (sortDir === "asc" ? " ↑" : " ↓") : ""}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((h) => {
            const pnlPos = h.unrealized_pnl >= 0;
            return (
              <tr key={h.ticker} style={styles.tr}>
                {COL.map((c) => (
                  <td
                    key={c.key}
                    style={{
                      ...styles.td,
                      textAlign: c.align ?? "left",
                      color:
                        c.key === "ticker"
                          ? "#93c5fd"
                          : ["unrealized_pnl", "unrealized_pnl_pct"].includes(c.key)
                          ? pnlPos ? "#4ade80" : "#f87171"
                          : undefined,
                      fontWeight: c.key === "ticker" ? 600 : undefined,
                    }}
                  >
                    {fmt(h[c.key], c.key)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

const styles = {
  wrapper: { overflowX: "auto" },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 13 },
  th: {
    padding: "10px 14px",
    color: "#475569",
    fontWeight: 600,
    fontSize: 11,
    letterSpacing: "0.06em",
    borderBottom: "1px solid #1e2230",
    background: "#0d0f14",
    userSelect: "none",
  },
  tr: { borderBottom: "1px solid #111623" },
  td: { padding: "11px 14px", color: "#cbd5e1" },
  empty: { color: "#475569", fontSize: 13, padding: "24px 16px" },
};
