import { useState } from "react";

const API = "/quant/m20";

const METRIC_OPTS = [
  "sharpe_ratio",
  "sortino_ratio",
  "calmar_ratio",
  "total_return",
  "annualized_return",
  "max_drawdown",
  "win_rate",
  "volatility",
];

function buildBars(n, drift) {
  const bars = [];
  for (let i = 0; i < n; i++) {
    const close = 100 * Math.pow(1 + drift, i);
    bars.push({
      date: new Date(Date.now() - (n - i) * 86400000).toISOString().slice(0, 10),
      open: close * 0.999,
      high: close * 1.005,
      low: close * 0.995,
      close,
      volume: 10000,
    });
  }
  return bars;
}

function buildSignals(n, type) {
  const sigs = {};
  for (let i = 0; i < n; i++) {
    const date = new Date(Date.now() - (n - i) * 86400000).toISOString().slice(0, 10);
    sigs[date] = type;
  }
  return sigs;
}

const STRATEGIES = [
  { name: "Bull Trend", drift: 0.003, signal: "LONG" },
  { name: "Neutral", drift: 0.001, signal: "LONG" },
  { name: "Bear Trend", drift: -0.002, signal: "SHORT" },
];

export default function M20StrategyComparison() {
  const [primaryMetric, setPrimaryMetric] = useState("sharpe_ratio");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const n = 250;
      const ids = [];
      for (const s of STRATEGIES) {
        const resp = await fetch(`${API}/comparison/run-and-register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            strategy_name: s.name,
            ticker: "SIM",
            price_data: { SIM: buildBars(n, s.drift) },
            signals: buildSignals(n, s.signal),
            initial_capital: 100000,
            commission_rate: 0.001,
          }),
        });
        if (!resp.ok) throw new Error(await resp.text());
        const data = await resp.json();
        ids.push(data.strategy_id);
      }

      const cmpResp = await fetch(`${API}/comparison/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ strategy_ids: ids, primary_metric: primaryMetric, include_correlation: true }),
      });
      if (!cmpResp.ok) throw new Error(await cmpResp.text());
      setResult(await cmpResp.json());
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  const fmt = (v, pct) => (v == null ? "—" : pct ? `${(v * 100).toFixed(2)}%` : v.toFixed(4));

  return (
    <div style={{ maxWidth: 960, margin: "0 auto", padding: "2rem 1rem" }}>
      <h1 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "0.25rem" }}>
        Strategy Comparison
      </h1>
      <p style={{ color: "#64748b", marginBottom: "1.5rem", fontSize: "0.9rem" }}>
        Runs 3 synthetic strategies (Bull / Neutral / Bear) and ranks them by your chosen metric.
      </p>

      <div style={{ display: "flex", gap: "1rem", alignItems: "flex-end", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        <div>
          <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: 4 }}>
            Primary ranking metric
          </label>
          <select
            value={primaryMetric}
            onChange={(e) => setPrimaryMetric(e.target.value)}
            style={{
              padding: "0.5rem 0.75rem",
              borderRadius: 6,
              border: "1px solid #334155",
              background: "#0f172a",
              color: "#f1f5f9",
              fontSize: "0.9rem",
            }}
          >
            {METRIC_OPTS.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>
        <button
          onClick={run}
          disabled={loading}
          style={{
            padding: "0.55rem 1.25rem",
            borderRadius: 6,
            background: "#10b981",
            color: "#fff",
            border: "none",
            cursor: loading ? "not-allowed" : "pointer",
            fontWeight: 600,
            opacity: loading ? 0.6 : 1,
          }}
        >
          {loading ? "Running…" : "Run Comparison"}
        </button>
      </div>

      {error && (
        <div style={{ background: "#450a0a", color: "#fca5a5", padding: "0.75rem 1rem", borderRadius: 6, marginBottom: "1rem", fontSize: "0.85rem" }}>
          {error}
        </div>
      )}

      {result && (
        <>
          <div style={{ marginBottom: "1rem", fontSize: "0.9rem", color: "#64748b" }}>
            Best strategy:{" "}
            <span style={{ color: "#10b981", fontWeight: 700 }}>{result.best_strategy}</span>
            {" "}· Ranked by <em>{result.primary_metric}</em>
          </div>

          <div style={{ overflowX: "auto", marginBottom: "1.5rem" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #1e293b" }}>
                  {["Rank", "Strategy", "Total Return", "Ann. Return", "Sharpe", "Sortino", "Calmar", "Max DD", "Win Rate", "Vol", "Score"].map((h) => (
                    <th key={h} style={{ textAlign: "left", padding: "0.5rem 0.75rem", color: "#64748b", fontWeight: 500, whiteSpace: "nowrap" }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.ranked_table.map((row) => (
                  <tr
                    key={row.strategy_id}
                    style={{
                      borderBottom: "1px solid #1e293b",
                      background: row.rank === 1 ? "#10b98111" : "transparent",
                    }}
                  >
                    <td style={{ padding: "0.5rem 0.75rem", color: row.rank === 1 ? "#10b981" : "#f1f5f9", fontWeight: row.rank === 1 ? 700 : 400 }}>
                      #{row.rank}
                    </td>
                    <td style={{ padding: "0.5rem 0.75rem", fontWeight: 600, color: "#f1f5f9" }}>{row.strategy_name}</td>
                    <td style={{ padding: "0.5rem 0.75rem", color: row.total_return >= 0 ? "#10b981" : "#ef4444" }}>{fmt(row.total_return, true)}</td>
                    <td style={{ padding: "0.5rem 0.75rem", color: row.annualized_return >= 0 ? "#10b981" : "#ef4444" }}>{fmt(row.annualized_return, true)}</td>
                    <td style={{ padding: "0.5rem 0.75rem", color: "#f1f5f9" }}>{fmt(row.sharpe_ratio)}</td>
                    <td style={{ padding: "0.5rem 0.75rem", color: "#f1f5f9" }}>{fmt(row.sortino_ratio)}</td>
                    <td style={{ padding: "0.5rem 0.75rem", color: "#f1f5f9" }}>{fmt(row.calmar_ratio)}</td>
                    <td style={{ padding: "0.5rem 0.75rem", color: "#ef4444" }}>{fmt(row.max_drawdown, true)}</td>
                    <td style={{ padding: "0.5rem 0.75rem", color: "#f1f5f9" }}>{fmt(row.win_rate, true)}</td>
                    <td style={{ padding: "0.5rem 0.75rem", color: "#f1f5f9" }}>{fmt(row.volatility, true)}</td>
                    <td style={{ padding: "0.5rem 0.75rem", color: "#6366f1", fontWeight: 600 }}>{row.score.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {result.correlation_matrix && (
            <>
              <h3 style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: "0.75rem", color: "#f1f5f9" }}>
                Equity Curve Correlation Matrix
              </h3>
              <table style={{ borderCollapse: "collapse", fontSize: "0.82rem" }}>
                <thead>
                  <tr>
                    <th style={{ padding: "0.4rem 0.6rem", color: "#64748b" }}></th>
                    {result.strategies.map((s) => (
                      <th key={s.strategy_id} style={{ padding: "0.4rem 0.6rem", color: "#94a3b8" }}>
                        {s.strategy_name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.strategies.map((s, i) => (
                    <tr key={s.strategy_id}>
                      <td style={{ padding: "0.4rem 0.6rem", color: "#94a3b8", fontWeight: 600 }}>{s.strategy_name}</td>
                      {result.correlation_matrix[i].map((corr, j) => (
                        <td
                          key={j}
                          style={{
                            padding: "0.4rem 0.75rem",
                            textAlign: "center",
                            color: corr === 1.0 ? "#94a3b8" : corr > 0 ? "#10b981" : "#ef4444",
                            fontWeight: i === j ? 700 : 400,
                          }}
                        >
                          {corr.toFixed(3)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </>
      )}
    </div>
  );
}
