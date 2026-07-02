import { useState } from "react";

const API = "/quant/m20";

function getColor(corr) {
  if (corr === null) return "#1e293b";
  const v = Math.max(-1, Math.min(1, corr));
  if (v >= 0) {
    const g = Math.round(v * 255);
    return `rgb(${255 - g}, ${255}, ${255 - g})`;
  }
  const g = Math.round(-v * 255);
  return `rgb(${255}, ${255 - g}, ${255 - g})`;
}

function makeDefaultReturns(n, drift) {
  const result = {};
  for (let i = 0; i < n; i++) {
    const date = new Date(Date.now() - (n - i) * 86400000).toISOString().slice(0, 10);
    result[date] = drift + (Math.random() - 0.5) * 0.02;
  }
  return result;
}

const DEFAULT_TICKERS = [
  { name: "AAPL", drift: 0.001 },
  { name: "MSFT", drift: 0.0009 },
  { name: "GOOGL", drift: 0.0008 },
  { name: "AMZN", drift: -0.0003 },
];

export default function M20CorrelationHeatmap() {
  const [matrix, setMatrix] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [n, setN] = useState(120);

  async function computeMatrix() {
    setLoading(true);
    setError("");
    setMatrix(null);
    try {
      const entries = DEFAULT_TICKERS.map((t) => ({
        ticker: t.name,
        returns: makeDefaultReturns(n, t.drift),
      }));
      await fetch(`${API}/correlation/add-returns-batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ entries }),
      });

      const resp = await fetch(`${API}/correlation/matrix`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tickers: DEFAULT_TICKERS.map((t) => t.name) }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      setMatrix(await resp.json());
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 780, margin: "0 auto", padding: "2rem 1rem" }}>
      <h1 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "0.25rem" }}>
        Correlation Heatmap
      </h1>
      <p style={{ color: "#64748b", marginBottom: "1.5rem", fontSize: "0.9rem" }}>
        Pearson N×N correlation matrix. Green = positive, Red = negative.
      </p>

      <div style={{ display: "flex", gap: "1rem", alignItems: "flex-end", marginBottom: "1.5rem" }}>
        <div>
          <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: 4 }}>
            Observations per ticker: {n}
          </label>
          <input
            type="range"
            min={30}
            max={252}
            step={10}
            value={n}
            onChange={(e) => setN(Number(e.target.value))}
            style={{ width: 200 }}
          />
        </div>
        <button
          onClick={computeMatrix}
          disabled={loading}
          style={{
            padding: "0.55rem 1.25rem",
            borderRadius: 6,
            background: "#0ea5e9",
            color: "#fff",
            border: "none",
            cursor: loading ? "not-allowed" : "pointer",
            fontWeight: 600,
            opacity: loading ? 0.6 : 1,
          }}
        >
          {loading ? "Computing…" : "Compute Matrix"}
        </button>
      </div>

      {error && (
        <div style={{ background: "#450a0a", color: "#fca5a5", padding: "0.75rem 1rem", borderRadius: 6, marginBottom: "1rem", fontSize: "0.85rem" }}>
          {error}
        </div>
      )}

      {matrix && (
        <>
          <div style={{ marginBottom: "1rem", fontSize: "0.85rem", color: "#64748b" }}>
            Observations: {matrix.num_observations} · Min: {matrix.min_correlation.toFixed(3)} · Max: {matrix.max_correlation.toFixed(3)} · Avg |corr|: {matrix.avg_correlation.toFixed(3)}
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ borderCollapse: "collapse", fontSize: "0.85rem" }}>
              <thead>
                <tr>
                  <th style={{ padding: "0.4rem 0.75rem", color: "#64748b" }}></th>
                  {matrix.tickers.map((t) => (
                    <th key={t} style={{ padding: "0.4rem 0.75rem", color: "#94a3b8", fontWeight: 600, minWidth: 80 }}>
                      {t}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrix.tickers.map((rowTicker, i) => (
                  <tr key={rowTicker}>
                    <td style={{ padding: "0.4rem 0.75rem", color: "#94a3b8", fontWeight: 600 }}>{rowTicker}</td>
                    {matrix.values[i].map((corr, j) => (
                      <td
                        key={j}
                        title={`${rowTicker} vs ${matrix.tickers[j]}: ${corr.toFixed(4)}`}
                        style={{
                          padding: "0.5rem 0.75rem",
                          background: getColor(corr),
                          color: "#000",
                          textAlign: "center",
                          fontWeight: i === j ? 700 : 400,
                          fontSize: "0.82rem",
                        }}
                      >
                        {corr.toFixed(3)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
