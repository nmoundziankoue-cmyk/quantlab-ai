import { useState } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 20, fontWeight: 700, color: "#f0f6fc", marginBottom: 4 },
  sub: { fontSize: 12, color: "#8b949e", marginBottom: 24 },
  grid3: { display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12, marginBottom: 16 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sHdr: { fontSize: 14, fontWeight: 700, color: "#ff9f43", marginBottom: 12 },
  label: { fontSize: 11, color: "#8b949e", marginBottom: 4, display: "block" },
  input: { width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", padding: "6px 10px", fontSize: 13, boxSizing: "border-box" },
  btn: { background: "#238636", color: "#fff", border: "none", borderRadius: 6, padding: "8px 18px", fontSize: 13, cursor: "pointer", fontWeight: 600 },
  card: { background: "#161b22", borderRadius: 6, padding: "10px 14px" },
  cardLabel: { fontSize: 10, color: "#8b949e", textTransform: "uppercase" },
  cardVal: { fontSize: 14, fontWeight: 700, marginTop: 2 },
  err: { color: "#ff7b72", fontSize: 12, marginTop: 8 },
  scenBtn: (a) => ({ padding: "8px 14px", fontSize: 12, cursor: "pointer", borderRadius: 6, border: "1px solid " + (a ? "#ff9f43" : "#30363d"), background: a ? "#ff9f4322" : "#161b22", color: a ? "#ff9f43" : "#8b949e", fontFamily: "monospace" }),
  table: { width: "100%", borderCollapse: "collapse", fontSize: 11 },
  th: { background: "#161b22", padding: "6px 10px", textAlign: "left", color: "#8b949e" },
  td: { padding: "5px 10px", borderBottom: "1px solid #21262d", color: "#f0f6fc" },
};

const SCENARIOS = [
  { key: "2008-crash", label: "2008 Financial Crisis", driftShock: -0.05, volShock: 2.0 },
  { key: "covid-2020", label: "COVID-19 2020", driftShock: -0.03, volShock: 1.8 },
  { key: "2022-bear", label: "2022 Bear Market", driftShock: -0.02, volShock: 1.4 },
  { key: "bull-2017", label: "Bull Market 2017", driftShock: 0.03, volShock: 0.6 },
  { key: "custom", label: "Custom Scenario", driftShock: 0, volShock: 1.0 },
];

export default function M19ScenarioEngine() {
  const [selected, setSelected] = useState("covid-2020");
  const [customDrift, setCustomDrift] = useState("0.0");
  const [customVol, setCustomVol] = useState("1.0");
  const [numPaths, setNumPaths] = useState("200");
  const [numSteps, setNumSteps] = useState("126");
  const [baseDrift, setBaseDrift] = useState("0.0003");
  const [baseVol, setBaseVol] = useState("0.012");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const runScenario = async () => {
    setLoading(true); setErr("");
    const scenario = SCENARIOS.find(s => s.key === selected);
    const dShock = selected === "custom" ? parseFloat(customDrift) : scenario.driftShock;
    const vShock = selected === "custom" ? parseFloat(customVol) : scenario.volShock;
    const finalDrift = parseFloat(baseDrift) + dShock;
    const finalVol = parseFloat(baseVol) * vShock;
    try {
      const r = await fetch("/quant/monte-carlo/gbm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mean_daily_return: finalDrift, daily_volatility: finalVol, num_paths: parseInt(numPaths), num_steps: parseInt(numSteps) }),
      });
      const d = await r.json();
      if (!r.ok) { setErr(JSON.stringify(d)); return; }
      const label = scenario.label;
      setResults(prev => {
        const filtered = prev.filter(x => x.label !== label);
        return [...filtered, { label, drift: finalDrift, vol: finalVol, ...d }];
      });
    } catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  };

  const currScenario = SCENARIOS.find(s => s.key === selected);

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Scenario Engine</div>
      <div style={S.sub}>Stress-test portfolios under historical and custom market scenarios via Monte Carlo.</div>

      <div style={S.section}>
        <div style={S.sHdr}>Scenario Selection</div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
          {SCENARIOS.map(sc => (
            <button key={sc.key} style={S.scenBtn(selected === sc.key)} onClick={() => setSelected(sc.key)}>{sc.label}</button>
          ))}
        </div>

        {selected !== "custom" && currScenario && (
          <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 12 }}>
            Drift shock: <span style={{ color: currScenario.driftShock < 0 ? "#ff7b72" : "#3fb950" }}>{currScenario.driftShock > 0 ? "+" : ""}{(currScenario.driftShock * 100).toFixed(1)}%</span>
            &nbsp;| Vol multiplier: <span style={{ color: "#e3b341" }}>{currScenario.volShock}×</span>
          </div>
        )}

        {selected === "custom" && (
          <div style={S.grid3}>
            <div><label style={S.label}>Drift Shock (abs)</label><input style={S.input} value={customDrift} onChange={e => setCustomDrift(e.target.value)} /></div>
            <div><label style={S.label}>Vol Multiplier</label><input style={S.input} value={customVol} onChange={e => setCustomVol(e.target.value)} /></div>
          </div>
        )}

        <div style={S.grid3}>
          <div><label style={S.label}>Base Daily Drift</label><input style={S.input} value={baseDrift} onChange={e => setBaseDrift(e.target.value)} /></div>
          <div><label style={S.label}>Base Daily Vol</label><input style={S.input} value={baseVol} onChange={e => setBaseVol(e.target.value)} /></div>
          <div><label style={S.label}>Num Paths</label><input style={S.input} value={numPaths} onChange={e => setNumPaths(e.target.value)} /></div>
        </div>
        <div style={{ marginTop: 4 }}>
          <label style={S.label}>Steps (trading days)</label>
          <input style={{ ...S.input, maxWidth: 200 }} value={numSteps} onChange={e => setNumSteps(e.target.value)} />
        </div>

        <div style={{ marginTop: 12 }}>
          <button style={S.btn} onClick={runScenario} disabled={loading}>{loading ? "Running…" : "Run Scenario"}</button>
        </div>
        {err && <div style={S.err}>{err}</div>}
      </div>

      {results.length > 0 && (
        <div style={S.section}>
          <div style={S.sHdr}>Scenario Results</div>
          <table style={S.table}>
            <thead>
              <tr>{["Scenario", "Drift", "Vol", "VaR 95%", "VaR 99%", "P(Ruin)", "Max DD p50"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {results.map((r, i) => (
                <tr key={i}>
                  <td style={{ ...S.td, color: "#ff9f43" }}>{r.label}</td>
                  <td style={{ ...S.td, color: r.drift < 0 ? "#ff7b72" : "#3fb950" }}>{(r.drift * 100).toFixed(3)}%</td>
                  <td style={{ ...S.td, color: "#e3b341" }}>{(r.vol * 100).toFixed(3)}%</td>
                  <td style={S.td}>{(r.var_95 * 100).toFixed(2)}%</td>
                  <td style={S.td}>{(r.var_99 * 100).toFixed(2)}%</td>
                  <td style={{ ...S.td, color: r.probability_of_ruin > 0.05 ? "#ff7b72" : "#3fb950" }}>{(r.probability_of_ruin * 100).toFixed(2)}%</td>
                  <td style={S.td}>{(r.max_drawdown_p50 * 100).toFixed(2)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
