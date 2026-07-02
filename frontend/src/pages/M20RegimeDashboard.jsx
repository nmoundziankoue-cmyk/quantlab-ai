import { useState } from "react";

const API = "/quant/m20";

const REGIME_COLORS = {
  BULL: "#10b981",
  BEAR: "#ef4444",
  HIGH_VOL: "#f59e0b",
  LOW_VOL: "#6366f1",
  RANGING: "#64748b",
};

function Badge({ regime }) {
  const color = REGIME_COLORS[regime] || "#64748b";
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 10px",
        borderRadius: 12,
        background: color + "22",
        color,
        fontWeight: 600,
        fontSize: "0.8rem",
      }}
    >
      {regime}
    </span>
  );
}

function buildBars(n, start, drift) {
  const bars = [];
  for (let i = 0; i < n; i++) {
    const close = start * Math.pow(1 + drift, i);
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

export default function M20RegimeDashboard() {
  const [ticker, setTicker] = useState("AAPL");
  const [drift, setDrift] = useState(0.002);
  const [bars] = useState(350);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function detect() {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const resp = await fetch(`${API}/regime/detect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker, bars: buildBars(bars, 100, drift) }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      setResult(await resp.json());
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  const last10 = result ? result.history.slice(-10).reverse() : [];
  const regimeCounts = result
    ? Object.entries(
        result.history.reduce((acc, p) => {
          acc[p.regime] = (acc[p.regime] || 0) + 1;
          return acc;
        }, {})
      )
    : [];

  return (
    <div style={{ maxWidth: 860, margin: "0 auto", padding: "2rem 1rem" }}>
      <h1 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "0.25rem" }}>
        Regime Detection Dashboard
      </h1>
      <p style={{ color: "#64748b", marginBottom: "1.5rem", fontSize: "0.9rem" }}>
        Detects BULL / BEAR / HIGH_VOL / LOW_VOL / RANGING from price bars using MA crossover, realized vol, and momentum.
      </p>

      <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "1.25rem" }}>
        <div style={{ flex: 1, minWidth: 140 }}>
          <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: 4 }}>Ticker</label>
          <input
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            style={{ width: "100%", padding: "0.5rem", borderRadius: 6, border: "1px solid #334155", background: "#0f172a", color: "#f1f5f9" }}
          />
        </div>
        <div style={{ flex: 1, minWidth: 140 }}>
          <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: 4 }}>
            Daily drift ({drift > 0 ? "+" : ""}{(drift * 100).toFixed(3)}%)
          </label>
          <input
            type="range"
            min={-0.005}
            max={0.005}
            step={0.0001}
            value={drift}
            onChange={(e) => setDrift(Number(e.target.value))}
            style={{ width: "100%", marginTop: 8 }}
          />
        </div>
        <div style={{ display: "flex", alignItems: "flex-end" }}>
          <button
            onClick={detect}
            disabled={loading}
            style={{
              padding: "0.55rem 1.25rem",
              borderRadius: 6,
              background: "#6366f1",
              color: "#fff",
              border: "none",
              cursor: loading ? "not-allowed" : "pointer",
              fontWeight: 600,
              opacity: loading ? 0.6 : 1,
            }}
          >
            {loading ? "Detecting…" : "Detect Regime"}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ background: "#450a0a", color: "#fca5a5", padding: "0.75rem 1rem", borderRadius: 6, marginBottom: "1rem", fontSize: "0.85rem" }}>
          {error}
        </div>
      )}

      {result && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
            {[
              { label: "Current Regime", value: <Badge regime={result.current_regime} /> },
              { label: "Confidence", value: `${(result.current_confidence * 100).toFixed(1)}%` },
              { label: "Observations", value: result.num_observations.toLocaleString() },
              { label: "Transitions", value: result.transitions },
            ].map((kpi) => (
              <div
                key={kpi.label}
                style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, padding: "1rem" }}
              >
                <div style={{ fontSize: "0.75rem", color: "#64748b", marginBottom: "0.4rem" }}>{kpi.label}</div>
                <div style={{ fontSize: "1.15rem", fontWeight: 700, color: "#f1f5f9" }}>{kpi.value}</div>
              </div>
            ))}
          </div>

          <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.75rem", color: "#f1f5f9" }}>
            Regime Distribution
          </h3>
          <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", marginBottom: "1.5rem" }}>
            {regimeCounts.map(([regime, count]) => (
              <div
                key={regime}
                style={{
                  background: (REGIME_COLORS[regime] || "#64748b") + "22",
                  borderRadius: 8,
                  padding: "0.5rem 1rem",
                  fontSize: "0.85rem",
                  color: REGIME_COLORS[regime] || "#94a3b8",
                  fontWeight: 600,
                }}
              >
                {regime}: {count} bars ({((count / result.history.length) * 100).toFixed(1)}%)
              </div>
            ))}
          </div>

          <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.75rem", color: "#f1f5f9" }}>
            Last 10 Regime Points
          </h3>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #1e293b" }}>
                {["Date", "Regime", "Confidence", "Vol (Recent)", "Vol (Long)", "Momentum"].map((h) => (
                  <th key={h} style={{ textAlign: "left", padding: "0.5rem 0.75rem", color: "#64748b", fontWeight: 500 }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {last10.map((pt) => (
                <tr key={pt.date} style={{ borderBottom: "1px solid #1e293b" }}>
                  <td style={{ padding: "0.5rem 0.75rem", color: "#94a3b8" }}>{pt.date}</td>
                  <td style={{ padding: "0.5rem 0.75rem" }}><Badge regime={pt.regime} /></td>
                  <td style={{ padding: "0.5rem 0.75rem", color: "#f1f5f9" }}>{(pt.confidence * 100).toFixed(1)}%</td>
                  <td style={{ padding: "0.5rem 0.75rem", color: "#f1f5f9" }}>{(pt.indicators.realized_vol_recent * 100).toFixed(2)}%</td>
                  <td style={{ padding: "0.5rem 0.75rem", color: "#f1f5f9" }}>{(pt.indicators.realized_vol_long * 100).toFixed(2)}%</td>
                  <td style={{ padding: "0.5rem 0.75rem", color: "#f1f5f9" }}>{(pt.indicators.momentum_20d * 100).toFixed(2)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
