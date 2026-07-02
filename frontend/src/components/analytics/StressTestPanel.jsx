/**
 * StressTestPanel — Bar chart of stress scenario impacts.
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

export default function StressTestPanel({ result }) {
  if (!result) return null;

  const isDetail = !!result.asset_impacts;

  if (isDetail) {
    return <DetailView result={result} />;
  }

  // Summary view (run-all)
  return <SummaryView scenarios={result.scenarios} totalValue={result.total_portfolio_value} />;
}

function SummaryView({ scenarios, totalValue }) {
  const data = (scenarios ?? [])
    .filter((s) => s.portfolio_return_pct != null)
    .map((s) => ({
      name: s.scenario_name.replace(/\s+/g, "\n").slice(0, 24),
      return_pct: parseFloat(s.portfolio_return_pct?.toFixed(2) ?? 0),
      pnl: s.total_pnl,
    }))
    .sort((a, b) => a.return_pct - b.return_pct);

  return (
    <div>
      <div style={styles.title}>All Stress Scenarios — Portfolio Return Impact</div>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart layout="vertical" data={data} margin={{ top: 0, right: 30, left: 120, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e2230" horizontal={false} />
          <XAxis type="number" tickFormatter={(v) => `${v}%`} tick={{ fill: "#475569", fontSize: 10 }} />
          <YAxis type="category" dataKey="name" tick={{ fill: "#94a3b8", fontSize: 9 }} width={120} />
          <Tooltip
            contentStyle={{ background: "#0d1117", border: "1px solid #1e2230", fontSize: 12 }}
            formatter={(value, name) => [`${value}%`, "Return"]}
          />
          <Bar dataKey="return_pct" radius={[0, 3, 3, 0]}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.return_pct >= 0 ? "#4ade80" : "#f87171"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function DetailView({ result }) {
  const impacts = [...(result.asset_impacts ?? [])].sort((a, b) => a.pnl - b.pnl);

  return (
    <div>
      <div style={styles.title}>{result.scenario_name}</div>
      <div style={styles.meta}>{result.description}</div>

      {result.period_start && (
        <div style={styles.period}>
          Period: {result.period_start} → {result.period_end}
        </div>
      )}

      <div style={styles.summaryRow}>
        <div style={styles.summaryItem}>
          <div style={styles.summaryLabel}>Portfolio P&L</div>
          <div style={{ ...styles.summaryValue, color: result.total_pnl >= 0 ? "#4ade80" : "#f87171" }}>
            {result.total_pnl >= 0 ? "+" : ""}${result.total_pnl?.toLocaleString("en-US", { maximumFractionDigits: 0 })}
          </div>
        </div>
        <div style={styles.summaryItem}>
          <div style={styles.summaryLabel}>Portfolio Return</div>
          <div style={{ ...styles.summaryValue, color: result.portfolio_return_pct >= 0 ? "#4ade80" : "#f87171" }}>
            {result.portfolio_return_pct >= 0 ? "+" : ""}{result.portfolio_return_pct?.toFixed(2)}%
          </div>
        </div>
      </div>

      {/* Asset breakdown */}
      <table style={styles.table}>
        <thead>
          <tr>
            {["Ticker", "Weight %", "Return %", "P&L"].map((h) => (
              <th key={h} style={styles.th}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {impacts.map((a) => (
            <tr key={a.ticker}>
              <td style={{ ...styles.td, fontWeight: 700, color: "#93c5fd" }}>{a.ticker}</td>
              <td style={styles.td}>{a.weight_pct?.toFixed(1)}%</td>
              <td style={{ ...styles.td, color: (a.return_pct ?? 0) >= 0 ? "#4ade80" : "#f87171" }}>
                {a.return_pct != null ? `${a.return_pct >= 0 ? "+" : ""}${a.return_pct.toFixed(2)}%` : "—"}
              </td>
              <td style={{ ...styles.td, color: a.pnl >= 0 ? "#4ade80" : "#f87171" }}>
                {a.pnl >= 0 ? "+" : ""}${a.pnl.toLocaleString("en-US", { maximumFractionDigits: 0 })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const styles = {
  title: { fontSize: 11, fontWeight: 700, color: "#475569", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 8 },
  meta: { fontSize: 12, color: "#334155", marginBottom: 6 },
  period: { fontSize: 11, color: "#475569", marginBottom: 12 },
  summaryRow: { display: "flex", gap: 16, marginBottom: 16 },
  summaryItem: { background: "#0d1117", border: "1px solid #1e2230", borderRadius: 8, padding: "10px 14px", flex: 1 },
  summaryLabel: { fontSize: 10, color: "#475569", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" },
  summaryValue: { fontSize: 20, fontWeight: 700, marginTop: 4 },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 12, marginTop: 10 },
  th: { textAlign: "left", padding: "6px 8px", color: "#475569", fontWeight: 600, fontSize: 10, letterSpacing: "0.06em", textTransform: "uppercase", borderBottom: "1px solid #1e2230" },
  td: { padding: "7px 8px", color: "#94a3b8", borderBottom: "1px solid #0d1117" },
};
