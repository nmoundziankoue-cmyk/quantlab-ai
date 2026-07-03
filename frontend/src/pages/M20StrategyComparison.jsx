import { useState, useEffect } from "react";

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
  { name: "Bull Trend", drift:  0.003, signal: "LONG"  },
  { name: "Neutral",    drift:  0.001, signal: "LONG"  },
  { name: "Bear Trend", drift: -0.002, signal: "SHORT" },
];

const fmt    = (v, pct) => v == null ? "—" : pct ? `${(v * 100).toFixed(2)}%` : v.toFixed(4);
const fmtPct = (v)      => fmt(v, true);

export default function M20StrategyComparison() {
  const [primaryMetric, setPrimaryMetric] = useState("sharpe_ratio");
  const [result, setResult]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  async function run() {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const n   = 250;
      const ids = [];
      for (const s of STRATEGIES) {
        const resp = await fetch(`${API}/comparison/run-and-register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            strategy_name:   s.name,
            ticker:          "SIM",
            price_data:      { SIM: buildBars(n, s.drift) },
            signals:         buildSignals(n, s.signal),
            initial_capital: 100000,
            commission_rate: 0.001,
          }),
        });
        if (!resp.ok) throw new Error(await resp.text());
        ids.push((await resp.json()).strategy_id);
      }
      const cmp = await fetch(`${API}/comparison/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ strategy_ids: ids, primary_metric: primaryMetric, include_correlation: true }),
      });
      if (!cmp.ok) throw new Error(await cmp.text());
      setResult(await cmp.json());
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { run(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div style={S.root}>
      {/* Header */}
      <div style={S.pageHeader}>
        <div>
          <h1 style={S.h1}>Strategy Comparison</h1>
          <p style={S.h1Sub}>
            3 synthetic strategies · Sharpe / Sortino / Calmar ranking · equity-curve correlation
          </p>
        </div>
        {result && (
          <div style={{ textAlign: "right" }}>
            <div className="ql-label" style={{ marginBottom: 4 }}>Best strategy</div>
            <div style={{ fontFamily: "var(--font-display)", fontSize: 15, fontWeight: 700, color: "#27C784" }}>
              {result.best_strategy}
            </div>
          </div>
        )}
      </div>

      {/* Controls */}
      <div style={S.controls}>
        <div style={S.controlGroup}>
          <label className="ql-label">Primary ranking metric</label>
          <select
            value={primaryMetric}
            onChange={(e) => setPrimaryMetric(e.target.value)}
            style={{ padding: "7px 10px", minWidth: 180 }}
          >
            {METRIC_OPTS.map((m) => (
              <option key={m} value={m}>{m.replace(/_/g, " ")}</option>
            ))}
          </select>
        </div>
        <button onClick={run} disabled={loading} style={S.btn}>
          {loading ? "Running…" : "Run Comparison"}
        </button>
      </div>

      {error && <div style={S.errorBox}>{error}</div>}

      {result && (
        <>
          {/* Ranking table */}
          <div style={S.panel}>
            <div style={S.panelTitle}>
              Ranked by {result.primary_metric.replace(/_/g, " ")}
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    {["Rank", "Strategy", "Total Return", "Ann. Return", "Sharpe", "Sortino", "Calmar", "Max DD", "Win Rate", "Vol", "Score"].map((h) => (
                      <th key={h} style={{ whiteSpace: "nowrap" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.ranked_table.map((row) => {
                    const isTop = row.rank === 1;
                    return (
                      <tr key={row.strategy_id} style={{ background: isTop ? "#27C78410" : "transparent" }}>
                        <td>
                          <span className="ql-value" style={{ color: isTop ? "#27C784" : "#7A84A0", fontWeight: isTop ? 700 : 400 }}>
                            #{row.rank}
                          </span>
                        </td>
                        <td style={{ fontFamily: "var(--font-display)", fontWeight: 600, color: isTop ? "#DDE2EE" : "#7A84A0" }}>
                          {row.strategy_name}
                        </td>
                        <td className="ql-value" style={{ color: row.total_return >= 0 ? "#27C784" : "#E5473E" }}>
                          {fmtPct(row.total_return)}
                        </td>
                        <td className="ql-value" style={{ color: row.annualized_return >= 0 ? "#27C784" : "#E5473E" }}>
                          {fmtPct(row.annualized_return)}
                        </td>
                        <td className="ql-value" style={{ color: "#E2A52B" }}>{fmt(row.sharpe_ratio)}</td>
                        <td className="ql-value" style={{ color: "#E2A52B" }}>{fmt(row.sortino_ratio)}</td>
                        <td className="ql-value" style={{ color: "#E2A52B" }}>{fmt(row.calmar_ratio)}</td>
                        <td className="ql-value" style={{ color: "#E5473E" }}>{fmtPct(row.max_drawdown)}</td>
                        <td className="ql-value" style={{ color: "#DDE2EE" }}>{fmtPct(row.win_rate)}</td>
                        <td className="ql-value" style={{ color: "#7A84A0" }}>{fmtPct(row.volatility)}</td>
                        <td className="ql-value" style={{ color: "#9D7FEA", fontWeight: 600 }}>
                          {row.score.toFixed(4)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Equity-curve correlation */}
          {result.correlation_matrix && (
            <div style={S.panel}>
              <div style={S.panelTitle}>Equity Curve Correlation</div>
              <table style={{ borderCollapse: "collapse", fontFamily: "var(--font-mono)" }}>
                <thead>
                  <tr>
                    <th style={{ padding: "6px 14px", color: "#454D66", textAlign: "right" }}></th>
                    {result.strategies.map((s) => (
                      <th key={s.strategy_id} style={{ padding: "6px 14px", color: "#7A84A0", fontSize: 11, fontWeight: 600 }}>
                        {s.strategy_name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.strategies.map((s, i) => (
                    <tr key={s.strategy_id}>
                      <td style={{ padding: "6px 14px", color: "#7A84A0", fontWeight: 600, fontSize: 11, textAlign: "right" }}>
                        {s.strategy_name}
                      </td>
                      {result.correlation_matrix[i].map((corr, j) => (
                        <td key={j} style={{
                          padding: "8px 14px",
                          textAlign: "center",
                          fontSize: 12,
                          fontWeight: i === j ? 700 : 400,
                          color: i === j ? "#7A84A0" : corr > 0 ? "#27C784" : "#E5473E",
                        }}>
                          {corr.toFixed(3)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              <p style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "#454D66", marginTop: 10 }}>
                Composite score = 0.40 × Sharpe + 0.25 × Sortino + 0.20 × Calmar + 0.15 × (1 − |MaxDD|)
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

const S = {
  root:         { padding: "28px 32px", maxWidth: 1080 },
  pageHeader:   { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 },
  h1:           { fontFamily: "var(--font-display)", fontSize: 20, fontWeight: 700, color: "#DDE2EE", margin: "0 0 6px" },
  h1Sub:        { fontFamily: "var(--font-mono)", fontSize: 10, color: "#454D66", margin: 0, letterSpacing: "0.03em" },
  controls:     { display: "flex", gap: 16, alignItems: "flex-end", marginBottom: 20 },
  controlGroup: { display: "flex", flexDirection: "column", gap: 4 },
  btn: {
    padding: "8px 20px",
    borderRadius: 6,
    background: "#27C784",
    color: "#0B0D13",
    border: "none",
    fontFamily: "var(--font-display)",
    fontWeight: 700,
    fontSize: 13,
    cursor: "pointer",
    alignSelf: "flex-end",
  },
  errorBox: {
    background: "#E5473E18",
    border: "1px solid #E5473E44",
    color: "#E5473E",
    padding: "10px 14px",
    borderRadius: 6,
    marginBottom: 16,
    fontFamily: "var(--font-mono)",
    fontSize: 12,
  },
  panel: {
    background: "#131720",
    border: "1px solid #232A3D",
    borderRadius: 7,
    padding: "16px 18px",
    marginBottom: 12,
  },
  panelTitle: {
    fontFamily: "var(--font-display)",
    fontSize: 10,
    fontWeight: 700,
    color: "#567EFF",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    marginBottom: 14,
  },
};
