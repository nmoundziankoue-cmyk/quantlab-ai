function fmtUSD(v) {
  if (v == null) return "—";
  const n = Number(v);
  return (n < 0 ? "-$" : "$") + Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtPct(v) {
  if (v == null) return "—";
  return Number(v).toFixed(2) + "%";
}

export default function PnLCard({ account }) {
  if (!account) {
    return (
      <div style={styles.card}>
        <div style={styles.label}>P&amp;L Summary</div>
        <div style={styles.empty}>No account selected</div>
      </div>
    );
  }

  const totalPnL = Number(account.total_equity) - Number(account.initial_cash);
  const pnlPct = (totalPnL / Number(account.initial_cash)) * 100;
  const isPositive = totalPnL >= 0;

  return (
    <div style={styles.card}>
      <div style={styles.label}>P&amp;L Summary</div>
      <div style={{ ...styles.pnlValue, color: isPositive ? "#4ade80" : "#f87171" }}>
        {fmtUSD(totalPnL)}
        <span style={{ ...styles.pnlPct, color: isPositive ? "#4ade80" : "#f87171" }}>
          {" "}({isPositive ? "+" : ""}{fmtPct(pnlPct)})
        </span>
      </div>
      <div style={styles.row}>
        <div style={styles.stat}>
          <div style={styles.statLabel}>Total Equity</div>
          <div style={styles.statValue}>{fmtUSD(account.total_equity)}</div>
        </div>
        <div style={styles.stat}>
          <div style={styles.statLabel}>Initial Capital</div>
          <div style={styles.statValue}>{fmtUSD(account.initial_cash)}</div>
        </div>
      </div>
    </div>
  );
}

const styles = {
  card: {
    background: "#111318",
    border: "1px solid #1e2230",
    borderRadius: 8,
    padding: "16px 20px",
  },
  label: { fontSize: 11, fontWeight: 600, letterSpacing: "0.06em", color: "#475569", marginBottom: 8, textTransform: "uppercase" },
  empty: { color: "#475569", fontSize: 13 },
  pnlValue: { fontSize: 22, fontWeight: 700, marginBottom: 12, fontVariantNumeric: "tabular-nums" },
  pnlPct: { fontSize: 14, fontWeight: 600 },
  row: { display: "flex", gap: 24 },
  stat: {},
  statLabel: { fontSize: 11, color: "#475569", marginBottom: 2 },
  statValue: { fontSize: 14, fontWeight: 600, color: "#cbd5e1", fontVariantNumeric: "tabular-nums" },
};
