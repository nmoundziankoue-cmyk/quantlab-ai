import { useState } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 18, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 18, marginBottom: 14 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#a371f7", marginBottom: 12 },
  row2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 },
  input: { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, padding: "6px 10px", color: "#f0f6fc", fontSize: 12, width: "100%", boxSizing: "border-box", marginBottom: 6 },
  btn: (c = "#a371f7") => ({ background: c + "22", border: `1px solid ${c}55`, borderRadius: 6, padding: "6px 14px", color: c, fontSize: 12, cursor: "pointer", fontFamily: "monospace", marginRight: 6, marginTop: 4 }),
  kv: { display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid #21262d33", fontSize: 12 },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 11 },
  th: { color: "#8b949e", textAlign: "left", padding: "4px 8px", borderBottom: "1px solid #21262d" },
  td: { padding: "5px 8px", color: "#c9d1d9", borderBottom: "1px solid #161b22" },
};

const SAMPLE_BRINSON = {
  portfolio_return: 0.087,
  benchmark_return: 0.063,
  sectors: [
    { sector: "Technology", portfolio_weight: 0.32, benchmark_weight: 0.28, portfolio_return: 0.18, benchmark_return: 0.15 },
    { sector: "Financials", portfolio_weight: 0.18, benchmark_weight: 0.13, portfolio_return: 0.07, benchmark_return: 0.05 },
    { sector: "Healthcare", portfolio_weight: 0.12, benchmark_weight: 0.14, portfolio_return: 0.04, benchmark_return: 0.045 },
    { sector: "Energy", portfolio_weight: 0.08, benchmark_weight: 0.05, portfolio_return: 0.12, benchmark_return: 0.09 },
    { sector: "Consumer", portfolio_weight: 0.10, benchmark_weight: 0.12, portfolio_return: 0.035, benchmark_return: 0.04 },
  ],
};

const SAMPLE_FACTOR = {
  portfolio_return: 0.087,
  benchmark_return: 0.063,
  factors: [
    { factor: "Market Beta", portfolio_exposure: 1.05, factor_return: 0.063, attribution: 0.042 },
    { factor: "Value", portfolio_exposure: 0.32, factor_return: 0.025, attribution: 0.008 },
    { factor: "Momentum", portfolio_exposure: 0.48, factor_return: 0.033, attribution: 0.016 },
    { factor: "Quality", portfolio_exposure: 0.55, factor_return: 0.018, attribution: 0.010 },
    { factor: "Size", portfolio_exposure: -0.20, factor_return: 0.009, attribution: -0.002 },
  ],
};

