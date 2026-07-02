function fmtUSD(v) {
  if (v == null) return "—";
  const n = Number(v);
  return (n < 0 ? "-$" : "$") + Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtQty(v) {
  if (v == null) return "—";
  return Number(v).toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 4 });
}

function fmtPct(v) {
  if (v == null) return "—";
  const n = Number(v);
  return (n >= 0 ? "+" : "") + n.toFixed(2) + "%";
}

export default function PositionsTable({ positions = [], isLoading }) {
  if (isLoading) {
    return <div style={styles.empty}>Loading positions…</div>;
  }
  if (!positions.length) {
    return <div style={styles.empty}>No open positions</div>;
  }

  return (
    <div style={styles.wrap}>
      <table style={styles.table}>
        <thead>
          <tr>
            {["Ticker", "Qty", "Avg Cost", "Market Price", "Market Value", "Unrealized P&L", "P&L %"].map((h) => (
              <th key={h} style={styles.th}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {positions.map((pos) => {
            const unrealized = pos.unrealized_pnl != null ? Number(pos.unrealized_pnl) : null;
            const pnlPct = pos.cost_basis && Number(pos.cost_basis) > 0
              ? ((unrealized / Number(pos.cost_basis)) * 100)
              : null;
            const isPos = unrealized == null || unrealized >= 0;

            return (
              <tr key={pos.id} style={styles.tr}>
                <td style={styles.tdTicker}>{pos.ticker}</td>
                <td style={styles.td}>{fmtQty(pos.quantity)}</td>
                <td style={styles.td}>{fmtUSD(pos.average_cost)}</td>
                <td style={styles.td}>{pos.market_price ? fmtUSD(pos.market_price) : "—"}</td>
                <td style={styles.td}>{pos.market_value ? fmtUSD(pos.market_value) : "—"}</td>
                <td style={{ ...styles.td, color: isPos ? "#4ade80" : "#f87171", fontWeight: 600 }}>
                  {fmtUSD(unrealized)}
                </td>
                <td style={{ ...styles.td, color: isPos ? "#4ade80" : "#f87171" }}>
                  {fmtPct(pnlPct)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

const styles = {
  wrap: { overflowX: "auto" },
  empty: { padding: "24px 0", color: "#475569", fontSize: 13, textAlign: "center" },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 13 },
  th: {
    padding: "8px 12px",
    textAlign: "right",
    fontSize: 11,
    fontWeight: 600,
    letterSpacing: "0.05em",
    color: "#475569",
    borderBottom: "1px solid #1e2230",
    whiteSpace: "nowrap",
  },
  tr: { borderBottom: "1px solid #0d0f14" },
  td: {
    padding: "9px 12px",
    textAlign: "right",
    color: "#cbd5e1",
    fontVariantNumeric: "tabular-nums",
    whiteSpace: "nowrap",
  },
  tdTicker: {
    padding: "9px 12px",
    textAlign: "left",
    color: "#e2e8f0",
    fontWeight: 600,
    whiteSpace: "nowrap",
  },
};
