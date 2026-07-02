function fmtUSD(v) {
  if (v == null) return "—";
  return "$" + Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function BuyingPowerCard({ account }) {
  if (!account) {
    return (
      <div style={styles.card}>
        <div style={styles.label}>Account</div>
        <div style={styles.empty}>No account selected</div>
      </div>
    );
  }

  const cashUsed = Number(account.total_equity) - Number(account.cash_balance);
  const utilization = account.total_equity > 0 ? (cashUsed / Number(account.total_equity)) * 100 : 0;

  return (
    <div style={styles.card}>
      <div style={styles.label}>Account — {account.name}</div>
      <div style={styles.bpValue}>{fmtUSD(account.buying_power)}</div>
      <div style={styles.bpSub}>Buying Power Available</div>
      <div style={styles.barWrap}>
        <div style={{ ...styles.bar, width: `${Math.min(utilization, 100).toFixed(1)}%` }} />
      </div>
      <div style={styles.row}>
        <div style={styles.stat}>
          <div style={styles.statLabel}>Cash Balance</div>
          <div style={styles.statValue}>{fmtUSD(account.cash_balance)}</div>
        </div>
        <div style={styles.stat}>
          <div style={styles.statLabel}>Invested</div>
          <div style={styles.statValue}>{fmtUSD(cashUsed)}</div>
        </div>
        <div style={styles.stat}>
          <div style={styles.statLabel}>Utilization</div>
          <div style={styles.statValue}>{utilization.toFixed(1)}%</div>
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
  bpValue: { fontSize: 22, fontWeight: 700, color: "#60a5fa", fontVariantNumeric: "tabular-nums", marginBottom: 2 },
  bpSub: { fontSize: 11, color: "#475569", marginBottom: 10 },
  barWrap: { height: 4, background: "#1e2230", borderRadius: 2, marginBottom: 12, overflow: "hidden" },
  bar: { height: "100%", background: "#2563eb", borderRadius: 2, transition: "width 0.3s" },
  row: { display: "flex", gap: 24 },
  stat: {},
  statLabel: { fontSize: 11, color: "#475569", marginBottom: 2 },
  statValue: { fontSize: 13, fontWeight: 600, color: "#cbd5e1", fontVariantNumeric: "tabular-nums" },
};
