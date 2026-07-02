import { useState, useEffect } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 20, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  card: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#58a6ff", marginBottom: 14, display:"flex", justifyContent:"space-between" },
  table: { width: "100%", borderCollapse: "collapse" },
  th: { fontSize: 11, color: "#8b949e", textAlign: "left", borderBottom: "1px solid #21262d", padding: "4px 8px" },
  td: { fontSize: 12, color: "#c9d1d9", padding: "6px 8px", borderBottom: "1px solid #161b22" },
  badge: (c) => ({ display:"inline-block", fontSize:10, padding:"2px 6px", borderRadius:4, background:c+"22", color:c, fontWeight:700 }),
  btn: { background: "#21262d", border: "1px solid #30363d", color: "#c9d1d9", borderRadius: 4, padding: "4px 12px", cursor: "pointer", fontSize: 11 },
  filter: { display:"flex", gap:8, marginBottom:14, alignItems:"center" },
  input: { background:"#161b22", border:"1px solid #30363d", borderRadius:4, color:"#f0f6fc", padding:"4px 8px", fontSize:12, width:120 },
};

const STATUS_COLORS = { WORKING:"#58a6ff", PARTIAL:"#e3b341", FILLED:"#3fb950", CANCELLED:"#8b949e", REJECTED:"#ff7b72", EXPIRED:"#8b949e", AMENDED:"#a371f7" };

export default function M17TradeBlotter() {
  const [orders, setOrders] = useState([]);
  const [filter, setFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

  const load = () =>
    fetch("/trading/orders").then(r => r.json()).then(d => setOrders(d.orders || [])).catch(() => {});

  useEffect(() => { load(); const id = setInterval(load, 5000); return () => clearInterval(id); }, []);

  const visible = orders.filter(o => {
    const tickerMatch = !filter || o.ticker.includes(filter.toUpperCase());
    const statusMatch = statusFilter === "ALL" || o.status === statusFilter;
    return tickerMatch && statusMatch;
  });

  const summary = orders.reduce((acc, o) => {
    acc[o.status] = (acc[o.status] || 0) + 1;
    return acc;
  }, {});

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Trade Blotter</div>

      <div style={{ display:"grid", gridTemplateColumns:"repeat(5,1fr)", gap:12, marginBottom:20 }}>
        {Object.entries(STATUS_COLORS).map(([s,c]) => (
          <div key={s} style={{ background:"#0d1117", border:`1px solid ${c}33`, borderRadius:6, padding:"10px 14px", cursor:"pointer" }}
               onClick={() => setStatusFilter(s === statusFilter ? "ALL" : s)}>
            <div style={{ fontSize:11, color:c, fontWeight:700 }}>{s}</div>
            <div style={{ fontSize:18, fontWeight:700, color:"#f0f6fc" }}>{summary[s] || 0}</div>
          </div>
        ))}
      </div>

      <div style={S.card}>
        <div style={S.sHdr}>
          <span>Orders ({visible.length})</span>
          <button style={S.btn} onClick={load}>Refresh</button>
        </div>
        <div style={S.filter}>
          <input style={S.input} placeholder="Filter ticker..." value={filter} onChange={e => setFilter(e.target.value)} />
          <select style={{ ...S.input, width:120 }} value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
            {["ALL","WORKING","PARTIAL","FILLED","CANCELLED","REJECTED","EXPIRED"].map(s => <option key={s}>{s}</option>)}
          </select>
        </div>
        <table style={S.table}>
          <thead>
            <tr>{["Time","ID","Ticker","Type","Side","Qty","Filled","Avg Price","Status","Strategy"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {visible.slice().reverse().map(o => (
              <tr key={o.order_id}>
                <td style={S.td}>{new Date(o.created_at).toLocaleTimeString()}</td>
                <td style={S.td}>{o.order_id.slice(0,8)}</td>
                <td style={{ ...S.td, fontWeight:700, color:"#f0f6fc" }}>{o.ticker}</td>
                <td style={S.td}>{o.order_type}</td>
                <td style={{ ...S.td, color: o.side.startsWith("BUY") ? "#3fb950" : "#ff7b72" }}>{o.side}</td>
                <td style={S.td}>{o.quantity.toLocaleString()}</td>
                <td style={S.td}>{o.filled_quantity.toLocaleString()}</td>
                <td style={S.td}>{o.avg_fill_price ? `$${o.avg_fill_price.toFixed(2)}` : "—"}</td>
                <td style={S.td}><span style={S.badge(STATUS_COLORS[o.status] || "#8b949e")}>{o.status}</span></td>
                <td style={{ ...S.td, color:"#8b949e" }}>{o.strategy_tag || "—"}</td>
              </tr>
            ))}
            {visible.length === 0 && <tr><td colSpan={10} style={{ ...S.td, textAlign:"center", color:"#8b949e", padding:20 }}>No orders</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
