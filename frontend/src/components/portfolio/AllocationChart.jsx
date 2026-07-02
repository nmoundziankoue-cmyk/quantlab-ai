import {
  Cell,
  PieChart,
  Pie,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Legend,
} from "recharts";

const COLORS = [
  "#3b82f6", "#8b5cf6", "#10b981", "#f59e0b",
  "#ef4444", "#06b6d4", "#ec4899", "#84cc16",
];

const fmtUSD = (v) =>
  "$" + Number(v).toLocaleString("en-US", { maximumFractionDigits: 0 });

export default function AllocationChart({ bySector = [], byTicker = [] }) {
  if (!byTicker.length)
    return <div style={styles.empty}>No holdings to display.</div>;

  return (
    <div style={styles.grid}>
      <div style={styles.card}>
        <div style={styles.cardTitle}>By Sector</div>
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={bySector}
              dataKey="market_value"
              nameKey="label"
              cx="50%"
              cy="50%"
              outerRadius={88}
              innerRadius={48}
              paddingAngle={2}
              label={({ label, weight_pct }) => `${label} ${weight_pct?.toFixed(1)}%`}
              labelLine={false}
            >
              {bySector.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(v) => fmtUSD(v)}
              contentStyle={{ background: "#0d0f14", border: "1px solid #1e2230", borderRadius: 6, fontSize: 12 }}
              itemStyle={{ color: "#94a3b8" }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>By Position (Market Value)</div>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={byTicker} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#111623" />
            <XAxis type="number" tickFormatter={fmtUSD} tick={{ fontSize: 11, fill: "#64748b" }} />
            <YAxis
              type="category"
              dataKey="label"
              tick={{ fontSize: 12, fill: "#94a3b8" }}
              width={54}
            />
            <Tooltip
              formatter={(v) => fmtUSD(v)}
              contentStyle={{ background: "#0d0f14", border: "1px solid #1e2230", borderRadius: 6, fontSize: 12 }}
              itemStyle={{ color: "#94a3b8" }}
            />
            <Bar dataKey="market_value" name="Mkt Value" radius={[0, 4, 4, 0]}>
              {byTicker.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

const styles = {
  grid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 },
  card: {
    background: "#0d0f14",
    border: "1px solid #1e2230",
    borderRadius: 10,
    padding: "16px 12px 12px",
  },
  cardTitle: { fontSize: 12, fontWeight: 600, color: "#64748b", letterSpacing: "0.06em", marginBottom: 12 },
  empty: { color: "#475569", fontSize: 13, padding: "24px 16px" },
};
