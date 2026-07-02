/**
 * EfficientFrontierChart — Recharts scatter plot of the efficient frontier.
 */
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceDot,
} from "recharts";

function fmtPct(v) {
  return `${(v * 100).toFixed(2)}%`;
}

export default function EfficientFrontierChart({ points, optimizedPoint }) {
  if (!points || points.length === 0) return null;

  const data = points.map((p) => ({
    x: parseFloat((p.expected_volatility * 100).toFixed(3)),
    y: parseFloat((p.expected_return * 100).toFixed(3)),
    sharpe: p.sharpe_ratio,
  }));

  const optPoint = optimizedPoint
    ? {
        x: parseFloat((optimizedPoint.expected_volatility * 100).toFixed(3)),
        y: parseFloat((optimizedPoint.expected_return * 100).toFixed(3)),
      }
    : null;

  return (
    <div>
      <div style={styles.title}>Efficient Frontier</div>
      <ResponsiveContainer width="100%" height={300}>
        <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e2230" />
          <XAxis
            dataKey="x"
            name="Volatility"
            tickFormatter={(v) => `${v}%`}
            tick={{ fill: "#475569", fontSize: 10 }}
            label={{ value: "Volatility (%)", position: "insideBottom", offset: -10, fill: "#475569", fontSize: 10 }}
          />
          <YAxis
            dataKey="y"
            name="Return"
            tickFormatter={(v) => `${v}%`}
            tick={{ fill: "#475569", fontSize: 10 }}
            label={{ value: "Return (%)", angle: -90, position: "insideLeft", fill: "#475569", fontSize: 10 }}
          />
          <Tooltip
            cursor={{ strokeDasharray: "3 3" }}
            contentStyle={{ background: "#0d1117", border: "1px solid #1e2230", fontSize: 12 }}
            formatter={(value, name) => [`${value}%`, name]}
          />
          <Scatter name="Frontier" data={data} fill="#2563eb" opacity={0.7} r={3} line={{ stroke: "#2563eb", strokeWidth: 1.5 }} />
          {optPoint && (
            <ReferenceDot
              x={optPoint.x}
              y={optPoint.y}
              r={7}
              fill="#f59e0b"
              stroke="#fff"
              strokeWidth={1.5}
              label={{ value: "Opt", fill: "#fff", fontSize: 9, fontWeight: 700 }}
            />
          )}
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}

const styles = {
  title: { fontSize: 11, fontWeight: 700, color: "#475569", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 10 },
};
