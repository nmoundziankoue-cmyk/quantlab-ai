import { useState } from "react";
import { formatApiError } from "../utils/formatApiError";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 20, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  row: { display: "flex", gap: 16 },
  card: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#58a6ff", marginBottom: 14 },
  field: { marginBottom: 10 },
  label: { fontSize: 11, color: "#8b949e", display: "block", marginBottom: 4, textTransform: "uppercase" },
  input: { width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 4, color: "#f0f6fc", padding: "6px 10px", fontSize: 13, boxSizing: "border-box" },
  select: { width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 4, color: "#f0f6fc", padding: "6px 10px", fontSize: 13, boxSizing: "border-box" },
  btn: { background: "#1f6feb", color: "#fff", border: "none", borderRadius: 6, padding: "7px 16px", cursor: "pointer", fontSize: 12, fontWeight: 700 },
  table: { width: "100%", borderCollapse: "collapse" },
  th: { fontSize: 11, color: "#8b949e", textAlign: "left", borderBottom: "1px solid #21262d", padding: "4px 8px" },
  td: { fontSize: 12, color: "#c9d1d9", padding: "6px 8px", borderBottom: "1px solid #161b22" },
  kv: { display:"flex", justifyContent:"space-between", fontSize:12, padding:"4px 0", borderBottom:"1px solid #21262d" },
  err: { color: "#ff7b72", fontSize: 12, marginTop: 8 },
};

const SAMPLE_HOLDINGS = [
  { ticker:"AAPL", portfolio_weight:0.25, benchmark_weight:0.20, portfolio_return:0.08, benchmark_return:0.05, sector:"Technology" },
  { ticker:"MSFT", portfolio_weight:0.20, benchmark_weight:0.18, portfolio_return:0.12, benchmark_return:0.07, sector:"Technology" },
  { ticker:"JPM",  portfolio_weight:0.15, benchmark_weight:0.10, portfolio_return:0.03, benchmark_return:0.04, sector:"Financials" },
  { ticker:"XOM",  portfolio_weight:0.10, benchmark_weight:0.08, portfolio_return:-0.02, benchmark_return:0.01, sector:"Energy" },
];