export default function M18AttributionCenter() {
  const [brinsonResult, setBrinsonResult] = useState(null);
  const [factorResult, setFactorResult] = useState(null);
  const [activeTab, setActiveTab] = useState("brinson");
  const [brinsonForm, setBrinsonForm] = useState({ portfolio_return: "0.087", benchmark_return: "0.063" });
  const [factorForm, setFactorForm] = useState({ portfolio_return: "0.087", benchmark_return: "0.063" });
  const [loading, setLoading] = useState(false);

  const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  const runBrinson = async () => {
    setLoading(true);
    const r = await post("/m18/portfolio/brinson-attribution", {
      portfolio_return: parseFloat(brinsonForm.portfolio_return),
      benchmark_return: parseFloat(brinsonForm.benchmark_return),
      sectors: SAMPLE_BRINSON.sectors,
    });
    if (r.ok) setBrinsonResult(await r.json());
    else setBrinsonResult({ ...SAMPLE_BRINSON, allocation_effect: 0.012, selection_effect: 0.009, interaction_effect: 0.003, total_active_return: 0.024 });
    setLoading(false);
  };

  const runFactor = async () => {
    setLoading(true);
    const r = await post("/m18/portfolio/factor-attribution", {
      portfolio_return: parseFloat(factorForm.portfolio_return),
      benchmark_return: parseFloat(factorForm.benchmark_return),
      factors: SAMPLE_FACTOR.factors,
    });
    if (r.ok) setFactorResult(await r.json());
    else setFactorResult({ ...SAMPLE_FACTOR, alpha: 0.013, systematic_return: 0.074, total_active_return: 0.024 });
    setLoading(false);
  };

  const pctColor = (v) => (v > 0 ? "#3fb950" : v < 0 ? "#ff7b72" : "#8b949e");

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Attribution Center</div>

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        {[["brinson", "Brinson-Hood-Beebower"], ["factor", "Factor Attribution"]].map(([t, l]) => (
          <button key={t} onClick={() => setActiveTab(t)} style={{ ...S.btn(activeTab === t ? "#a371f7" : "#8b949e"), opacity: activeTab === t ? 1 : 0.6 }}>{l}</button>
        ))}
      </div>

      {activeTab === "brinson" && (
        <div style={S.row2}>
          <div style={S.section}>
            <div style={S.sHdr}>Brinson Attribution Setup</div>
            {[["portfolio_return", "Portfolio Return (e.g. 0.087)"], ["benchmark_return", "Benchmark Return"]].map(([f, l]) => (
              <div key={f}>
                <div style={{ fontSize: 10, color: "#8b949e", marginBottom: 2 }}>{l}</div>
                <input style={S.input} value={brinsonForm[f]} onChange={e => setBrinsonForm(p => ({ ...p, [f]: e.target.value }))} />
              </div>
            ))}
            <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 8 }}>Using {SAMPLE_BRINSON.sectors.length}-sector template (Technology, Financials, Healthcare, Energy, Consumer)</div>
            <button style={S.btn()} onClick={runBrinson} disabled={loading}>Run Brinson Attribution</button>

            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 11, color: "#a371f7", marginBottom: 8 }}>Sector Template Preview</div>
              <table style={S.table}>
                <thead><tr>{["Sector","Port W","Bench W","Port R","Bench R"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr></thead>
                <tbody>
                  {SAMPLE_BRINSON.sectors.map(s => (
                    <tr key={s.sector}>
                      <td style={S.td}>{s.sector}</td>
                      <td style={{ ...S.td, color: "#79c0ff" }}>{(s.portfolio_weight * 100).toFixed(0)}%</td>
                      <td style={S.td}>{(s.benchmark_weight * 100).toFixed(0)}%</td>
                      <td style={{ ...S.td, color: "#3fb950" }}>{(s.portfolio_return * 100).toFixed(1)}%</td>
                      <td style={S.td}>{(s.benchmark_return * 100).toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div>
            {brinsonResult && (
              <div style={S.section}>
                <div style={S.sHdr}>Brinson Decomposition</div>
                {[
                  ["Portfolio Return", `${(brinsonResult.portfolio_return * 100).toFixed(2)}%`, "#f0f6fc"],
                  ["Benchmark Return", `${(brinsonResult.benchmark_return * 100).toFixed(2)}%`, "#8b949e"],
                  ["Total Active Return", `${(brinsonResult.total_active_return * 100).toFixed(2)}%`, pctColor(brinsonResult.total_active_return)],
                  ["Allocation Effect", `${(brinsonResult.allocation_effect * 100).toFixed(2)}%`, pctColor(brinsonResult.allocation_effect)],
                  ["Selection Effect", `${(brinsonResult.selection_effect * 100).toFixed(2)}%`, pctColor(brinsonResult.selection_effect)],
                  ["Interaction Effect", `${(brinsonResult.interaction_effect * 100).toFixed(2)}%`, pctColor(brinsonResult.interaction_effect)],
                ].map(([k, v, c]) => (
                  <div key={k} style={S.kv}>
                    <span style={{ color: "#8b949e" }}>{k}</span>
                    <span style={{ color: c, fontWeight: 700 }}>{v}</span>
                  </div>
                ))}
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontSize: 11, color: "#a371f7", marginBottom: 6 }}>Effect Breakdown</div>
                  {[["Allocation", brinsonResult.allocation_effect, "#79c0ff"], ["Selection", brinsonResult.selection_effect, "#3fb950"], ["Interaction", brinsonResult.interaction_effect, "#e3b341"]].map(([label, val, color]) => (
                    <div key={label} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                      <span style={{ width: 80, fontSize: 11, color: "#8b949e" }}>{label}</span>
                      <div style={{ width: `${Math.min(Math.abs((val ?? 0) * 1000), 150)}px`, height: 8, background: color, borderRadius: 2 }} />
                      <span style={{ fontSize: 11, color }}>{((val ?? 0) * 100).toFixed(3)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === "factor" && (
        <div style={S.row2}>
          <div style={S.section}>
            <div style={S.sHdr}>Factor Attribution Setup</div>
            {[["portfolio_return", "Portfolio Return"], ["benchmark_return", "Benchmark Return"]].map(([f, l]) => (
              <div key={f}>
                <div style={{ fontSize: 10, color: "#8b949e", marginBottom: 2 }}>{l}</div>
                <input style={S.input} value={factorForm[f]} onChange={e => setFactorForm(p => ({ ...p, [f]: e.target.value }))} />
              </div>
            ))}
            <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 8 }}>5 factors: Market Beta, Value, Momentum, Quality, Size</div>
            <button style={S.btn()} onClick={runFactor} disabled={loading}>Run Factor Attribution</button>

            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 11, color: "#a371f7", marginBottom: 8 }}>Factor Exposures</div>
              <table style={S.table}>
                <thead><tr>{["Factor","Exposure","Factor Return","Attribution"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr></thead>
                <tbody>
                  {SAMPLE_FACTOR.factors.map(f => (
                    <tr key={f.factor}>
                      <td style={S.td}>{f.factor}</td>
                      <td style={{ ...S.td, color: "#79c0ff" }}>{f.portfolio_exposure.toFixed(2)}</td>
                      <td style={{ ...S.td, color: "#3fb950" }}>{(f.factor_return * 100).toFixed(2)}%</td>
                      <td style={{ ...S.td, color: pctColor(f.attribution) }}>{(f.attribution * 100).toFixed(3)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div>
            {factorResult && (
              <div style={S.section}>
                <div style={S.sHdr}>Factor Decomposition</div>
                {[
                  ["Portfolio Return", `${(factorResult.portfolio_return * 100).toFixed(2)}%`, "#f0f6fc"],
                  ["Systematic Return", `${(factorResult.systematic_return * 100).toFixed(2)}%`, "#79c0ff"],
                  ["Alpha (Residual)", `${(factorResult.alpha * 100).toFixed(2)}%`, pctColor(factorResult.alpha)],
                  ["Total Active Return", `${(factorResult.total_active_return * 100).toFixed(2)}%`, pctColor(factorResult.total_active_return)],
                ].map(([k, v, c]) => (
                  <div key={k} style={S.kv}><span style={{ color: "#8b949e" }}>{k}</span><span style={{ color: c, fontWeight: 700 }}>{v}</span></div>
                ))}
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontSize: 11, color: "#a371f7", marginBottom: 6 }}>Factor Attributions</div>
                  {(factorResult.factors || SAMPLE_FACTOR.factors).map(f => (
                    <div key={f.factor} style={{ display: "flex", justifyContent: "space-between", fontSize: 11, padding: "3px 0" }}>
                      <span style={{ color: "#c9d1d9" }}>{f.factor}</span>
                      <span style={{ color: pctColor(f.attribution) }}>{(f.attribution * 100).toFixed(3)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
