import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { altIntelligenceApi } from "../api/altIntelligenceApi";

const S = {
  page: { padding: 28, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" },
  card: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20, marginBottom: 16 },
  title: { fontSize: 13, fontWeight: 700, color: "#8b949e", letterSpacing: "0.06em", marginBottom: 14, textTransform: "uppercase" },
  label: { fontSize: 12, color: "#8b949e", marginBottom: 4, display: "block" },
  input: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "9px 12px", fontSize: 13, width: "100%", boxSizing: "border-box" },
  btn: { background: "#1f6feb", border: "none", borderRadius: 6, color: "#fff", padding: "10px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer" },
  err: { background: "#2d1317", border: "1px solid #f85149", borderRadius: 6, color: "#f85149", padding: "10px 14px", fontSize: 13, marginBottom: 14 },
  pill: { display: "inline-block", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600 },
  metricBox: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 6, padding: "14px 12px", textAlign: "center" },
  metricValue: { fontSize: 22, fontWeight: 700, color: "#58a6ff", lineHeight: 1.2 },
  metricLabel: { fontSize: 11, color: "#8b949e", marginTop: 4, textTransform: "uppercase", letterSpacing: "0.06em" },
  gauge: { background: "#21262d", borderRadius: 4, height: 12, width: "100%", overflow: "hidden" },
};

function ratioSignal(ratio) {
  if (ratio > 0.65) return { label: "BULLISH", color: "#3fb950", bg: "#1a3a25" };
  if (ratio < 0.35) return { label: "BEARISH", color: "#f85149", bg: "#2d1317" };
  return { label: "NEUTRAL", color: "#d29922", bg: "#2d1f0a" };
}

function fmt(n, d = 3) { return Number(n).toFixed(d); }

export default function AltInsiderActivity() {
  const [symbol, setSymbol] = useState("AAPL");
  const [buys, setBuys] = useState("12");
  const [sells, setSells] = useState("5");
  const [execChanges, setExecChanges] = useState("2");
  const [totalExecs, setTotalExecs] = useState("15");
  const [windowDays, setWindowDays] = useState("90");
  const [text, setText] = useState("The company reported strong quarterly results beating analyst expectations.");
  const [result, setResult] = useState(null);

  const mut = useMutation({
    mutationFn: () => altIntelligenceApi.computeFeatures({
      symbol,
      document_texts: text ? [text] : [],
      insider_buys: parseInt(buys) || 0,
      insider_sells: parseInt(sells) || 0,
      executive_changes: parseInt(execChanges) || 0,
      total_executives: parseInt(totalExecs) || 1,
      window_days: parseInt(windowDays) || 90,
    }),
    onSuccess: r => setResult(r.data),
  });

  const features = result?.features || {};
  const insiderRatio = features.alt_insider_buying_ratio ?? null;
  const signal = insiderRatio !== null ? ratioSignal(insiderRatio) : null;

  return (
    <div style={S.page}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Insider Activity</h1>
        <p style={{ color: "#8b949e", margin: "4px 0 0", fontSize: 13 }}>
          Insider buying ratio, executive turnover, and filing frequency signals for institutional alternative alpha
        </p>
      </div>

      <div style={S.card}>
        <div style={S.title}>Input Parameters</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 14 }}>
          <div><label style={S.label}>Symbol</label><input style={S.input} value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} /></div>
          <div><label style={S.label}>Window (days)</label><input style={S.input} type="number" value={windowDays} onChange={e => setWindowDays(e.target.value)} /></div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 14 }}>
          <div><label style={S.label}>Insider Buys</label><input style={S.input} type="number" value={buys} onChange={e => setBuys(e.target.value)} min={0} /></div>
          <div><label style={S.label}>Insider Sells</label><input style={S.input} type="number" value={sells} onChange={e => setSells(e.target.value)} min={0} /></div>
          <div><label style={S.label}>Exec Changes</label><input style={S.input} type="number" value={execChanges} onChange={e => setExecChanges(e.target.value)} min={0} /></div>
          <div><label style={S.label}>Total Executives</label><input style={S.input} type="number" value={totalExecs} onChange={e => setTotalExecs(e.target.value)} min={1} /></div>
        </div>
        <div style={{ marginBottom: 14 }}>
          <label style={S.label}>Recent Filing / News Text (optional, for sentiment signal)</label>
          <textarea style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "9px 12px", fontSize: 12, width: "100%", boxSizing: "border-box", resize: "vertical", fontFamily: "monospace", minHeight: 80 }}
            value={text} onChange={e => setText(e.target.value)} />
        </div>
        <button style={{ ...S.btn, opacity: mut.isPending ? 0.6 : 1 }} onClick={() => mut.mutate()} disabled={mut.isPending}>
          {mut.isPending ? "Computing…" : "Compute Insider Signals"}
        </button>
      </div>

      {mut.error && <div style={S.err}>{mut.error.message}</div>}

      {result && (
        <>
          {/* Primary signal */}
          {signal && (
            <div style={{ ...S.card, borderLeft: `4px solid ${signal.color}` }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontSize: 13, color: "#8b949e", marginBottom: 4 }}>Insider Buying Signal — {result.symbol}</div>
                  <div style={{ fontSize: 28, fontWeight: 700, color: signal.color }}>{(insiderRatio * 100).toFixed(1)}%</div>
                  <div style={{ fontSize: 12, color: "#8b949e", marginTop: 4 }}>buying ratio (buys / total trades)</div>
                </div>
                <span style={{ ...S.pill, background: signal.bg, color: signal.color, border: `1px solid ${signal.color}`, fontSize: 14, padding: "6px 16px" }}>
                  {signal.label}
                </span>
              </div>
              <div style={{ marginTop: 14 }}>
                <div style={S.gauge}>
                  <div style={{ width: `${insiderRatio * 100}%`, background: signal.color, height: "100%", transition: "width 0.4s ease" }} />
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4, fontSize: 11, color: "#8b949e" }}>
                  <span>0% — Pure Sell</span><span>50% — Neutral</span><span>100% — Pure Buy</span>
                </div>
              </div>
            </div>
          )}

          {/* Feature grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
            {[
              ["Insider Buying Ratio", "alt_insider_buying_ratio", "%", 100],
              ["Executive Turnover", "alt_executive_turnover", "%", 100],
              ["Filing Frequency", "alt_filing_frequency", "", 1],
              ["Alt Sentiment", "alt_sentiment", "", 1],
              ["Event Density", "alt_event_density", "", 1],
              ["ESG Score", "alt_esg_score", "", 1],
            ].map(([label, key, suffix, scale]) => {
              const val = features[key];
              return val !== undefined ? (
                <div key={key} style={S.metricBox}>
                  <div style={S.metricValue}>{suffix === "%" ? (val * scale).toFixed(1) + "%" : fmt(val)}</div>
                  <div style={S.metricLabel}>{label}</div>
                </div>
              ) : null;
            })}
          </div>

          {/* Full feature table */}
          <div style={{ ...S.card, marginTop: 16 }}>
            <div style={S.title}>All Alternative Features</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
              {Object.entries(features).map(([k, v]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "5px 8px", background: "#0d1117", borderRadius: 4, fontSize: 12 }}>
                  <span style={{ color: "#8b949e" }}>{k.replace("alt_", "").replace(/_/g, " ")}</span>
                  <span style={{ color: "#58a6ff", fontWeight: 600, fontFamily: "monospace" }}>{fmt(v)}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
