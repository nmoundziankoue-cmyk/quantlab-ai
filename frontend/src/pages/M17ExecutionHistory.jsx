import { useState, useEffect } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 20, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  card: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#58a6ff", marginBottom: 14 },
  table: { width: "100%", borderCollapse: "collapse" },
  th: { fontSize: 11, color: "#8b949e", textAlign: "left", borderBottom: "1px solid #21262d", padding: "4px 8px" },
  td: { fontSize: 12, color: "#c9d1d9", padding: "6px 8px", borderBottom: "1px solid #161b22" },
  btn: { background: "#1f6feb", color: "#fff", border: "none", borderRadius: 6, padding: "7px 16px", cursor: "pointer", fontSize: 12, fontWeight: 700 },
  input: { background: "#161b22", border: "1px solid #30363d", borderRadius: 4, color: "#f0f6fc", padding: "6px 10px", fontSize: 13 },
};

const SIDE_COLORS = { BUY:"#3fb950", SELL:"#ff7b72", SELL_SHORT:"#ff7b72", BUY_TO_COVER:"#3fb950" };

export default function M17ExecutionHistory() {
  const [fills, setFills] = useState([]);
  const [closedTrades, setClosedTrades] = useState([]);
  const [tab, setTab] = useState("fills");
  const [filterTicker, setFilterTicker] = useState("");

  const loadFills = async () => {
    const r = await fetch("/trading/paper/fills");
    if (r.ok) { const d = await r.json(); setFills(d.fills || []); }
  };

  const loadClosedTrades = async () => {
    const r = await fetch("/trading/paper/closed-trades");
    if (r.ok) { const d = await r.json(); setClosedTrades(d.trades || []); }
  };

  useEffect(() => { loadFills(); loadClosedTrades(); }, []);

  const filtered = (arr) => filterTicker ? arr.filter(x => x.ticker?.toLowerCase().includes(filterTicker.toLowerCase())) : arr;

  const totalPnL = closedTrades.reduce((sum, t) => sum + (t.realised_pnl || 0), 0);
  const winCount = closedTrades.filter(t => (t.realised_pnl || 0) > 0).length;
  const lossCount = closedTrades.filter(t => (t.realised_pnl || 0) < 0).length;

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Execution History</div>

      <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:10, marginBottom:16 }}>
        {[["Total Fills",fills.length],["Closed Trades",closedTrades.length],["Win/Loss",`${winCount}/${lossCount}`],["Realised P&L",`$${totalPnL.toFixed(2)}`]].map(([l,v])=>(
          <div key={l} style={{ ...S.card, marginBottom:0 }}>
            <div style={{ fontSize:10, color:"#8b949e", textTransform:"uppercase" }}>{l}</div>
            <div style={{ fontSize:18, fontWeight:700, color:l==="Realised P&L"?(totalPnL>=0?"#3fb950":"#ff7b72"):"#f0f6fc" }}>{v}</div>
          </div>
        ))}
      </div>

      <div style={{ display:"flex", gap:8, marginBottom:16, alignItems:"center" }}>
        {["fills","closed"].map(t=>(
          <button key={t} style={{ ...S.btn, background:tab===t?"#1f6feb":"#21262d" }} onClick={()=>setTab(t)}>{t==="fills"?"Fill History":"Closed Trades"}</button>
        ))}
        <input style={{ ...S.input, marginLeft:"auto", width:160 }} placeholder="Filter by ticker" value={filterTicker} onChange={e=>setFilterTicker(e.target.value)} />
        <button style={{ ...S.btn, background:"#21262d", padding:"6px 12px" }} onClick={() => { loadFills(); loadClosedTrades(); }}>↻</button>
      </div>

      {tab === "fills" && (
        <div style={S.card}>
          <div style={S.sHdr}>Fill History ({filtered(fills).length})</div>
          <table style={S.table}>
            <thead><tr>{["Ticker","Side","Qty","Fill Price","Commission","Slippage bps","Status","Time"].map(h=><th key={h} style={S.th}>{h}</th>)}</tr></thead>
            <tbody>
              {filtered(fills).slice().reverse().map((f,i)=>(
                <tr key={i}>
                  <td style={{ ...S.td, fontWeight:700 }}>{f.ticker}</td>
                  <td style={{ ...S.td, color: SIDE_COLORS[f.side] || "#c9d1d9" }}>{f.side}</td>
                  <td style={S.td}>{f.filled_qty}</td>
                  <td style={S.td}>${f.fill_price?.toFixed(4)}</td>
                  <td style={S.td}>${f.commission?.toFixed(2)}</td>
                  <td style={S.td}>{f.slippage_bps?.toFixed(1) ?? "—"}</td>
                  <td style={S.td}><span style={{ color: f.is_filled ? "#3fb950" : "#ff7b72", fontWeight:700 }}>{f.is_filled ? "FILLED" : "REJECTED"}</span></td>
                  <td style={{ ...S.td, color:"#8b949e", fontSize:10 }}>{f.timestamp ? new Date(f.timestamp).toLocaleTimeString() : "—"}</td>
                </tr>
              ))}
              {filtered(fills).length===0 && <tr><td colSpan={8} style={{...S.td,textAlign:"center",color:"#8b949e"}}>No fills</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab === "closed" && (
        <div style={S.card}>
          <div style={S.sHdr}>Closed Trades ({filtered(closedTrades).length})</div>
          <table style={S.table}>
            <thead><tr>{["Ticker","Side","Qty","Entry","Exit","Realised P&L","Commission","Return %","Duration"].map(h=><th key={h} style={S.th}>{h}</th>)}</tr></thead>
            <tbody>
              {filtered(closedTrades).slice().reverse().map((t,i)=>(
                <tr key={i}>
                  <td style={{ ...S.td, fontWeight:700 }}>{t.ticker}</td>
                  <td style={{ ...S.td, color: SIDE_COLORS[t.side] || "#c9d1d9" }}>{t.side}</td>
                  <td style={S.td}>{t.quantity}</td>
                  <td style={S.td}>${t.entry_price?.toFixed(2)}</td>
                  <td style={S.td}>${t.exit_price?.toFixed(2)}</td>
                  <td style={{ ...S.td, color:(t.realised_pnl||0)>=0?"#3fb950":"#ff7b72", fontWeight:700 }}>${(t.realised_pnl||0).toFixed(2)}</td>
                  <td style={S.td}>${t.commission?.toFixed(2)}</td>
                  <td style={{ ...S.td, color:(t.return_pct||0)>=0?"#3fb950":"#ff7b72" }}>{((t.return_pct||0)*100).toFixed(2)}%</td>
                  <td style={{ ...S.td, color:"#8b949e" }}>{t.holding_seconds ? `${(t.holding_seconds/60).toFixed(0)}m` : "—"}</td>
                </tr>
              ))}
              {filtered(closedTrades).length===0 && <tr><td colSpan={9} style={{...S.td,textAlign:"center",color:"#8b949e"}}>No closed trades</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
