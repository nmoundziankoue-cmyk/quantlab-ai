import { useState, useEffect } from "react";
import useRegimeStore, { REGIME_COLORS } from "../store/useRegimeStore";

const API = "/quant/m20";

function RegimeBadge({ regime, large = false }) {
  const color = REGIME_COLORS[regime] ?? "#7A84A0";
  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 5,
      padding: large ? "4px 12px" : "2px 8px",
      borderRadius: 4,
      background: color + "18",
      border: `1px solid ${color}44`,
      color,
      fontFamily: "var(--font-mono)",
      fontWeight: 600,
      fontSize: large ? 14 : 11,
      letterSpacing: "0.05em",
    }}>
      <span style={{ width: 5, height: 5, borderRadius: "50%", background: color, flexShrink: 0 }} />
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
  const setRegime = useRegimeStore((s) => s.setRegime);

  const [ticker, setTicker]   = useState("AAPL");
  const [drift, setDrift]     = useState(0.002);
  const [bars]                = useState(350);
  const [result, setResult]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

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
      const data = await resp.json();
      setResult(data);
      setRegime(data.current_regime, data.current_confidence);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { detect(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const last10 = result ? result.history.slice(-10).reverse() : [];
  const regimeCounts = result
    ? Object.entries(result.history.reduce((acc, p) => {
        acc[p.regime] = (acc[p.regime] || 0) + 1;
        return acc;
      }, {})).sort((a, b) => b[1] - a[1])
    : [];

  return (
    <div style={S.root}>
      {/* Page header */}
      <div style={S.pageHeader}>
        <div>
          <h1 style={S.h1}>Regime Detection</h1>
          <p style={S.h1Sub}>
            BULL · BEAR · HIGH_VOL · LOW_VOL · RANGING — MA crossover × realized vol × momentum
          </p>
        </div>
        {result && <RegimeBadge regime={result.current_regime} large />}
      </div>

      {/* Controls */}
      <div style={S.controls}>
        <div style={S.controlGroup}>
          <label className="ql-label">Ticker</label>
          <input
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            style={S.textInput}
          />
        </div>
        <div style={{ ...S.controlGroup, flex: 2 }}>
          <label className="ql-label">
            Daily drift&nbsp;
            <span className="ql-value" style={{ color: drift >= 0 ? "#27C784" : "#E5473E" }}>
              {drift >= 0 ? "+" : ""}{(drift * 100).toFixed(3)}%
            </span>
          </label>
          <input
            type="range"
            min={-0.005}
            max={0.005}
            step={0.0001}
            value={drift}
            onChange={(e) => setDrift(Number(e.target.value))}
            style={{ width: "100%", marginTop: 6, accentColor: "#567EFF" }}
          />
        </div>
        <button onClick={detect} disabled={loading} style={S.btn}>
          {loading ? "Detecting…" : "Run Detection"}
        </button>
      </div>

      {error && (
        <div style={S.errorBox}>{error}</div>
      )}

      {/* KPI strip */}
      {result && (
        <div style={S.kpiRow}>
          {[
            { label: "Current Regime", value: <RegimeBadge regime={result.current_regime} />, mono: false },
            { label: "Confidence",    value: `${(result.current_confidence * 100).toFixed(1)}%` },
            { label: "Observations", value: result.num_observations.toLocaleString() },
            { label: "Transitions",  value: result.transitions },
          ].map((k) => (
            <div key={k.label} style={S.kpiCard}>
              <div className="ql-label" style={{ marginBottom: 8 }}>{k.label}</div>
              <div className="ql-value" style={{ fontSize: 22, fontWeight: 600, color: "#E2A52B", lineHeight: 1 }}>
                {k.value}
              </div>
            </div>
          ))}
        </div>
      )}

      {result && (
        <>
          {/* Regime distribution */}
          <div style={S.panel}>
            <div style={S.panelTitle}>Regime Distribution — {result.history.length} bars</div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {regimeCounts.map(([regime, count]) => {
                const color = REGIME_COLORS[regime] ?? "#7A84A0";
                const pct = ((count / result.history.length) * 100).toFixed(1);
                return (
                  <div key={regime} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    <RegimeBadge regime={regime} />
                    <div style={{ height: 3, width: 100, background: "#232A3D", borderRadius: 2 }}>
                      <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: 2 }} />
                    </div>
                    <span className="ql-value" style={{ fontSize: 10, color: "#7A84A0" }}>
                      {count} bars · {pct}%
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* History table */}
          <div style={S.panel}>
            <div style={S.panelTitle}>Last 10 Regime Points</div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    {["Date", "Regime", "Confidence", "Vol 20d", "Vol 252d", "Momentum 20d"].map((h) => (
                      <th key={h} style={{ textAlign: "left" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {last10.map((pt) => (
                    <tr key={pt.date}>
                      <td className="ql-value" style={{ color: "#7A84A0" }}>{pt.date}</td>
                      <td><RegimeBadge regime={pt.regime} /></td>
                      <td className="ql-value" style={{ color: "#E2A52B" }}>{(pt.confidence * 100).toFixed(1)}%</td>
                      <td className="ql-value">{(pt.indicators.realized_vol_recent * 100).toFixed(2)}%</td>
                      <td className="ql-value">{(pt.indicators.realized_vol_long  * 100).toFixed(2)}%</td>
                      <td className="ql-value" style={{ color: pt.indicators.momentum_20d >= 0 ? "#27C784" : "#E5473E" }}>
                        {pt.indicators.momentum_20d >= 0 ? "+" : ""}{(pt.indicators.momentum_20d * 100).toFixed(2)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

const S = {
  root:       { padding: "28px 32px", maxWidth: 960 },
  pageHeader: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 },
  h1:         { fontFamily: "var(--font-display)", fontSize: 20, fontWeight: 700, color: "#DDE2EE", margin: "0 0 6px", lineHeight: 1.2 },
  h1Sub:      { fontFamily: "var(--font-mono)", fontSize: 10, color: "#454D66", margin: 0, letterSpacing: "0.03em" },
  controls:   { display: "flex", gap: 16, alignItems: "flex-end", marginBottom: 20, flexWrap: "wrap" },
  controlGroup: { display: "flex", flexDirection: "column", gap: 4, flex: 1, minWidth: 120 },
  textInput:  { padding: "7px 10px" },
  btn: {
    padding: "8px 20px",
    borderRadius: 6,
    background: "#567EFF",
    color: "#fff",
    border: "none",
    fontFamily: "var(--font-display)",
    fontWeight: 600,
    fontSize: 13,
    cursor: "pointer",
    whiteSpace: "nowrap",
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
  kpiRow:  { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: 14 },
  kpiCard: { background: "#131720", border: "1px solid #232A3D", borderRadius: 7, padding: "14px 16px" },
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
