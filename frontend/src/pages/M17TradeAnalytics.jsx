import { useState } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 20, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  row: { display: "flex", gap: 16 },
  card: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#58a6ff", marginBottom: 14 },
  field: { marginBottom: 10 },
  label: { fontSize: 11, color: "#8b949e", display: "block", marginBottom: 4, textTransform: "uppercase" },
  input: { width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 4, color: "#f0f6fc", padding: "6px 10px", fontSize: 13, boxSizing: "border-box" },
  btn: { background: "#1f6feb", color: "#fff", border: "none", borderRadius: 6, padding: "7px 16px", cursor: "pointer", fontSize: 12, fontWeight: 700 },
  grid: { display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12 },
  metric: { background: "#161b22", borderRadius: 6, padding: "12px 14px" },
  mLabel: { fontSize: 10, color: "#8b949e", textTransform: "uppercase", marginBottom: 4 },
  mVal: { fontSize: 18, fontWeight: 700, color: "#f0f6fc" },
  err: { color: "#ff7b72", fontSize: 12, marginTop: 8 },
  ok: { color: "#3fb950", fontSize: 12, marginTop: 8 },
};

const SAMPLE_TRADE = { trade_id: "T001", ticker: "AAPL", side: "BUY", quantity: 100, entry_price: 170.0, exit_price: 185.0, entry_datetime: "2025-01-01T09:30:00Z", exit_datetime: "2025-01-15T16:00:00Z", commission: 2.5, pnl: 1497.5, sector: "TECHNOLOGY" };

