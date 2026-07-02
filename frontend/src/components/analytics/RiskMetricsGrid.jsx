/**
 * RiskMetricsGrid — Full suite of risk metrics in a compact grid.
 */
function Metric({ label, value, fmt = "num", color }) {
  let display = "—";
  if (value != null) {
    if (fmt === "pct") display = `${(value * 100).toFixed(2)}%`;
    else if (fmt === "pct_direct") display = `${value.toFixed(2)}%`;
    else display = typeof value === "number" ? value.toFixed(4) : String(value);
  }

  return (
    <div style={styles.metric}>
      <div style={styles.metricLabel}>{label}</div>
      <div style={{ ...styles.metricValue, color: color ?? "#e2e8f0" }}>{display}</div>
    </div>
  );
}

export default function RiskMetricsGrid({ metrics }) {
  if (!metrics) return null;

  const positiveColor = "#4ade80";
  const negativeColor = "#f87171";
  const neutralColor = "#93c5fd";

  const sections = [
    {
      title: "Return Metrics",
      items: [
        { label: "Annual Volatility", value: metrics.volatility_annual, fmt: "pct" },
        { label: "Downside Dev.", value: metrics.downside_deviation, fmt: "pct" },
        { label: "Semi-Variance", value: metrics.semi_variance, fmt: "num" },
        { label: "Max Drawdown", value: metrics.max_drawdown_pct != null ? metrics.max_drawdown_pct / 100 : null, fmt: "pct", color: negativeColor },
        { label: "Ulcer Index", value: metrics.ulcer_index, fmt: "num" },
      ],
    },
    {
      title: "Risk-Adjusted Ratios",
      items: [
        { label: "Sharpe Ratio", value: metrics.sharpe_ratio, fmt: "num", color: (metrics.sharpe_ratio ?? 0) > 0 ? positiveColor : negativeColor },
        { label: "Sortino Ratio", value: metrics.sortino_ratio, fmt: "num", color: (metrics.sortino_ratio ?? 0) > 0 ? positiveColor : negativeColor },
        { label: "Calmar Ratio", value: metrics.calmar_ratio, fmt: "num" },
        { label: "Treynor Ratio", value: metrics.treynor_ratio, fmt: "num" },
        { label: "Info. Ratio", value: metrics.information_ratio, fmt: "num" },
      ],
    },
    {
      title: "Benchmark Stats",
      items: [
        { label: "Beta", value: metrics.beta, fmt: "num", color: neutralColor },
        { label: "Alpha (Annual)", value: metrics.alpha_annual, fmt: "pct", color: (metrics.alpha_annual ?? 0) > 0 ? positiveColor : negativeColor },
        { label: "R²", value: metrics.r_squared, fmt: "num" },
        { label: "Tracking Error", value: metrics.tracking_error, fmt: "pct" },
      ],
    },
    {
      title: "Diversification",
      items: [
        { label: "HHI", value: metrics.hhi, fmt: "num" },
        { label: "Div. Ratio", value: metrics.diversification_ratio, fmt: "num", color: neutralColor },
      ],
    },
  ];

  return (
    <div style={styles.container}>
      {sections.map((sec) => (
        <div key={sec.title} style={styles.section}>
          <div style={styles.sectionTitle}>{sec.title}</div>
          <div style={styles.grid}>
            {sec.items.map((item) => (
              <Metric key={item.label} {...item} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

const styles = {
  container: { display: "flex", flexWrap: "wrap", gap: 20 },
  section: { flex: "1 1 220px", minWidth: 200 },
  sectionTitle: { fontSize: 10, fontWeight: 700, color: "#475569", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 10, paddingBottom: 6, borderBottom: "1px solid #1e2230" },
  grid: { display: "flex", flexDirection: "column", gap: 6 },
  metric: { display: "flex", justifyContent: "space-between", alignItems: "center" },
  metricLabel: { fontSize: 12, color: "#64748b" },
  metricValue: { fontSize: 13, fontWeight: 600, fontVariantNumeric: "tabular-nums" },
};
