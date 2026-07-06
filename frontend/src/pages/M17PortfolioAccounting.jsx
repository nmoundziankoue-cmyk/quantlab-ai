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
  ok: { color: "#3fb950", fontSize: 12, marginTop: 8 },
  err: { color: "#ff7b72", fontSize: 12, marginTop: 8 },
  kv: { display:"flex", justifyContent:"space-between", fontSize:12, padding:"4px 0", borderBottom:"1px solid #21262d" },
};

export default function M17PortfolioAccounting() {
  const [depositForm, setDepositForm] = useState({ amount: 1000000, currency: "USD", description: "Initial deposit" });
  const [withdrawForm, setWithdrawForm] = useState({ amount: 50000, description: "Withdrawal" });
  const [tradeForm, setTradeForm] = useState({ ticker:"AAPL", side:"BUY", quantity:100, price:175, commission:2.5 });
  const [splitForm, setSplitForm] = useState({ ticker:"AAPL", ratio:2.0 });
  const [divForm, setDivForm] = useState({ ticker:"AAPL", amount_per_share:0.25, shares_held:100 });
  const [mtmForm, setMtmForm] = useState({ prices: "AAPL:180,MSFT:425" });
  const [nav, setNav] = useState(null);
  const [snapshot, setSnapshot] = useState(null);
  const [msg, setMsg] = useState(null);
  const [err, setErr] = useState(null);

  const post = async (url, body) => {
    setMsg(null); setErr(null);
    const r = await fetch(url, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body) });
    if (r.ok) { const d = await r.json(); setMsg(d.message || "OK"); }
    else { const d = await r.json(); setErr(formatApiError(d.detail, "Error")); }
  };

  const loadNav = async () => {
    const prices = {};
    mtmForm.prices.split(",").forEach(s => { const [t,v] = s.split(":"); if(t&&v) prices[t.trim().toUpperCase()] = Number(v); });
    const r = await fetch("/trading/accounting/nav", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ prices }) });
    if (r.ok) setNav(await r.json());
  };

  const loadSnapshot = async () => {
    const prices = {};
    mtmForm.prices.split(",").forEach(s => { const [t,v] = s.split(":"); if(t&&v) prices[t.trim().toUpperCase()] = Number(v); });
    const r = await fetch("/trading/accounting/snapshot", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ prices }) });
    if (r.ok) setSnapshot(await r.json());
  };

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Portfolio Accounting Engine</div>

      <div style={S.row}>
        <div style={{ flex:"0 0 300px" }}>
          <div style={S.card}>
            <div style={S.sHdr}>Cash Operations</div>
            <div style={{ borderBottom:"1px solid #21262d", paddingBottom:12, marginBottom:12 }}>
              <div style={{ fontSize:11, color:"#58a6ff", marginBottom:8 }}>Deposit</div>
              {[["amount","Amount"],["currency","Currency"],["description","Description"]].map(([k,l])=>(
                <div key={k} style={S.field}><label style={S.label}>{l}</label><input style={S.input} value={depositForm[k]} onChange={e=>setDepositForm(p=>({...p,[k]:e.target.value}))} /></div>
              ))}
              <button style={S.btn} onClick={() => post("/trading/accounting/deposit", { ...depositForm, amount:Number(depositForm.amount) })}>Deposit</button>
            </div>
            <div style={{ fontSize:11, color:"#58a6ff", marginBottom:8 }}>Withdraw</div>
            {[["amount","Amount"],["description","Description"]].map(([k,l])=>(
              <div key={k} style={S.field}><label style={S.label}>{l}</label><input style={S.input} value={withdrawForm[k]} onChange={e=>setWithdrawForm(p=>({...p,[k]:e.target.value}))} /></div>
            ))}
            <button style={S.btn} onClick={() => post("/trading/accounting/withdraw", { ...withdrawForm, amount:Number(withdrawForm.amount) })}>Withdraw</button>
            {msg && <div style={S.ok}>{msg}</div>}
            {err && <div style={S.err}>{err}</div>}
          </div>

          <div style={S.card}>
            <div style={S.sHdr}>Book Trade</div>
            {[["ticker","Ticker","text"],["side","Side","text"],["quantity","Qty","number"],["price","Price","number"],["commission","Commission","number"]].map(([k,l,t])=>(
              <div key={k} style={S.field}><label style={S.label}>{l}</label><input style={S.input} type={t} value={tradeForm[k]} onChange={e=>setTradeForm(p=>({...p,[k]:e.target.value}))} /></div>
            ))}
            <button style={S.btn} onClick={() => post("/trading/accounting/book-trade", { ...tradeForm, quantity:Number(tradeForm.quantity), price:Number(tradeForm.price), commission:Number(tradeForm.commission) })}>Book Trade</button>
          </div>

          <div style={S.card}>
            <div style={S.sHdr}>Corporate Actions</div>
            <div style={{ borderBottom:"1px solid #21262d", paddingBottom:12, marginBottom:12 }}>
              <div style={{ fontSize:11, color:"#58a6ff", marginBottom:8 }}>Stock Split</div>
              {[["ticker","Ticker"],["ratio","Ratio (e.g. 2 = 2:1)"]].map(([k,l])=>(
                <div key={k} style={S.field}><label style={S.label}>{l}</label><input style={S.input} value={splitForm[k]} onChange={e=>setSplitForm(p=>({...p,[k]:e.target.value}))} /></div>
              ))}
              <button style={S.btn} onClick={() => post("/trading/accounting/split", { ...splitForm, ratio:Number(splitForm.ratio) })}>Apply Split</button>
            </div>
            <div style={{ fontSize:11, color:"#58a6ff", marginBottom:8 }}>Cash Dividend</div>
            {[["ticker","Ticker"],["amount_per_share","$ Per Share"],["shares_held","Shares Held"]].map(([k,l])=>(
              <div key={k} style={S.field}><label style={S.label}>{l}</label><input style={S.input} value={divForm[k]} onChange={e=>setDivForm(p=>({...p,[k]:e.target.value}))} /></div>
            ))}
            <button style={S.btn} onClick={() => post("/trading/accounting/dividend", { ...divForm, amount_per_share:Number(divForm.amount_per_share), shares_held:Number(divForm.shares_held) })}>Apply Dividend</button>
          </div>
        </div>

        <div style={{ flex:1 }}>
          <div style={S.card}>
            <div style={S.sHdr}>Mark to Market / NAV</div>
            <div style={S.field}><label style={S.label}>Prices (ticker:price, comma-sep)</label>
              <input style={S.input} value={mtmForm.prices} onChange={e=>setMtmForm(p=>({...p,prices:e.target.value}))} />
            </div>
            <div style={{ display:"flex", gap:8 }}>
              <button style={S.btn} onClick={loadNav}>Get NAV</button>
              <button style={{ ...S.btn, background:"#21262d" }} onClick={loadSnapshot}>Full Snapshot</button>
            </div>
            {nav && (
              <div style={{ marginTop:12 }}>
                {[["Cash",`$${nav.cash?.toFixed(2)}`],["Equity",`$${nav.equity?.toFixed(2)}`],["NAV",`$${nav.nav?.toFixed(2)}`],["Unrealised P&L",`$${nav.unrealised_pnl?.toFixed(2)}`]].map(([l,v])=>(
                  <div key={l} style={S.kv}><span style={{color:"#8b949e"}}>{l}</span><span style={{color:"#f0f6fc",fontWeight:700}}>{v}</span></div>
                ))}
              </div>
            )}
          </div>

          {snapshot && (
            <div style={S.card}>
              <div style={S.sHdr}>P&L Snapshot</div>
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8 }}>
                {[["Day P&L",snapshot.day_pnl],["Month P&L",snapshot.month_pnl],["Year P&L",snapshot.year_pnl],["Total Realised",snapshot.total_realised_pnl],["Total Commission",snapshot.total_commission],["Total Dividends",snapshot.total_dividends]].map(([l,v])=>(
                  <div key={l} style={S.kv}>
                    <span style={{color:"#8b949e"}}>{l}</span>
                    <span style={{color:v>=0?"#3fb950":"#ff7b72",fontWeight:700}}>${v?.toFixed(2)}</span>
                  </div>
                ))}
              </div>
              {snapshot.positions?.length > 0 && (
                <div style={{ marginTop:16 }}>
                  <div style={{ fontSize:11, color:"#8b949e", marginBottom:8 }}>POSITIONS</div>
                  <table style={S.table}>
                    <thead><tr>{["Ticker","Qty","Cost","Mkt Price","Unreal P&L"].map(h=><th key={h} style={S.th}>{h}</th>)}</tr></thead>
                    <tbody>{snapshot.positions.map(p=>(
                      <tr key={p.ticker}>
                        <td style={{...S.td,fontWeight:700}}>{p.ticker}</td>
                        <td style={S.td}>{p.quantity}</td>
                        <td style={S.td}>${p.avg_cost?.toFixed(2)}</td>
                        <td style={S.td}>${p.market_price?.toFixed(2)}</td>
                        <td style={{...S.td,color:p.unrealised_pnl>=0?"#3fb950":"#ff7b72"}}>${p.unrealised_pnl?.toFixed(2)}</td>
                      </tr>
                    ))}</tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
