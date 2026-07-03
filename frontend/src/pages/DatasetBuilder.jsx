import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { marketDataApi } from "../api/marketDataApi";

const S = {
  page: { padding: 28, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" },
  card: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20, marginBottom: 16 },
  title: { fontSize: 13, fontWeight: 700, color: "#8b949e", letterSpacing: "0.06em", marginBottom: 14, textTransform: "uppercase" },
  label: { fontSize: 12, color: "#8b949e", marginBottom: 4, display: "block" },
  input: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "9px 12px", fontSize: 13, width: "100%", boxSizing: "border-box" },
  select: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "9px 12px", fontSize: 13, width: "100%", boxSizing: "border-box" },
  btn: { background: "#1f6feb", border: "none", borderRadius: 6, color: "#fff", padding: "10px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer" },
  btnGreen: { background: "#238636", border: "none", borderRadius: 6, color: "#fff", padding: "10px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer" },
  err: { background: "#2d1317", border: "1px solid #f85149", borderRadius: 6, color: "#f85149", padding: "10px 14px", fontSize: 13, marginBottom: 14 },
  metricBox: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 6, padding: "12px 14px", textAlign: "center" },
  metricValue: { fontSize: 22, fontWeight: 700, color: "#58a6ff", lineHeight: 1.2 },
  metricLabel: { fontSize: 11, color: "#8b949e", marginTop: 4, textTransform: "uppercase", letterSpacing: "0.06em" },
  splitCard: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 6, padding: 16, flex: 1 },
  pill: { display: "inline-block", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600 },
};

const SPLIT_COLORS = { train: "#1f6feb", val: "#d29922", test: "#3fb950" };

function generateSyntheticBars(n = 500, seed = 42) {
  // LCG pseudo-random for determinism (no Math.random)
  let state = seed;
  const rand = () => { state = (state * 1664525 + 1013904223) & 0xffffffff; return (state >>> 0) / 0xffffffff; };
  const bars = [];
  let close = 100;
  const start = new Date("2021-01-04");
  for (let i = 0; i < n; i++) {
    const ret = (rand() - 0.5) * 0.03;
    close *= (1 + ret);
    const high = close * (1 + rand() * 0.008);
    const low = close * (1 - rand() * 0.008);
    const open = close * (1 + (rand() - 0.5) * 0.004);
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    bars.push({ timestamp: d.toISOString(), open: Math.max(low, Math.min(high, open)), high, low, close, volume: 1e6 + rand() * 4e6 });
  }
  return bars;
}

