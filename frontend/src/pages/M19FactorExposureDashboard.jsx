import { useState } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 20, fontWeight: 700, color: "#f0f6fc", marginBottom: 4 },
  sub: { fontSize: 12, color: "#8b949e", marginBottom: 24 },
  grid2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 },
  grid3: { display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sHdr: { fontSize: 14, fontWeight: 700, color: "#a371f7", marginBottom: 12 },
  label: { fontSize: 11, color: "#8b949e", marginBottom: 4, display: "block" },
  input: { width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", padding: "6px 10px", fontSize: 13, boxSizing: "border-box" },
  textarea: { width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", padding: "6px 10px", fontSize: 11, boxSizing: "border-box", height: 80, resize: "vertical" },
  btn: { background: "#238636", color: "#fff", border: "none", borderRadius: 6, padding: "8px 18px", fontSize: 13, cursor: "pointer", fontWeight: 600, marginTop: 8 },
  card: { background: "#161b22", borderRadius: 6, padding: "10px 14px" },
  cardLabel: { fontSize: 10, color: "#8b949e", textTransform: "uppercase" },
  cardVal: { fontSize: 14, fontWeight: 700, color: "#f0f6fc", marginTop: 2 },
  err: { color: "#ff7b72", fontSize: 12, marginTop: 8 },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 11 },
  th: { background: "#161b22", padding: "6px 10px", textAlign: "left", color: "#8b949e" },
  td: { padding: "5px 10px", borderBottom: "1px solid #21262d", color: "#f0f6fc" },
  row: { display: "flex", gap: 12, marginBottom: 12 },
};

const FACTORS = ["MARKET", "SIZE", "VALUE", "MOMENTUM", "QUALITY", "LOW_VOL"];

const DEFAULT_FACTOR_RETURNS = `{"MARKET": [0.01, -0.005, 0.012, 0.003, -0.008, 0.015, 0.002, -0.005, 0.009, 0.001, -0.003, 0.007, 0.004, -0.002, 0.006, 0.008, -0.001, 0.011, -0.004, 0.003, 0.005, -0.002, 0.008, 0.001, -0.003], "SIZE": [0.005, 0.002, -0.001, 0.007, 0.003, -0.002, 0.004, 0.001, -0.003, 0.006, 0.002, -0.001, 0.005, 0.003, -0.002, 0.004, 0.001, -0.003, 0.007, 0.002, -0.001, 0.005, 0.003, -0.002, 0.004]}`;
const DEFAULT_SEC_RETURNS = `{"2024-01-01": 0.012, "2024-01-02": -0.003, "2024-01-03": 0.015, "2024-01-04": 0.001, "2024-01-05": -0.005, "2024-01-06": 0.018, "2024-01-07": 0.003, "2024-01-08": -0.002, "2024-01-09": 0.010, "2024-01-10": 0.002, "2024-01-11": -0.001, "2024-01-12": 0.008, "2024-01-13": 0.005, "2024-01-14": -0.003, "2024-01-15": 0.009, "2024-01-16": 0.011, "2024-01-17": -0.002, "2024-01-18": 0.013, "2024-01-19": -0.004, "2024-01-20": 0.004, "2024-01-21": 0.006, "2024-01-22": -0.001, "2024-01-23": 0.010, "2024-01-24": 0.002, "2024-01-25": -0.002}`;

export default function M19FactorExposureDashboard() {
  const [ticker, setTicker] = useState("AAPL");
  const [factorRetsText, setFactorRetsText] = useState(DEFAULT_FACTOR_RETURNS);
  const [secRetsText, setSecRetsText] = useState(DEFAULT_SEC_RETURNS);
  const [selectedFactors, setSelectedFactors] = useState(["MARKET", "SIZE"]);
  const [exposure, setExposure] = useState(null);
  const [corrs, setCorrs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const toggleFactor = (f) => {
    setSelectedFactors(prev => prev.includes(f) ? prev.filter(x => x !== f) : [...prev, f]);
  };

  const loadData = async () => {
    setLoading(true); setErr("");
    try {
      let factorRets = JSON.parse(factorRetsText);
      const dates = Object.values(factorRets)[0]?.map((_, i) => `2024-01-${String(i + 1).padStart(2, "0")}`) || [];
      const factorReturns = [];
      for (const [fac, vals] of Object.entries(factorRets)) {
        vals.forEach((v, i) => factorReturns.push({ date: dates[i], factor: fac, return_value: v }));
      }
      await fetch("/quant/factors/returns", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ factor_returns: factorReturns }),
      });

      const secRets = JSON.parse(secRetsText);
      const regR = await fetch("/quant/factors/regress", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker, security_returns: secRets, factors: selectedFactors }),
      });
      const exp = await regR.json();
      if (!regR.ok) { setErr(JSON.stringify(exp)); return; }
      setExposure(exp);

      const cR = await fetch("/quant/factors/correlations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ factors: selectedFactors }),
      });
      if (cR.ok) setCorrs(await cR.json());
    } catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Factor Exposure Dashboard</div>
      <div style={S.sub}>Multi-factor OLS regression: alpha, betas, t-stats, p-values, R², information ratio.</div>

      <div style={S.section}>
        <div style={S.sHdr}>Input Data</div>
        <div style={S.row}>
          <div style={{ flex: 1 }}>
            <label style={S.label}>Ticker</label>
            <input style={S.input} value={ticker} onChange={e => setTicker(e.target.value)} />
          </div>
        </div>
        <div>
          <label style={S.label}>Factor Returns JSON {"{ \"MARKET\": [r1, r2, ...], \"SIZE\": [...] }"}</label>
          <textarea style={S.textarea} value={factorRetsText} onChange={e => setFactorRetsText(e.target.value)} />
        </div>
        <div style={{ marginTop: 8 }}>
          <label style={S.label}>Security Returns JSON {"{ \"YYYY-MM-DD\": return, ... }"}</label>
          <textarea style={S.textarea} value={secRetsText} onChange={e => setSecRetsText(e.target.value)} />
        </div>
        <div style={{ marginTop: 8 }}>
          <label style={S.label}>Factors to Regress</label>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 4 }}>
            {FACTORS.map(f => (
              <button key={f} onClick={() => toggleFactor(f)} style={{
                padding: "3px 10px", fontSize: 11, borderRadius: 4, cursor: "pointer",
                background: selectedFactors.includes(f) ? "#1f6feb" : "#161b22",
                border: selectedFactors.includes(f) ? "1px solid #58a6ff" : "1px solid #30363d",
                color: "#f0f6fc",
              }}>{f}</button>
            ))}
          </div>
        </div>
        <button style={S.btn} onClick={loadData} disabled={loading}>{loading ? "Regressing…" : "Run Regression"}</button>
        {err && <div style={S.err}>{err}</div>}
      </div>

      {exposure && (
        <div style={S.section}>
          <div style={S.sHdr}>Factor Exposure — {exposure.ticker}</div>
          <div style={S.grid3}>
            {[
              ["Alpha (Ann.)", `${(exposure.alpha * 100).toFixed(3)}%`],
              ["R²", exposure.r_squared?.toFixed(4)],
              ["Tracking Error", `${(exposure.tracking_error * 100).toFixed(3)}%`],
              ["Info Ratio", exposure.information_ratio?.toFixed(3)],
              ["Adj R²", exposure.adj_r_squared?.toFixed(4)],
            ].map(([l, v]) => (
              <div key={l} style={S.card}>
                <div style={S.cardLabel}>{l}</div>
                <div style={S.cardVal}>{v}</div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 12 }}>
            <table style={S.table}>
              <thead>
                <tr>{["Factor", "Beta", "T-Stat", "P-Value"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr>
              </thead>
              <tbody>
                {Object.entries(exposure.betas || {}).map(([fac, beta]) => (
                  <tr key={fac}>
                    <td style={S.td}>{fac}</td>
                    <td style={S.td}>{beta?.toFixed(4)}</td>
                    <td style={S.td}>{exposure.t_stats?.[fac]?.toFixed(3)}</td>
                    <td style={S.td} style={{ ...S.td, color: (exposure.p_values?.[fac] || 1) < 0.05 ? "#3fb950" : "#8b949e" }}>
                      {exposure.p_values?.[fac]?.toFixed(4)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {corrs.length > 0 && (
        <div style={S.section}>
          <div style={S.sHdr}>Factor Correlations</div>
          <table style={S.table}>
            <thead><tr>{["Factor A", "Factor B", "Correlation", "N"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr></thead>
            <tbody>
              {corrs.map((c, i) => (
                <tr key={i}>
                  <td style={S.td}>{c.factor_a}</td>
                  <td style={S.td}>{c.factor_b}</td>
                  <td style={S.td} style={{ ...S.td, color: Math.abs(c.correlation) > 0.7 ? "#ff7b72" : "#3fb950" }}>
                    {c.correlation?.toFixed(4)}
                  </td>
                  <td style={S.td}>{c.num_observations}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
