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
  kv: { display:"flex", justifyContent:"space-between", fontSize:12, padding:"5px 0", borderBottom:"1px solid #21262d" },
  err: { color: "#ff7b72", fontSize: 12, marginTop: 8 },
  ok: { color: "#3fb950", fontSize: 12, marginTop: 8 },
};

const SCORE_COLOR = s => s >= 80 ? "#3fb950" : s >= 60 ? "#e3b341" : "#ff7b72";

export default function M17ExecutionCost() {
  const [recordForm, setRecordForm] = useState({ trade_id:"TCA001", ticker:"AAPL", side:"BUY", quantity:1000, arrival_price:175.0, execution_price:175.35, benchmark_price:175.0, commission:5.0, bid_price:174.98, ask_price:175.02, broker_id:"GS-PRIME", benchmark:"ARRIVAL" });
  const [analyseForm, setAnalyseForm] = useState({ trade_id:"TCA001" });
  const [analysis, setAnalysis] = useState(null);
  const [report, setReport] = useState(null);
  const [msg, setMsg] = useState(null);
  const [err, setErr] = useState(null);

  const recordTrade = async () => {
    setMsg(null); setErr(null);
    const body = { ...recordForm, quantity:Number(recordForm.quantity), arrival_price:Number(recordForm.arrival_price), execution_price:Number(recordForm.execution_price), benchmark_price:Number(recordForm.benchmark_price), commission:Number(recordForm.commission), bid_price:Number(recordForm.bid_price), ask_price:Number(recordForm.ask_price) };
    const r = await fetch("/trading/tca/record", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body) });
    if (r.ok) setMsg("Trade recorded for TCA");
    else { const d = await r.json(); setErr(formatApiError(d.detail)); }
  };

  const analyseTrade = async () => {
    setErr(null); setAnalysis(null);
    const r = await fetch("/trading/tca/analyse", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(analyseForm) });
    if (r.ok) setAnalysis(await r.json());
    else { const d = await r.json(); setErr(formatApiError(d.detail)); }
  };

  const getReport = async () => {
    setErr(null); setReport(null);
    const r = await fetch("/trading/tca/report");
    if (r.ok) setReport(await r.json());
    else { const d = await r.json(); setErr(formatApiError(d.detail)); }
  };

  const bps = v => v != null ? `${v.toFixed(1)} bps` : "—";

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Transaction Cost Analysis (TCA)</div>

      <div style={S.row}>
        <div style={{ flex:"0 0 320px" }}>
          <div style={S.card}>
            <div style={S.sHdr}>Record Trade</div>
            {[
              ["trade_id","Trade ID","text"],["ticker","Ticker","text"],["side","Side","text"],["quantity","Quantity","number"],
              ["arrival_price","Arrival Price","number"],["execution_price","Exec Price","number"],["benchmark_price","Benchmark Price","number"],
              ["commission","Commission $","number"],["bid_price","Bid","number"],["ask_price","Ask","number"],["broker_id","Broker ID","text"],
            ].map(([k,l,t])=>(
              <div key={k} style={S.field}><label style={S.label}>{l}</label><input style={S.input} type={t} step="0.01" value={recordForm[k]} onChange={e=>setRecordForm(p=>({...p,[k]:e.target.value}))} /></div>
            ))}
            <div style={S.field}><label style={S.label}>Benchmark</label>
              <select style={S.select} value={recordForm.benchmark} onChange={e=>setRecordForm(p=>({...p,benchmark:e.target.value}))}>
                {["ARRIVAL","VWAP","TWAP","OPEN","CLOSE","MID"].map(b=><option key={b}>{b}</option>)}
              </select>
            </div>
            <button style={S.btn} onClick={recordTrade}>Record</button>
            {msg && <div style={S.ok}>{msg}</div>}
            {err && <div style={S.err}>{err}</div>}
          </div>

          <div style={S.card}>
            <div style={S.sHdr}>Analyse Trade</div>
            <div style={S.field}><label style={S.label}>Trade ID</label><input style={S.input} value={analyseForm.trade_id} onChange={e=>setAnalyseForm(p=>({...p,trade_id:e.target.value}))} /></div>
            <div style={{ display:"flex", gap:8 }}>
              <button style={S.btn} onClick={analyseTrade}>Analyse</button>
              <button style={{ ...S.btn, background:"#21262d" }} onClick={getReport}>Full Report</button>
            </div>
          </div>
        </div>

        <div style={{ flex:1 }}>
          {analysis && (
            <div style={S.card}>
              <div style={S.sHdr}>Cost Breakdown — {analysis.trade_id}</div>
              <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:8, marginBottom:16 }}>
                {[["Spread Cost",bps(analysis.spread_cost_bps)],["Slippage",bps(analysis.slippage_bps)],["Delay Cost",bps(analysis.delay_cost_bps)],["Opp Cost",bps(analysis.opportunity_cost_bps)],["Commission",bps(analysis.commission_bps)],["Total IS",bps(analysis.implementation_shortfall_bps)]].map(([l,v])=>(
                  <div key={l} style={{ background:"#161b22", borderRadius:6, padding:"10px 12px" }}>
                    <div style={{ fontSize:10, color:"#8b949e", textTransform:"uppercase" }}>{l}</div>
                    <div style={{ fontSize:16, fontWeight:700, color:"#f0f6fc" }}>{v}</div>
                  </div>
                ))}
              </div>
              {[["Arrival Price",`$${analysis.arrival_price?.toFixed(2)}`],["Execution Price",`$${analysis.execution_price?.toFixed(2)}`],["Benchmark",analysis.benchmark],["Broker",analysis.broker_id]].map(([l,v])=>(
                <div key={l} style={S.kv}><span style={{color:"#8b949e"}}>{l}</span><span>{v}</span></div>
              ))}
            </div>
          )}

          {report && (
            <div style={S.card}>
              <div style={S.sHdr}>TCA Report</div>
              <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:8, marginBottom:16 }}>
                {[["Total Trades",report.total_trades],["Avg IS",bps(report.avg_implementation_shortfall_bps)],["Avg Slippage",bps(report.avg_slippage_bps)],["Avg Commission",bps(report.avg_commission_bps)],["Avg Spread",bps(report.avg_spread_cost_bps)],["Period",report.period_start ? report.period_start.slice(0,10) : "—"]].map(([l,v])=>(
                  <div key={l} style={{ background:"#161b22", borderRadius:6, padding:"10px 12px" }}>
                    <div style={{ fontSize:10, color:"#8b949e", textTransform:"uppercase" }}>{l}</div>
                    <div style={{ fontSize:15, fontWeight:700, color:"#f0f6fc" }}>{v}</div>
                  </div>
                ))}
              </div>

              {report.broker_scorecards?.length > 0 && (
                <div>
                  <div style={{ fontSize:11, color:"#8b949e", marginBottom:8 }}>BROKER SCORECARDS</div>
                  <table style={S.table}>
                    <thead><tr>{["Broker","Trades","Avg Slippage","Avg Comm","Fill Rate","Score"].map(h=><th key={h} style={S.th}>{h}</th>)}</tr></thead>
                    <tbody>{report.broker_scorecards.map(b=>(
                      <tr key={b.broker_id}>
                        <td style={{...S.td,fontWeight:700}}>{b.broker_id}</td>
                        <td style={S.td}>{b.total_trades}</td>
                        <td style={S.td}>{bps(b.avg_slippage_bps)}</td>
                        <td style={S.td}>{bps(b.avg_commission_bps)}</td>
                        <td style={S.td}>{(b.avg_fill_rate*100)?.toFixed(1)}%</td>
                        <td style={S.td}><span style={{ color:SCORE_COLOR(b.quality_score), fontWeight:700 }}>{b.quality_score?.toFixed(0)}</span></td>
                      </tr>
                    ))}</tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {!analysis && !report && (
            <div style={{ ...S.card, display:"flex", alignItems:"center", justifyContent:"center", minHeight:200 }}>
              <div style={{ textAlign:"center", color:"#8b949e" }}>
                <div style={{ fontSize:32, marginBottom:12 }}>$</div>
                <div>Record a trade and analyse its costs</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
