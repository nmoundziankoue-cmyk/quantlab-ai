import { useState } from "react";
import { formatApiError } from "../utils/formatApiError";

const S = {
  wrap: { padding: 24, fontFamily: "monospace", maxWidth: 480 },
  hdr: { fontSize: 20, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  card: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 24 },
  field: { marginBottom: 14 },
  label: { fontSize: 11, color: "#8b949e", display: "block", marginBottom: 4, textTransform: "uppercase" },
  input: { width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 4, color: "#f0f6fc", padding: "8px 10px", fontSize: 14, boxSizing: "border-box" },
  select: { width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 4, color: "#f0f6fc", padding: "8px 10px", fontSize: 14, boxSizing: "border-box" },
  btnRow: { display: "flex", gap: 10, marginTop: 20 },
  buy: { flex: 1, background: "#1a6b3c", color: "#3fb950", border: "2px solid #3fb950", borderRadius: 6, padding: 12, cursor: "pointer", fontSize: 14, fontWeight: 700 },
  sell: { flex: 1, background: "#6b1a1a", color: "#ff7b72", border: "2px solid #ff7b72", borderRadius: 6, padding: 12, cursor: "pointer", fontSize: 14, fontWeight: 700 },
  result: { marginTop: 20, background: "#161b22", borderRadius: 6, padding: 14 },
  ok: { color: "#3fb950", fontSize: 13, marginBottom: 8 },
  err: { color: "#ff7b72", fontSize: 13 },
  row: { display: "flex", justifyContent: "space-between", fontSize: 12, padding: "3px 0", color: "#c9d1d9", borderBottom: "1px solid #21262d" },
};

export default function M17OrderTicket() {
  const [form, setForm] = useState({ ticker: "AAPL", order_type: "MARKET", quantity: 100, limit_price: "", stop_price: "" });
  const [result, setResult] = useState(null);
  const [err, setErr] = useState(null);

  const place = async (side) => {
    setResult(null); setErr(null);
    const body = { ticker: form.ticker, order_type: form.order_type, side, quantity: Number(form.quantity) };
    if (form.limit_price) body.limit_price = Number(form.limit_price);
    if (form.stop_price) body.stop_price = Number(form.stop_price);
    const r = await fetch("/trading/orders/submit", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(body) });
    if (r.ok) setResult(await r.json());
    else { const d = await r.json(); setErr(formatApiError(d.detail, "Submission failed")); }
  };

  const f = (k, v) => setForm(p => ({ ...p, [k]: v }));

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Order Ticket</div>
      <div style={S.card}>
        <div style={S.field}>
          <label style={S.label}>Ticker</label>
          <input style={S.input} value={form.ticker} onChange={e => f("ticker", e.target.value.toUpperCase())} />
        </div>
        <div style={S.field}>
          <label style={S.label}>Order Type</label>
          <select style={S.select} value={form.order_type} onChange={e => f("order_type", e.target.value)}>
            {["MARKET","LIMIT","STOP","STOP_LIMIT","IOC","FOK","GTC"].map(t => <option key={t}>{t}</option>)}
          </select>
        </div>
        <div style={S.field}>
          <label style={S.label}>Quantity</label>
          <input style={S.input} type="number" min="1" value={form.quantity} onChange={e => f("quantity", e.target.value)} />
        </div>
        {["LIMIT","STOP_LIMIT","IOC","FOK"].includes(form.order_type) && (
          <div style={S.field}>
            <label style={S.label}>Limit Price</label>
            <input style={S.input} type="number" step="0.01" value={form.limit_price} onChange={e => f("limit_price", e.target.value)} placeholder="e.g. 175.50" />
          </div>
        )}
        {["STOP","STOP_LIMIT"].includes(form.order_type) && (
          <div style={S.field}>
            <label style={S.label}>Stop Price</label>
            <input style={S.input} type="number" step="0.01" value={form.stop_price} onChange={e => f("stop_price", e.target.value)} placeholder="e.g. 170.00" />
          </div>
        )}
        <div style={S.btnRow}>
          <button style={S.buy} onClick={() => place("BUY")}>BUY</button>
          <button style={S.sell} onClick={() => place("SELL")}>SELL</button>
        </div>
        {err && <div style={{ ...S.result }}><div style={S.err}>{err}</div></div>}
        {result && (
          <div style={S.result}>
            <div style={S.ok}>Order Submitted</div>
            {[["Order ID", result.order_id?.slice(0,8)], ["Status", result.status], ["Type", result.order_type], ["Side", result.side], ["Qty", result.quantity]].map(([k,v]) => (
              <div key={k} style={S.row}><span style={{color:"#8b949e"}}>{k}</span><span>{v}</span></div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
