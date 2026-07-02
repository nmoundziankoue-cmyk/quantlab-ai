/**
 * RiskContributionChart — Horizontal bar chart of per-asset risk contributions.
 * Uses Recharts BarChart.
 */
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ResponsiveContainer,
} from "recharts";

const COLORS = ["#2563eb", "#7c3aed", "#0891b2", "#059669", "#d97706", "#dc2626", "#db2777", "#65a30d"];

export default function RiskContributionChart({ riskContributions }) {
  if (!riskContributions) return null;

  const data = Object.entries(riskContributions)
    .map(([ticker, vals]) => ({
      ticker,
      pct_risk: parseFloat((vals.pct_risk * 100).toFixed(2)),
      weight: parseFloat((vals.weight * 100).toFixed(2)),
    }))
    .sort((a, b) => b.pct_risk - a.pct_risk);

  return (
    <div>
      <div style={styles.title}>Risk Contributions</div>
      <ResponsiveContainer width="100%" height={Math.max(120, data.length * 32)}>
        <BarChart layout="vertical" data={data} margin={{ top: 0, right: 20, left: 20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e2230" horizontal={false} />
          <XAxis
            type="number"
            tickFormatter={(v) => `${v}%`}
            tick={{ fill: "#475569", fontSize: 10 }}
            domain={[0, 100]}
          />
          <YAxis
            type="category"
            dataKey="ticker"
            tick={{ fill: "#94a3b8", fontSize: 11, fontWeight: 600 }}
            width={50}
          />
          <Tooltip
            contentStyle={{ background: "#0d1117", border: "1px solid #1e2230", fontSize: 12 }}
            labelStyle={{ color: "#e2e8f0", fontWeight: 700 }}
            formatter={(value, name) => [`${value}%`, name === "pct_risk" ? "Risk %" : "Weight %"]}
          />
          <Bar dataKey="pct_risk" name="Risk %" radius={[0, 3, 3, 0]}>
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

const styles = {
  title: { fontSize: 11, fontWeight: 700, color: "#475569", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 10 },
};
