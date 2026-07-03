import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";

const API = "/quant/m20";

// Maps correlation [-1, +1] onto a dark-palette-aware green↔red ramp
function cellColor(corr) {
  if (corr === null) return "#232A3D";
  const v = Math.max(-1, Math.min(1, corr));
  if (v >= 0) {
    const alpha = Math.round(v * 180).toString(16).padStart(2, "0");
    return `#27C784${alpha}`;
  }
  const alpha = Math.round(-v * 180).toString(16).padStart(2, "0");
  return `#E5473E${alpha}`;
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
  { name: "AAPL",  drift:  0.001  },
  { name: "MSFT",  drift:  0.0009 },
  { name: "GOOGL", drift:  0.0008 },
  { name: "AMZN",  drift: -0.0003 },
];

export default function M20CorrelationHeatmap() {
  const [matrix, setMatrix]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");
  const [n, setN]             = useState(120);

  // 3D tilt state for the heatmap panel
  const [tilt, setTilt] = useState({ rx: 0, ry: 0 });
  const panelRef = useRef(null);

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

  useEffect(() => { computeMatrix(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 3D tilt handlers — no transition during move (instant), smooth return on leave
  const handleMouseMove = (e) => {
    if (!panelRef.current) return;
    const rect = panelRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    setTilt({ rx: -y * 8, ry: x * 8 });
  };
  const handleMouseLeave = () => setTilt({ rx: 0, ry: 0 });

  const isFlat = tilt.rx === 0 && tilt.ry === 0;

  return (
    <div style={S.root}>
      {/* Header */}
      <div style={S.pageHeader}>
        <div>
          <h1 style={S.h1}>Correlation Heatmap</h1>
          <p style={S.h1Sub}>
            N×N Pearson matrix · 120 observations · green = positive · red = negative
          </p>
        </div>
      </div>

      {/* Controls */}
      <div style={S.controls}>
        <div style={S.controlGroup}>
          <label className="ql-label">
            Observations per ticker: <span className="ql-value" style={{ color: "#E2A52B" }}>{n}</span>
          </label>
          <input
            type="range"
            min={30}
            max={252}
            step={10}
            value={n}
            onChange={(e) => setN(Number(e.target.value))}
            style={{ width: 180, accentColor: "#567EFF" }}
          />
        </div>
        <button onClick={computeMatrix} disabled={loading} style={S.btn}>
          {loading ? "Computing…" : "Recompute"}
        </button>
      </div>

      {error && <div style={S.errorBox}>{error}</div>}

      {matrix && (
        <>
          {/* Stats strip — staggered entrance */}
          <div style={S.statsRow}>
            {[
              { label: "Observations", value: matrix.num_observations },
              { label: "Min corr",     value: matrix.min_correlation.toFixed(3) },
              { label: "Max corr",     value: matrix.max_correlation.toFixed(3) },
              { label: "Avg |corr|",   value: matrix.avg_correlation.toFixed(3) },
              { label: "Tickers",      value: matrix.tickers.join(" · ") },
            ].map((s, i) => (
              <motion.div
                key={s.label}
                style={S.statCell}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.07, duration: 0.3, ease: "easeOut" }}
              >
                <div className="ql-label" style={{ marginBottom: 4 }}>{s.label}</div>
                <div className="ql-value" style={{ fontSize: 15, fontWeight: 600, color: "#E2A52B" }}>{s.value}</div>
              </motion.div>
            ))}
          </div>

          {/* Heatmap panel — 3D perspective tilt on mouse move */}
          <div
            ref={panelRef}
            style={{
              ...S.panel,
              transform: `perspective(700px) rotateX(${tilt.rx}deg) rotateY(${tilt.ry}deg)`,
              transition: isFlat
                ? "transform 0.55s cubic-bezier(0.23, 1, 0.32, 1), box-shadow 0.55s ease-out"
                : "none",
              boxShadow: isFlat
                ? "0 0 0 rgba(0,0,0,0)"
                : "0 28px 70px rgba(0,0,0,0.55), 0 8px 24px rgba(86,126,255,0.12)",
              cursor: "crosshair",
              willChange: "transform",
            }}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
          >
            <div style={S.panelTitle}>Pearson Correlation Matrix</div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ borderCollapse: "collapse", fontFamily: "var(--font-mono)" }}>
                <thead>
                  <tr>
                    <th style={{ padding: "6px 14px", textAlign: "right", color: "#454D66", fontSize: 10 }}></th>
                    {(matrix?.tickers ?? []).map((t) => (
                      <th key={t} style={{ padding: "6px 14px", color: "#7A84A0", fontSize: 11, fontWeight: 600, minWidth: 90, textAlign: "center" }}>
                        {t}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(matrix?.tickers ?? []).map((rowTicker, i) => (
                    <tr key={rowTicker}>
                      <td style={{ padding: "6px 14px", color: "#7A84A0", fontWeight: 600, fontSize: 11, textAlign: "right", whiteSpace: "nowrap" }}>
                        {rowTicker}
                      </td>
                      {(matrix?.values?.[i] ?? []).map((corr, j) => {
                        const isDiag = i === j;
                        return (
                          <td
                            key={j}
                            title={`${rowTicker} vs ${matrix.tickers[j]}: ${corr.toFixed(4)}`}
                            style={{
                              padding: "10px 14px",
                              background: cellColor(isDiag ? 1 : corr),
                              textAlign: "center",
                              fontSize: 12,
                              fontWeight: isDiag ? 700 : 500,
                              color: isDiag ? "#DDE2EE" : Math.abs(corr) > 0.4 ? "#DDE2EE" : "#7A84A0",
                              borderRadius: 3,
                              cursor: "default",
                              transition: "filter 0.12s ease-out",
                            }}
                            onMouseEnter={(e) => { e.currentTarget.style.filter = "brightness(1.35)"; }}
                            onMouseLeave={(e) => { e.currentTarget.style.filter = ""; }}
                          >
                            {corr.toFixed(3)}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Legend */}
            <div style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "#E5473E" }}>−1.0</span>
              <div style={{
                flex: 1, maxWidth: 200, height: 4, borderRadius: 2,
                background: "linear-gradient(to right, #E5473E88, #232A3D, #27C78488)",
              }} />
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "#27C784" }}>+1.0</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "#454D66", marginLeft: 12 }}>
                Pearson r · {n} observations
              </span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

const S = {
  root:       { padding: "28px 32px", maxWidth: 820 },
  pageHeader: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 },
  h1:         { fontFamily: "var(--font-display)", fontSize: 20, fontWeight: 700, color: "#DDE2EE", margin: "0 0 6px" },
  h1Sub:      { fontFamily: "var(--font-mono)", fontSize: 10, color: "#454D66", margin: 0, letterSpacing: "0.03em" },
  controls:   { display: "flex", gap: 16, alignItems: "flex-end", marginBottom: 20 },
  controlGroup: { display: "flex", flexDirection: "column", gap: 4 },
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
  statsRow: { display: "flex", gap: 10, marginBottom: 14, flexWrap: "wrap" },
  statCell: { background: "#131720", border: "1px solid #232A3D", borderRadius: 7, padding: "12px 16px", minWidth: 100 },
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