export default function DatasetBuilderPage() {
  const [symbol, setSymbol] = useState("AAPL");
  const [labelType, setLabelType] = useState("classification");
  const [labelHorizon, setLabelHorizon] = useState(1);
  const [trainRatio, setTrainRatio] = useState(0.70);
  const [valRatio, setValRatio] = useState(0.15);
  const [result, setResult] = useState(null);

  const testRatio = Math.max(0, +(1 - trainRatio - valRatio).toFixed(2));

  const mut = useMutation({
    mutationFn: () => marketDataApi.buildDataset({
      symbol: symbol.toUpperCase(),
      bars: generateSyntheticBars(500),
      label_horizon: labelHorizon,
      label_type: labelType,
      train_ratio: trainRatio,
      val_ratio: valRatio,
      test_ratio: testRatio,
      drop_na: true,
    }).then(r => r.data),
    onSuccess: setResult,
  });

  return (
    <div style={S.page}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Dataset Builder</h1>
        <p style={{ color: "#8b949e", margin: "4px 0 0", fontSize: 13 }}>
          Generate train/val/test splits with feature engineering and label generation for ML models
        </p>
      </div>

      <div style={S.card}>
        <div style={S.title}>Configuration</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 14, marginBottom: 16 }}>
          <div>
            <label style={S.label}>Symbol</label>
            <input style={S.input} value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} />
          </div>
          <div>
            <label style={S.label}>Label Type</label>
            <select style={S.select} value={labelType} onChange={e => setLabelType(e.target.value)}>
              <option value="classification">Classification (up/down/flat)</option>
              <option value="regression">Regression (forward return)</option>
              <option value="forecasting">Forecasting (future price)</option>
            </select>
          </div>
          <div>
            <label style={S.label}>Label Horizon (bars)</label>
            <input style={S.input} type="number" min={1} max={63} value={labelHorizon} onChange={e => setLabelHorizon(+e.target.value)} />
          </div>
          <div>
            <label style={S.label}>Train / Val / Test</label>
            <div style={{ display: "flex", gap: 6 }}>
              <input style={{ ...S.input, textAlign: "center" }} type="number" step="0.05" min="0.1" max="0.9" value={trainRatio} onChange={e => setTrainRatio(+e.target.value)} placeholder="Train" />
              <input style={{ ...S.input, textAlign: "center" }} type="number" step="0.05" min="0.05" max="0.4" value={valRatio} onChange={e => setValRatio(+e.target.value)} placeholder="Val" />
              <div style={{ ...S.input, textAlign: "center", background: "#1a1f2e", color: "#8b949e" }}>{testRatio.toFixed(2)}</div>
            </div>
          </div>
        </div>

        {/* Ratio bar */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", height: 16, borderRadius: 4, overflow: "hidden", gap: 1 }}>
            {["train", "val", "test"].map((s, i) => {
              const ratio = i === 0 ? trainRatio : i === 1 ? valRatio : testRatio;
              return <div key={s} style={{ flex: ratio, background: SPLIT_COLORS[s], display: "flex", alignItems: "center", justifyContent: "center" }}>
                <span style={{ fontSize: 10, color: "#fff", fontWeight: 700 }}>{(ratio * 100).toFixed(0)}%</span>
              </div>;
            })}
          </div>
          <div style={{ display: "flex", gap: 16, marginTop: 6 }}>
            {["train", "val", "test"].map(s => (
              <span key={s} style={{ fontSize: 11, color: "#8b949e" }}>
                <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: 2, background: SPLIT_COLORS[s], marginRight: 4 }} />{s}
              </span>
            ))}
          </div>
        </div>

        <button style={{ ...S.btnGreen, ...(mut.isPending ? { opacity: 0.5 } : {}) }}
          onClick={() => mut.mutate()} disabled={mut.isPending}>
          {mut.isPending ? "Building…" : "Build Dataset (500 synthetic bars)"}
        </button>
      </div>

      {mut.error && <div style={S.err}>{mut.error.response?.data?.detail || mut.error.message}</div>}

      {result && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 16 }}>
            <div style={S.metricBox}><div style={S.metricValue}>{result.total_samples}</div><div style={S.metricLabel}>Total Samples</div></div>
            <div style={S.metricBox}><div style={S.metricValue}>{result.feature_names?.length || 0}</div><div style={S.metricLabel}>Features</div></div>
            <div style={S.metricBox}><div style={S.metricValue}>{result.label_horizon}</div><div style={S.metricLabel}>Label Horizon (bars)</div></div>
          </div>

          <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
            {(result?.splits ?? []).map(sp => (
              <div key={sp.split} style={{ ...S.splitCard, borderLeft: `3px solid ${SPLIT_COLORS[sp.split]}` }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: SPLIT_COLORS[sp.split], marginBottom: 8, textTransform: "uppercase" }}>{sp.split}</div>
                <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>{sp.n_samples.toLocaleString()} rows</div>
                <div style={{ fontSize: 11, color: "#8b949e" }}>{sp.n_features} features</div>
                {sp.start_date && <div style={{ fontSize: 11, color: "#8b949e", marginTop: 4 }}>{sp.start_date?.slice(0, 10)} → {sp.end_date?.slice(0, 10)}</div>}
              </div>
            ))}
          </div>

          {result.feature_names && (
            <div style={S.card}>
              <div style={S.title}>Features in Dataset ({result.feature_names.length})</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {result.feature_names.map(f => (
                  <span key={f} style={{ ...S.pill, background: "#21262d", color: "#e6edf3", border: "1px solid #30363d" }}>{f}</span>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
