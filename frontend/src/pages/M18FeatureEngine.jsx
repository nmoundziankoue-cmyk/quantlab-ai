import { useState, useEffect } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 18, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 18, marginBottom: 14 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#f0883e", marginBottom: 12 },
  row2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 },
  input: { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, padding: "6px 10px", color: "#f0f6fc", fontSize: 12, marginRight: 8, width: 110 },
  btn: (c="#f0883e") => ({ background: c + "22", border: `1px solid ${c}55`, borderRadius: 6, padding: "6px 14px", color: c, fontSize: 12, cursor: "pointer", fontFamily: "monospace", marginRight: 6 }),
  result: { background: "#161b22", borderRadius: 6, padding: 10, fontSize: 12, color: "#c9d1d9", marginTop: 10 },
  kv: { display: "flex", justifyContent: "space-between", padding: "3px 0", borderBottom: "1px solid #21262d33" },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 11 },
  th: { color: "#8b949e", textAlign: "left", padding: "4px 8px", borderBottom: "1px solid #21262d" },
  td: { padding: "5px 8px", color: "#c9d1d9", borderBottom: "1px solid #161b22" },
};

const FEATURES = [
  { label: "Rolling Mean", endpoint: (t, w) => `/m18/features/rolling-mean/${t}?window=${w}`, key: "value" },
  { label: "Rolling Std", endpoint: (t, w) => `/m18/features/rolling-std/${t}?window=${w}`, key: "value" },
  { label: "ATR", endpoint: (t, w) => `/m18/features/atr/${t}?window=${w}`, key: "atr" },
  { label: "VWAP", endpoint: (t) => `/m18/features/vwap/${t}`, key: "vwap" },
  { label: "TWAP", endpoint: (t) => `/m18/features/twap/${t}`, key: "twap" },
  { label: "Realized Vol", endpoint: (t, w) => `/m18/features/realized-vol/${t}?window=${w}`, key: "realized_vol" },
  { label: "Rolling Sharpe", endpoint: (t, w) => `/m18/features/sharpe/${t}?window=${w}`, key: "sharpe" },
  { label: "Rolling VaR", endpoint: (t, w) => `/m18/features/var/${t}?window=${w}`, key: "var" },
];

