import { useState } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 20, fontWeight: 700, color: "#f0f6fc", marginBottom: 4 },
  sub: { fontSize: 12, color: "#8b949e", marginBottom: 24 },
  grid2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 },
  grid3: { display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sHdr: { fontSize: 14, fontWeight: 700, color: "#f0883e", marginBottom: 12 },
  label: { fontSize: 11, color: "#8b949e", marginBottom: 4, display: "block" },
  input: { width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", padding: "6px 10px", fontSize: 13, boxSizing: "border-box" },
  select: { width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", padding: "6px 10px", fontSize: 13 },
  btn: { background: "#238636", color: "#fff", border: "none", borderRadius: 6, padding: "8px 18px", fontSize: 13, cursor: "pointer", fontWeight: 600, marginTop: 8 },
  card: { background: "#161b22", borderRadius: 6, padding: "10px 14px" },
  cardLabel: { fontSize: 10, color: "#8b949e", textTransform: "uppercase" },
  cardVal: { fontSize: 14, fontWeight: 700, color: "#f0f6fc", marginTop: 2 },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 11 },
  th: { background: "#161b22", padding: "6px 10px", textAlign: "left", color: "#8b949e", fontWeight: 600 },
  td: { padding: "5px 10px", borderBottom: "1px solid #21262d", color: "#f0f6fc" },
  err: { color: "#ff7b72", fontSize: 12, marginTop: 8 },
  badge: (c) => ({ display: "inline-block", fontSize: 10, padding: "2px 6px", borderRadius: 4, background: c + "22", color: c }),
};

const DEFAULT_PRICES = Array.from({ length: 100 }, (_, i) => (100 + i * 0.5 + Math.sin(i * 0.3) * 3).toFixed(2)).join(",");

export default function M19WalkForwardAnalyzer() {
  const [strategy, setStrategy] = useState("momentum");
  const [ticker, setTicker] = useState("AAPL");
  const [pricesText, setPricesText] = useState(DEFAULT_PRICES);
  const [isBars, setIsBars] = useState("40");
  const [oosBars, setOosBars] = useState("20");
  const [mode, setMode] = useState("ROLLING");
  const [result, setResult] = useState(null);
  const [windows, setWindows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const run = async () => {
    setLoading(true); setErr("");
    const prices = pricesText.split(",").map(p => parseFloat(p.trim())).filter(p => !isNaN(p));
    const bars = prices.map((p, i) => ({
      date: `2024-${String(1 + Math.floor(i / 28)).padStart(2, "0")}-${String((i % 28) + 1).padStart(2, "0")}`,
      open: p, high: p * 1.01, low: p * 0.99, close: p, volume: 10000,
    }));
    try {
      const r = await fetch("/quant/walk-forward/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          strategy_name: strategy,
          price_data: { [ticker]: bars },
          in_sample_bars: parseInt(isBars),
          out_sample_bars: parseInt(oosBars),
          window_mode: mode,
        }),
      });
      const d = await r.json();
      if (!r.ok) { setErr(JSON.stringify(d)); }
      else {
        setResult(d);
        const wResp = await fetch(`/quant/walk-forward/${d.run_id}/windows`);
        if (wResp.ok) setWindows(await wResp.json());
      }
    } catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  };

  const stab = result?.stability;

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Walk-Forward Analyzer</div>
      <div style={S.sub}>Validate strategy robustness by testing on rolling out-of-sample windows.</div>

      <div style={S.section}>
        <div style={S.sHdr}>Configuration</div>
        <div style={S.grid2}>
          <div>
            <label style={S.label}>Strategy Name</label>
            <input style={S.input} value={strategy} onChange={e => setStrategy(e.target.value)} />
          </div>
          <div>
            <label style={S.label}>Ticker</label>
            <input style={S.input} value={ticker} onChange={e => setTicker(e.target.value)} />
          </div>
          <div>
            <label style={S.label}>In-Sample Bars</label>
            <input style={S.input} value={isBars} onChange={e => setIsBars(e.target.value)} />
          </div>
          <div>
            <label style={S.label}>Out-of-Sample Bars</label>
            <input style={S.input} value={oosBars} onChange={e => setOosBars(e.target.value)} />
          </div>
          <div>
            <label style={S.label}>Window Mode</label>
            <select style={S.select} value={mode} onChange={e => setMode(e.target.value)}>
              <option>ROLLING</option><option>EXPANDING</option>
            </select>
          </div>
        </div>
        <div>
          <label style={S.label}>Prices (comma-separated)</label>
          <input style={S.input} value={pricesText} onChange={e => setPricesText(e.target.value)} />
        </div>
        <button style={S.btn} onClick={run} disabled={loading}>{loading ? "Running…" : "Run Walk-Forward"}</button>
        {err && <div style={S.err}>{err}</div>}
      </div>

      {stab && (
        <div style={S.section}>
          <div style={S.sHdr}>Stability Metrics</div>
          <div style={S.grid3}>
            {[
              ["Windows", stab.num_windows],
              ["Avg OOS Sharpe", stab.avg_oos_sharpe?.toFixed(3)],
              ["Avg Efficiency", stab.avg_efficiency?.toFixed(3)],
              ["% Positive", `${(stab.pct_windows_positive * 100).toFixed(1)}%`],
              ["Stability Score", stab.stability_score?.toFixed(3)],
              ["Degradation", stab.degradation?.toFixed(3)],
            ].map(([label, val]) => (
              <div key={label} style={S.card}>
                <div style={S.cardLabel}>{label}</div>
                <div style={S.cardVal}>{val}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {windows.length > 0 && (
        <div style={S.section}>
          <div style={S.sHdr}>Window Results ({windows.length})</div>
          <table style={S.table}>
            <thead>
              <tr>
                {["#", "IS Sharpe", "OOS Sharpe", "Efficiency", "OOS Return", "Status"].map(h => (
                  <th key={h} style={S.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {windows.map((w, i) => (
                <tr key={i}>
                  <td style={S.td}>{i + 1}</td>
                  <td style={S.td}>{w.in_sample_sharpe?.toFixed(3)}</td>
                  <td style={S.td}>{w.out_sample_sharpe?.toFixed(3)}</td>
                  <td style={S.td}>{w.efficiency?.toFixed(3)}</td>
                  <td style={S.td}>{(w.out_sample_return * 100)?.toFixed(2)}%</td>
                  <td style={S.td}>
                    <span style={S.badge(w.out_sample_sharpe >= 0 ? "#3fb950" : "#ff7b72")}>
                      {w.out_sample_sharpe >= 0 ? "Positive" : "Negative"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