export default function M17PerformanceAttribution() {
  const [holdings, setHoldings] = useState(JSON.stringify(SAMPLE_HOLDINGS, null, 2));
  const [model, setModel] = useState("BRINSON");
  const [result, setResult] = useState(null);
  const [fullReport, setFullReport] = useState(null);
  const [factorForm, setFactorForm] = useState({ portfolio_return:0.065, benchmark_return:0.045, factor_exposures:'[{"factor_name":"Market","exposure":1.05,"factor_return":0.04},{"factor_name":"Momentum","exposure":0.3,"factor_return":0.02}]' });
  const [factorResult, setFactorResult] = useState(null);
  const [err, setErr] = useState(null);

  const runBrinson = async () => {
    setErr(null); setResult(null);
    try {
      const h = JSON.parse(holdings);
      const r = await fetch("/trading/attribution/brinson", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ holdings: h, model }) });
      if (r.ok) setResult(await r.json());
      else { const d = await r.json(); setErr(formatApiError(d.detail)); }
    } catch { setErr("Invalid JSON"); }
  };

  const runFullReport = async () => {
    setErr(null); setFullReport(null);
    try {
      const h = JSON.parse(holdings);
      const r = await fetch("/trading/attribution/full-report", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ holdings: h, model }) });
      if (r.ok) setFullReport(await r.json());
      else { const d = await r.json(); setErr(formatApiError(d.detail)); }
    } catch { setErr("Invalid JSON"); }
  };

  const runFactor = async () => {
    setErr(null); setFactorResult(null);
    try {
      const fe = JSON.parse(factorForm.factor_exposures);
      const r = await fetch("/trading/attribution/factor", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ portfolio_return:Number(factorForm.portfolio_return), benchmark_return:Number(factorForm.benchmark_return), factor_exposures:fe }) });
      if (r.ok) setFactorResult(await r.json());
      else { const d = await r.json(); setErr(formatApiError(d.detail)); }
    } catch { setErr("Invalid factor JSON"); }
  };

  const pct = v => v != null ? `${(v*100).toFixed(2)}%` : "—";

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Performance Attribution Engine</div>

      <div style={S.row}>
        <div style={{ flex:"0 0 380px" }}>
          <div style={S.card}>
            <div style={S.sHdr}>Brinson-Hood-Beebower Attribution</div>
            <div style={S.field}><label style={S.label}>Model</label>
              <select style={S.select} value={model} onChange={e=>setModel(e.target.value)}>
                <option value="BRINSON">BRINSON (BHB)</option>
                <option value="BRINSON_FACHLER">BRINSON_FACHLER</option>
              </select>
            </div>
            <div style={S.field}><label style={S.label}>Holdings (JSON array)</label>
              <textarea style={{ ...S.input, height:200, fontFamily:"monospace", fontSize:11, resize:"vertical" }} value={holdings} onChange={e=>setHoldings(e.target.value)} />
            </div>
            <div style={{ display:"flex", gap:8 }}>
              <button style={S.btn} onClick={runBrinson}>Run Brinson</button>
              <button style={{ ...S.btn, background:"#21262d" }} onClick={runFullReport}>Full Report</button>
            </div>
            {err && <div style={S.err}>{err}</div>}
          </div>

          <div style={S.card}>
            <div style={S.sHdr}>Factor Attribution</div>
            {[["portfolio_return","Portfolio Return"],["benchmark_return","Benchmark Return"]].map(([k,l])=>(
              <div key={k} style={S.field}><label style={S.label}>{l}</label><input style={S.input} type="number" step="0.001" value={factorForm[k]} onChange={e=>setFactorForm(p=>({...p,[k]:e.target.value}))} /></div>
            ))}
            <div style={S.field}><label style={S.label}>Factor Exposures (JSON)</label>
              <textarea style={{ ...S.input, height:80, fontFamily:"monospace", fontSize:11, resize:"vertical" }} value={factorForm.factor_exposures} onChange={e=>setFactorForm(p=>({...p,factor_exposures:e.target.value}))} />
            </div>
            <button style={S.btn} onClick={runFactor}>Run Factor</button>
            {factorResult && (
              <div style={{ marginTop:10 }}>
                {[["Active Return",pct(factorResult.active_return)],["Factor Return",pct(factorResult.factor_return)],["Specific Return",pct(factorResult.specific_return)]].map(([l,v])=>(
                  <div key={l} style={S.kv}><span style={{color:"#8b949e"}}>{l}</span><span style={{color:"#f0f6fc"}}>{v}</span></div>
                ))}
                {factorResult.factor_contributions?.map(f=>(
                  <div key={f.factor_name} style={S.kv}><span style={{color:"#8b949e"}}>{f.factor_name}</span><span style={{color:"#58a6ff"}}>{pct(f.contribution)}</span></div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div style={{ flex:1 }}>
          {result && (
            <div style={S.card}>
              <div style={S.sHdr}>Brinson Results — {result.model}</div>
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr 1fr", gap:8, marginBottom:16 }}>
                {[["Allocation",result.total_allocation],["Selection",result.total_selection],["Interaction",result.total_interaction],["Active Return",result.active_return]].map(([l,v])=>(
                  <div key={l} style={{ background:"#161b22", borderRadius:6, padding:12 }}>
                    <div style={{ fontSize:10, color:"#8b949e", textTransform:"uppercase" }}>{l}</div>
                    <div style={{ fontSize:18, fontWeight:700, color:v>=0?"#3fb950":"#ff7b72" }}>{pct(v)}</div>
                  </div>
                ))}
              </div>
              <table style={S.table}>
                <thead><tr>{["Ticker","Sector","Alloc Eff","Sel Eff","Inter","Total"].map(h=><th key={h} style={S.th}>{h}</th>)}</tr></thead>
                <tbody>
                  {result.effects?.map(e=>(
                    <tr key={e.ticker}>
                      <td style={{...S.td,fontWeight:700}}>{e.ticker}</td>
                      <td style={{...S.td,color:"#8b949e"}}>{e.sector}</td>
                      <td style={{...S.td,color:e.allocation>=0?"#3fb950":"#ff7b72"}}>{pct(e.allocation)}</td>
                      <td style={{...S.td,color:e.selection>=0?"#3fb950":"#ff7b72"}}>{pct(e.selection)}</td>
                      <td style={{...S.td,color:e.interaction>=0?"#3fb950":"#ff7b72"}}>{pct(e.interaction)}</td>
                      <td style={{...S.td,color:(e.allocation+e.selection+e.interaction)>=0?"#3fb950":"#ff7b72"}}>{pct(e.allocation+e.selection+e.interaction)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {fullReport && (
            <div style={S.card}>
              <div style={S.sHdr}>Full Attribution Report</div>
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:8 }}>
                {[["Portfolio Return",pct(fullReport.portfolio_return)],["Benchmark Return",pct(fullReport.benchmark_return)],["Active Return",pct(fullReport.active_return)],["Tracking Error",pct(fullReport.tracking_error)],["Info Ratio",fullReport.information_ratio?.toFixed(2)],["Model",fullReport.model]].map(([l,v])=>(
                  <div key={l} style={{ background:"#161b22", borderRadius:6, padding:"10px 12px" }}>
                    <div style={{ fontSize:10, color:"#8b949e", textTransform:"uppercase" }}>{l}</div>
                    <div style={{ fontSize:14, fontWeight:700, color:"#f0f6fc" }}>{v}</div>
                  </div>
                ))}
              </div>
              {fullReport.sector_attribution?.length > 0 && (
                <div style={{ marginTop:14 }}>
                  <div style={{ fontSize:11, color:"#8b949e", marginBottom:8 }}>SECTOR BREAKDOWN</div>
                  <table style={S.table}>
                    <thead><tr>{["Sector","Portfolio Wt","Bench Wt","Active Return"].map(h=><th key={h} style={S.th}>{h}</th>)}</tr></thead>
                    <tbody>{fullReport.sector_attribution.map(s=>(
                      <tr key={s.sector}>
                        <td style={{...S.td,color:"#58a6ff"}}>{s.sector}</td>
                        <td style={S.td}>{pct(s.portfolio_weight)}</td>
                        <td style={S.td}>{pct(s.benchmark_weight)}</td>
                        <td style={{...S.td,color:s.active_return>=0?"#3fb950":"#ff7b72"}}>{pct(s.active_return)}</td>
                      </tr>
                    ))}</tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {!result && !fullReport && (
            <div style={{ ...S.card, display:"flex", alignItems:"center", justifyContent:"center", minHeight:200 }}>
              <div style={{ textAlign:"center", color:"#8b949e" }}>
                <div style={{ fontSize:32, marginBottom:12 }}>◎</div>
                <div>Configure holdings and run attribution analysis</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