export default function M18FeatureEngine() {
  const [ticker, setTicker] = useState("AAPL");
  const [price, setPrice] = useState("175.50");
  const [volume, setVolume] = useState("5000");
  const [high, setHigh] = useState("176.00");
  const [low, setLow] = useState("174.50");
  const [window, setWindow] = useState("20");
  const [snapshot, setSnapshot] = useState(null);
  const [rsi, setRsi] = useState(null);
  const [macd, setMacd] = useState(null);
  const [results, setResults] = useState({});
  const [msg, setMsg] = useState("");

  const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  const seedData = async () => {
    const t = ticker.toUpperCase();
    const base = parseFloat(price);
    for (let i = 0; i < 60; i++) {
      const p = base * (1 + (Math.random() - 0.5) * 0.02);
      const h = p * 1.005;
      const l = p * 0.995;
      await post("/m18/features/update", { ticker: t, price: p, volume: parseFloat(volume) * (0.8 + Math.random() * 0.4), high: h, low: l });
    }
    setMsg(`Seeded 60 observations for ${t}`);
    refreshAll();
  };

  const refreshAll = async () => {
    const t = ticker.toUpperCase();
    const w = parseInt(window);
    const snap = await fetch(`/m18/features/snapshot/${t}`).then(r => r.ok ? r.json() : null).catch(() => null);
    setSnapshot(snap);
    const r = await post("/m18/features/rsi", { ticker: t, window: 14 });
    if (r.ok) setRsi(await r.json()); else setRsi(null);
    const m = await post("/m18/features/macd", { ticker: t, fast: 12, slow: 26, signal: 9 });
    if (m.ok) setMacd(await m.json()); else setMacd(null);
    const res = {};
    for (const f of FEATURES) {
      const url = f.endpoint(t, w);
      const d = await fetch(url).then(r => r.ok ? r.json() : null).catch(() => null);
      if (d) res[f.label] = d[f.key];
    }
    setResults(res);
  };

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Feature Engine (21 Indicators)</div>

      <div style={S.section}>
        <div style={S.sHdr}>Seed Data</div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          {[["Ticker", ticker, setTicker, 80], ["Price", price, setPrice, 90], ["Volume", volume, setVolume, 90], ["High", high, setHigh, 90], ["Low", low, setLow, 90], ["Window", window, setWindow, 70]].map(([label, val, set, w]) => (
            <div key={label}>
              <div style={{ fontSize: 10, color: "#8b949e", marginBottom: 2 }}>{label}</div>
              <input style={{ ...S.input, width: w, marginRight: 0 }} value={val} onChange={e => set(e.target.value)} />
            </div>
          ))}
          <div style={{ marginTop: 14 }}>
            <button style={S.btn()} onClick={seedData}>Seed 60 Observations</button>
            <button style={S.btn("#58a6ff")} onClick={refreshAll}>Refresh All</button>
          </div>
        </div>
        {msg && <div style={{ marginTop: 8, fontSize: 11, color: "#8b949e" }}>{msg}</div>}
      </div>

      <div style={S.row2}>
        <div style={S.section}>
          <div style={S.sHdr}>RSI & MACD</div>
          {rsi && <div style={{ fontSize: 13, marginBottom: 8 }}>RSI(14): <b style={{ color: rsi.rsi > 70 ? "#ff7b72" : rsi.rsi < 30 ? "#3fb950" : "#f0883e" }}>{rsi.rsi?.toFixed(2)}</b></div>}
          {macd && (
            <div>
              <div style={{ fontSize: 12, color: "#c9d1d9", marginBottom: 4 }}>MACD Line: <b style={{ color: "#58a6ff" }}>{macd.macd_line?.toFixed(4)}</b></div>
              <div style={{ fontSize: 12, color: "#c9d1d9", marginBottom: 4 }}>Signal Line: <b style={{ color: "#e3b341" }}>{macd.signal_line?.toFixed(4)}</b></div>
              <div style={{ fontSize: 12, color: "#c9d1d9" }}>Histogram: <b style={{ color: macd.histogram >= 0 ? "#3fb950" : "#ff7b72" }}>{macd.histogram?.toFixed(4)}</b></div>
            </div>
          )}
          {!rsi && !macd && <div style={{ color: "#8b949e", fontSize: 12 }}>Seed data first.</div>}
        </div>

        <div style={S.section}>
          <div style={S.sHdr}>All Features (window={window})</div>
          {Object.keys(results).length === 0 ? <div style={{ color: "#8b949e", fontSize: 12 }}>Seed data first.</div> : (
            Object.entries(results).map(([label, val]) => (
              <div key={label} style={S.kv}>
                <span style={{ color: "#8b949e" }}>{label}</span>
                <span style={{ color: "#f0883e" }}>{val != null ? val.toFixed(6) : "N/A"}</span>
              </div>
            ))
          )}
        </div>
      </div>

      {snapshot && (
        <div style={S.section}>
          <div style={S.sHdr}>Feature Snapshot — {snapshot.ticker}</div>
          <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 8 }}>Data points: {snapshot.data_points}</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 8 }}>
            {Object.entries(snapshot.features || {}).filter(([, v]) => v != null).map(([k, v]) => (
              <div key={k} style={{ background: "#161b22", borderRadius: 6, padding: "6px 10px" }}>
                <div style={{ fontSize: 10, color: "#8b949e" }}>{k}</div>
                <div style={{ fontSize: 12, color: "#f0f6fc", fontWeight: 700 }}>{typeof v === "number" ? v.toFixed(4) : String(v)}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
