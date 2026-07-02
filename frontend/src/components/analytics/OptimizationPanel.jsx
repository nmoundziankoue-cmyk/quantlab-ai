/**
 * OptimizationPanel — Portfolio optimization form + results + efficient frontier.
 */
import { useState } from "react";
import { useRunOptimization, useEfficientFrontier } from "../../hooks/useAnalytics";
import EfficientFrontierChart from "./EfficientFrontierChart";

const METHODS = [
  { key: "equal_weight", label: "Equal Weight" },
  { key: "min_variance", label: "Min Variance" },
  { key: "max_sharpe", label: "Max Sharpe" },
  { key: "risk_parity", label: "Risk Parity" },
  { key: "max_diversification", label: "Max Diversification" },
  { key: "hrp", label: "Hierarchical Risk Parity" },
];

const LOOKBACKS = [
  { value: 63, label: "3 Months" },
  { value: 126, label: "6 Months" },
  { value: 252, label: "1 Year" },
  { value: 504, label: "2 Years" },
  { value: 756, label: "3 Years" },
];

export default function OptimizationPanel({ portfolioId }) {
  const [method, setMethod] = useState("max_sharpe");
  const [lookback, setLookback] = useState(252);
  const [result, setResult] = useState(null);
  const [frontier, setFrontier] = useState(null);
  const [error, setError] = useState("");

  const runOpt = useRunOptimization(portfolioId);
  const runFrontier = useEfficientFrontier(portfolioId);

  const handleRun = async () => {
    setError("");
    try {
      const res = await runOpt.mutateAsync({ method, lookback_days: lookback });
      setResult(res);
      // Also fetch frontier
      try {
        const fr = await runFrontier.mutateAsync({ params: { method, lookback_days: lookback }, nPoints: 40 });
        setFrontier(fr);
      } catch (_) {}
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div>
      {/* Config row */}
      <div style={styles.configRow}>
        <div style={styles.field}>
          <label style={styles.label}>Method</label>
          <select style={styles.select} value={method} onChange={(e) => setMethod(e.target.value)}>
            {METHODS.map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}
          </select>
        </div>
        <div style={styles.field}>
          <label style={styles.label}>Lookback Period</label>
          <select style={styles.select} value={lookback} onChange={(e) => setLookback(Number(e.target.value))}>
            {LOOKBACKS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
          </select>
        </div>
        <button
          style={{ ...styles.btn, opacity: runOpt.isPending ? 0.6 : 1 }}
          disabled={runOpt.isPending}
          onClick={handleRun}
        >
          {runOpt.isPending ? "Optimizing…" : "Run Optimization"}
        </button>
      </div>

      {error && <div style={styles.error}>{error}</div>}

      {result && (
        <div style={styles.resultSection}>
          {/* Summary stats */}
          <div style={styles.statsRow}>
            {[
              { label: "Method", value: METHODS.find((m) => m.key === result.method)?.label ?? result.method },
              { label: "Expected Return", value: result.expected_return != null ? `${(result.expected_return * 100).toFixed(3)}%` : "—" },
              { label: "Expected Vol.", value: result.expected_volatility != null ? `${(result.expected_volatility * 100).toFixed(3)}%` : "—" },
              { label: "Sharpe Ratio", value: result.sharpe_ratio?.toFixed(4) ?? "—" },
            ].map((s) => (
              <div key={s.label} style={styles.stat}>
                <div style={styles.statLabel}>{s.label}</div>
                <div style={styles.statValue}>{s.value}</div>
              </div>
            ))}
          </div>

          {/* Weights table */}
          <div style={styles.weightsTitle}>Optimal Weights</div>
          <div style={styles.weightsGrid}>
            {Object.entries(result.weights)
              .sort(([, a], [, b]) => b - a)
              .map(([ticker, weight]) => (
                <div key={ticker} style={styles.weightItem}>
                  <div style={styles.weightTicker}>{ticker}</div>
                  <div style={styles.weightBar}>
                    <div
                      style={{
                        height: "100%",
                        width: `${Math.max(1, weight * 100)}%`,
                        background: "#2563eb",
                        borderRadius: 2,
                      }}
                    />
                  </div>
                  <div style={styles.weightPct}>{(weight * 100).toFixed(1)}%</div>
                </div>
              ))}
          </div>
        </div>
      )}

      {frontier && <EfficientFrontierChart points={frontier.points} optimizedPoint={result} />}
    </div>
  );
}

const styles = {
  configRow: { display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap", marginBottom: 16 },
  field: { display: "flex", flexDirection: "column", gap: 4 },
  label: { fontSize: 10, fontWeight: 600, color: "#475569", letterSpacing: "0.06em", textTransform: "uppercase" },
  select: { background: "#0d1117", border: "1px solid #1e2230", borderRadius: 6, color: "#e2e8f0", fontSize: 12, padding: "7px 10px", outline: "none" },
  btn: { background: "#2563eb", border: "none", borderRadius: 6, color: "#fff", fontSize: 12, fontWeight: 700, padding: "8px 18px", cursor: "pointer", alignSelf: "flex-end" },
  error: { color: "#f87171", fontSize: 12, marginBottom: 12 },
  resultSection: { marginBottom: 20 },
  statsRow: { display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 16 },
  stat: { background: "#0d1117", border: "1px solid #1e2230", borderRadius: 8, padding: "10px 14px", flex: "1 1 120px" },
  statLabel: { fontSize: 10, color: "#475569", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" },
  statValue: { fontSize: 16, fontWeight: 700, color: "#e2e8f0", marginTop: 4 },
  weightsTitle: { fontSize: 10, fontWeight: 700, color: "#475569", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 8 },
  weightsGrid: { display: "flex", flexDirection: "column", gap: 6 },
  weightItem: { display: "flex", alignItems: "center", gap: 10 },
  weightTicker: { width: 50, fontSize: 11, fontWeight: 700, color: "#93c5fd" },
  weightBar: { flex: 1, height: 8, background: "#1e2230", borderRadius: 4, overflow: "hidden" },
  weightPct: { width: 40, fontSize: 11, color: "#94a3b8", textAlign: "right" },
};
