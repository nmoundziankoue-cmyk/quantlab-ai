/**
 * MonteCarloFanChart — Area chart with percentile confidence bands.
 */
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

function buildChartData(percentilePaths) {
  const keys = Object.keys(percentilePaths);
  if (!keys.length) return [];
  const len = percentilePaths[keys[0]].length;
  return Array.from({ length: len }, (_, i) => {
    const point = { day: i };
    keys.forEach((k) => { point[k] = percentilePaths[k][i]; });
    return point;
  });
}

function fmtUSD(v) {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
  return `$${v.toFixed(0)}`;
}

export default function MonteCarloFanChart({ result }) {
  if (!result || !result.percentile_paths) return null;

  const paths = result.percentile_paths;
  const data = buildChartData(paths);
  const hasP10 = !!paths.p10;

  return (
    <div>
      <div style={styles.title}>Monte Carlo Projection — {result.n_simulations.toLocaleString()} Simulations</div>

      {/* Summary stats */}
      <div style={styles.statsRow}>
        {[
          { label: "Expected Final", value: fmtUSD(result.expected_final_value), color: "#4ade80" },
          { label: "Prob. of Loss", value: `${(result.prob_loss * 100).toFixed(1)}%`, color: result.prob_loss > 0.3 ? "#f87171" : "#94a3b8" },
          { label: "Implied Annual Ret.", value: `${(result.implied_annual_return * 100).toFixed(2)}%`, color: (result.implied_annual_return ?? 0) > 0 ? "#4ade80" : "#f87171" },
          { label: "Model", value: result.model.toUpperCase(), color: "#93c5fd" },
        ].map((s) => (
          <div key={s.label} style={styles.stat}>
            <div style={styles.statLabel}>{s.label}</div>
            <div style={{ ...styles.statValue, color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={data} margin={{ top: 10, right: 20, bottom: 0, left: 20 }}>
          <defs>
            <linearGradient id="mcP95" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#2563eb" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#2563eb" stopOpacity={0.0} />
            </linearGradient>
            <linearGradient id="mcP25" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#2563eb" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#2563eb" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e2230" />
          <XAxis dataKey="day" tick={{ fill: "#475569", fontSize: 10 }} tickFormatter={(v) => `D${v}`} />
          <YAxis tick={{ fill: "#475569", fontSize: 10 }} tickFormatter={fmtUSD} />
          <Tooltip
            contentStyle={{ background: "#0d1117", border: "1px solid #1e2230", fontSize: 11 }}
            formatter={(value, name) => [fmtUSD(value), name.toUpperCase()]}
          />
          {/* Outer band */}
          {paths.p95 && paths.p5 && (
            <Area type="monotone" dataKey="p95" stroke="none" fill="url(#mcP95)" name="p95" />
          )}
          {/* Inner band */}
          {(paths.p75 || paths.p25) && (
            <Area type="monotone" dataKey="p75" stroke="none" fill="url(#mcP25)" name="p75" />
          )}
          {/* Median */}
          {paths.p50 && (
            <Area type="monotone" dataKey="p50" stroke="#2563eb" strokeWidth={2} fill="none" name="p50" dot={false} />
          )}
          {/* Downside */}
          {paths.p5 && (
            <Area type="monotone" dataKey="p5" stroke="#f87171" strokeWidth={1} strokeDasharray="4 2" fill="none" name="p5" dot={false} />
          )}
          {paths.p10 && (
            <Area type="monotone" dataKey="p10" stroke="#f97316" strokeWidth={1} strokeDasharray="4 2" fill="none" name="p10" dot={false} />
          )}
        </AreaChart>
      </ResponsiveContainer>

      {/* Terminal value table */}
      {result.final_value_stats && (
        <div style={styles.terminalRow}>
          {Object.entries(result.final_value_stats).map(([k, v]) => (
            <div key={k} style={styles.terminalItem}>
              <div style={styles.termLabel}>{k.toUpperCase()}</div>
              <div style={styles.termValue}>{fmtUSD(v)}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const styles = {
  title: { fontSize: 11, fontWeight: 700, color: "#475569", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 10 },
  statsRow: { display: "flex", gap: 16, marginBottom: 16, flexWrap: "wrap" },
  stat: { background: "#0d1117", border: "1px solid #1e2230", borderRadius: 8, padding: "10px 14px", flex: "1 1 140px" },
  statLabel: { fontSize: 10, color: "#475569", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" },
  statValue: { fontSize: 18, fontWeight: 700, marginTop: 4 },
  terminalRow: { display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12, borderTop: "1px solid #1e2230", paddingTop: 10 },
  terminalItem: { flex: "1 1 80px", textAlign: "center" },
  termLabel: { fontSize: 9, color: "#334155", fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase" },
  termValue: { fontSize: 12, color: "#94a3b8", fontWeight: 600, marginTop: 2 },
};
