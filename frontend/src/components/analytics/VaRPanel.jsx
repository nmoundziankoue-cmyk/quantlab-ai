/**
 * VaRPanel — Displays Value at Risk and CVaR metrics.
 */
export default function VaRPanel({ metrics }) {
  if (!metrics) return null;

  const rows = [
    { label: "Historical VaR 95%", value: metrics.var_historical_95, pct: true },
    { label: "Historical VaR 99%", value: metrics.var_historical_99, pct: true },
    { label: "Parametric VaR 95%", value: metrics.var_parametric_95, pct: true },
    { label: "Parametric VaR 99%", value: metrics.var_parametric_99, pct: true },
    { label: "Monte Carlo VaR 95%", value: metrics.var_monte_carlo_95, pct: true },
    { label: "CVaR / ES 95%", value: metrics.cvar_95, pct: true, highlight: true },
    { label: "CVaR / ES 99%", value: metrics.cvar_99, pct: true, highlight: true },
  ];

  return (
    <div>
      <div style={styles.title}>Value at Risk</div>
      <table style={styles.table}>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label}>
              <td style={styles.label}>{r.label}</td>
              <td style={{ ...styles.value, color: r.highlight ? "#f97316" : "#f87171" }}>
                {r.value != null ? `${(r.value * 100).toFixed(3)}%` : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const styles = {
  title: { fontSize: 11, fontWeight: 700, color: "#475569", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 10 },
  table: { width: "100%", borderCollapse: "collapse" },
  label: { padding: "5px 0", color: "#64748b", fontSize: 12 },
  value: { padding: "5px 0", fontWeight: 600, fontSize: 13, textAlign: "right", fontVariantNumeric: "tabular-nums" },
};