export default function M17TradeAnalytics() {
  const [trade, setTrade] = useState(JSON.stringify(SAMPLE_TRADE, null, 2));
  const [stats, setStats] = useState(null);
  const [perfForm, setPerfForm] = useState({ returns: "0.01,0.02,-0.005,0.015,0.008,-0.01,0.02,0.005,0.012,-0.003" });
  const [perf, setPerf] = useState(null);
  const [kellyForm, setKellyForm] = useState({ win_rate: 0.6, avg_win: 500, avg_loss: 300 });
  const [kelly, setKelly] = useState(null);
  const [msg, setMsg] = useState(null);
  const [err, setErr] = useState(null);

  const addTrade = async () => {
    setMsg(null); setErr(null);
    try {
      const body = JSON.parse(trade);
      const r = await fetch("/trading/analytics/trades/add", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body) });
      if (r.ok) { setMsg("Trade added"); loadStats(); }
      else { const d = await r.json(); setErr(d.detail); }
    } catch(e) { setErr("Invalid JSON"); }
  };

  const loadStats = async () => {
    const r = await fetch("/trading/analytics/trades/statistics");
    if (r.ok) setStats(await r.json());
    else { const d = await r.json(); setErr(d.detail); }
  };

  const calcPerf = async () => {
    const returns = perfForm.returns.split(",").map(Number).filter(n => !isNaN(n));
    const r = await fetch("/trading/analytics/portfolio-performance", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ returns, periods_per_year: 252 }) });
    if (r.ok) setPerf(await r.json());
  };

  const calcKelly = async () => {
    const r = await fetch("/trading/analytics/kelly", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ win_rate: Number(kellyForm.win_rate), avg_win: Number(kellyForm.avg_win), avg_loss: Number(kellyForm.avg_loss) }) });
    if (r.ok) setKelly(await r.json());
  };

  const STAT_KEYS = [["total_trades","Trades"],["win_rate","Win Rate",v=>`${(v*100).toFixed(1)}%`],["profit_factor","Profit Factor",v=>v.toFixed(2)],["expectancy","Expectancy",v=>`$${v.toFixed(2)}`],["kelly_fraction","Kelly Fraction",v=>`${(v*100).toFixed(1)}%`],["sharpe_ratio","Sharpe",v=>v.toFixed(2)],["sortino_ratio","Sortino",v=>v.toFixed(2)],["total_pnl","Total P&L",v=>`$${v.toFixed(2)}`],["avg_holding_days","Avg Hold",v=>`${v.toFixed(1)}d`]];

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Trade Analytics Engine</div>

      <div style={S.row}>
        <div style={{ flex:"0 0 360px" }}>
          <div style={S.card}>
            <div style={S.sHdr}>Add Trade Record (JSON)</div>
            <textarea style={{ ...S.input, height:200, fontFamily:"monospace", fontSize:11, resize:"vertical" }} value={trade} onChange={e=>setTrade(e.target.value)} />
            <button style={{ ...S.btn, marginTop:8 }} onClick={addTrade}>Add Trade</button>
            {msg && <div style={S.ok}>{msg}</div>}
            {err && <div style={S.err}>{err}</div>}
          </div>

          <div style={S.card}>
            <div style={S.sHdr}>Portfolio Performance</div>
            <div style={S.field}><label style={S.label}>Daily Returns (comma-separated)</label>
              <input style={S.input} value={perfForm.returns} onChange={e=>setPerfForm(p=>({...p,returns:e.target.value}))} />
            </div>
            <button style={S.btn} onClick={calcPerf}>Compute</button>
            {perf && <div style={{ marginTop:12 }}>
              {[["Sharpe","sharpe_ratio"],["Sortino","sortino_ratio"],["Calmar","calmar_ratio"],["Max DD","max_drawdown",v=>`${(v*100).toFixed(2)}%`],["Ann Return","annualised_return",v=>`${(v*100).toFixed(2)}%`],["Ann Vol","annualised_volatility",v=>`${(v*100).toFixed(2)}%`]].map(([l,k,fmt])=>(
                <div key={k} style={{ display:"flex", justifyContent:"space-between", fontSize:12, padding:"3px 0", borderBottom:"1px solid #21262d" }}>
                  <span style={{color:"#8b949e"}}>{l}</span>
                  <span style={{color:"#f0f6fc"}}>{fmt ? fmt(perf[k]) : perf[k]?.toFixed(4)}</span>
                </div>
              ))}
            </div>}
          </div>

          <div style={S.card}>
            <div style={S.sHdr}>Kelly Fraction</div>
            {[["win_rate","Win Rate"],["avg_win","Avg Win $"],["avg_loss","Avg Loss $"]].map(([k,l])=>(
              <div key={k} style={S.field}><label style={S.label}>{l}</label>
                <input style={S.input} type="number" step="0.01" value={kellyForm[k]} onChange={e=>setKellyForm(p=>({...p,[k]:e.target.value}))} />
              </div>
            ))}
            <button style={S.btn} onClick={calcKelly}>Compute</button>
            {kelly && <div style={{ marginTop:10, fontSize:20, fontWeight:700, color:"#58a6ff" }}>{(kelly.kelly_fraction*100).toFixed(1)}% of capital</div>}
          </div>
        </div>

        <div style={{ flex:1 }}>
          {stats && (
            <div style={S.card}>
              <div style={{ ...S.sHdr, display:"flex", justifyContent:"space-between" }}>
                Trade Statistics
                <button style={{ ...S.btn, padding:"4px 10px", fontSize:11, background:"#21262d" }} onClick={loadStats}>Refresh</button>
              </div>
              <div style={S.grid}>
                {STAT_KEYS.map(([k,l,fmt])=>(
                  <div key={k} style={S.metric}>
                    <div style={S.mLabel}>{l}</div>
                    <div style={S.mVal}>{fmt ? fmt(stats[k]) : stats[k]}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {!stats && (
            <div style={{ ...S.card, textAlign:"center" }}>
              <button style={{ ...S.btn, marginTop:20 }} onClick={loadStats}>Load Statistics</button>
              <div style={{ color:"#8b949e", fontSize:12, marginTop:12 }}>Add trade records first, then load statistics</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
