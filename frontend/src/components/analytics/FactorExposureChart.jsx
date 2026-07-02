/**
 * FactorExposureChart — Horizontal bar chart of factor betas.
 */
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";

export default function FactorExposureChart({ result }) {
  if (!result || !result.exposures) return null;

  const data = result.exposures
    .filter((e) => e.beta != null)
    .map((e) => ({
      factor: e.factor,
      beta: parseFloat(e.beta.toFixed(4)),
      significant: e.significant,
      t_stat: e.t_stat,
      p_value: e.p_value,
    }));

  if (!data.length) return <div style={styles.empty}>No factor data available.</div>;

  return (
    <div>
      <div style={styles.header}>
        <div style={styles.title}>Factor Exposures (Beta)</div>
        <div style={styles.metaRow}>
          <span style={styles.meta}>R²: {result.r_squared?.toFixed(4) ?? "—"}</span>
          <span style={styles.meta}>Adj. R²: {result.adj_r_squared?.toFixed(4) ?? "—"}</span>
          <span style={styles.meta}>
            Alpha (Ann.): {" "}
            <span style={{ color: (result.alpha_annual ?? 0) > 0 ? "#4ade80" : "#f87171" }}>
              {result.alpha_annual != null ? `${(result.alpha_annual * 100).toFixed(3)}%` : "—"}
            </span>
          </span>
          <span style={styles.meta}>N obs: {result.n_obs}</span>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={Math.max(160, data.length * 34)}>
        <BarChart layout="vertical" data={data} margin={{ top: 0, right: 30, left: 80, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e2230" horizontal={false} />
          <XAxis type="number" tick={{ fill: "#475569", fontSize: 10 }} domain={["auto", "auto"]} />
          <YAxis type="category" dataKey="factor" tick={{ fill: "#94a3b8", fontSize: 11 }} width={80} />
          <ReferenceLine x={0} stroke="#334155" strokeWidth={1} />
          <Tooltip
            contentStyle={{ background: "#0d1117", border: "1px solid #1e2230", fontSize: 12 }}
            formatter={(value, name, props) => [
              `β = ${value.toFixed(4)}  (t=${props.payload.t_stat?.toFixed(2)}, p=${props.payload.p_value?.toFixed(3)})`,
              "Beta",
            ]}
          />
          <Bar dataKey="beta" radius={[0, 3, 3, 0]}>
            {data.map((d, i) => (
              <Cell
                key={i}
                fill={d.beta > 0 ? "#2563eb" : "#7c3aed"}
                opacity={d.significant ? 1.0 : 0.4}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div style={styles.legend}>
        <span style={{ ...styles.legendItem, opacity: 1 }}>■ Significant (p&lt;0.05)</span>
        <span style={{ ...styles.legendItem, opacity: 0.4 }}>■ Not significant</span>
      </div>
    </div>
  );
}

const styles = {
  header: { marginBottom: 12 },
  title: { fontSize: 11, fontWeight: 700, color: "#475569", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 6 },
  metaRow: { display: "flex", gap: 16, flexWrap: "wrap" },
  meta: { fontSize: 11, color: "#64748b" },
  legend: { marginTop: 10, display: "flex", gap: 16 },
  legendItem: { fontSize: 10, color: "#94a3b8" },
  empty: { color: "#334155", fontSize: 13, padding: "12px 0" },
};
