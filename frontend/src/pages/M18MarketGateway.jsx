import { useState, useEffect } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 18, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  grid4: { display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginBottom: 20 },
  card: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "14px 18px" },
  label: { fontSize: 11, color: "#8b949e", textTransform: "uppercase", marginBottom: 4 },
  val: { fontSize: 18, fontWeight: 700, color: "#f0f6fc" },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 18, marginBottom: 14 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#3fb950", marginBottom: 12 },
  input: { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, padding: "6px 10px", color: "#f0f6fc", fontSize: 12, marginRight: 8 },
  btn: (c="#3fb950") => ({ background: c + "22", border: `1px solid ${c}55`, borderRadius: 6, padding: "6px 14px", color: c, fontSize: 12, cursor: "pointer", fontFamily: "monospace" }),
  badge: (ok) => ({ display: "inline-block", fontSize: 10, padding: "1px 6px", borderRadius: 4, background: ok ? "#3fb95022" : "#ff7b7222", color: ok ? "#3fb950" : "#ff7b72", fontWeight: 700 }),
  table: { width: "100%", borderCollapse: "collapse", fontSize: 11 },
  th: { color: "#8b949e", textAlign: "left", padding: "4px 8px", borderBottom: "1px solid #21262d" },
  td: { padding: "5px 8px", color: "#c9d1d9", borderBottom: "1px solid #161b22" },
};

export default function M18MarketGateway() {
  const [summary, setSummary] = useState(null);
  const [quotes, setQuotes] = useState({});
  const [ticker, setTicker] = useState("AAPL");
  const [bid, setBid] = useState("175.40");
  const [ask, setAsk] = useState("175.42");
  const [venue, setVenue] = useState("NYSE");
  const [msg, setMsg] = useState("");

  const refresh = () => {
    fetch("/m18/gateway/summary").then(r => r.json()).then(setSummary).catch(() => {});
    fetch("/m18/gateway/quotes").then(r => r.json()).then(setQuotes).catch(() => {});
  };
  useEffect(() => { refresh(); const t = setInterval(refresh, 4000); return () => clearInterval(t); }, []);

  const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  const setQuote = async () => {
    const r = await post("/m18/gateway/quote/set", { ticker, bid: parseFloat(bid), ask: parseFloat(ask), bid_size: 100, ask_size: 100, venue });
    if (r.ok) { setMsg(`Quote set: ${ticker} bid=${bid} ask=${ask} @${venue}`); refresh(); }
    else { const d = await r.json(); setMsg(d.detail); }
  };

  const ingestTick = async () => {
    const r = await post("/m18/gateway/tick/ingest", { ticker, price: parseFloat(bid), volume: 1000, venue });
    if (r.ok) { setMsg(`Tick ingested: ${ticker} @ ${bid}`); }
    else { const d = await r.json(); setMsg(d.detail); }
  };

  const venueList = summary?.venues || [];

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Market Data Gateway</div>

      <div style={S.grid4}>
        {[
          { label: "Total Venues", val: summary?.total_venues ?? "—" },
          { label: "Connected", val: summary?.connected_venues ?? "—" },
          { label: "Active Quotes", val: Object.keys(quotes).length },
          { label: "Status", val: summary ? (summary.connected_venues > 0 ? "LIVE" : "DISCONNECTED") : "—" },
        ].map(k => <div key={k.label} style={S.card}><div style={S.label}>{k.label}</div><div style={S.val}>{k.val}</div></div>)}
      </div>

      <div style={S.section}>
        <div style={S.sHdr}>Inject Quote / Tick</div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
          <input style={S.input} value={ticker} onChange={e => setTicker(e.target.value.toUpperCase())} placeholder="Ticker" style={{ ...S.input, width: 80 }} />
          <input style={S.input} value={bid} onChange={e => setBid(e.target.value)} placeholder="Bid" style={{ ...S.input, width: 90 }} />
          <input style={S.input} value={ask} onChange={e => setAsk(e.target.value)} placeholder="Ask" style={{ ...S.input, width: 90 }} />
          <input style={S.input} value={venue} onChange={e => setVenue(e.target.value.toUpperCase())} placeholder="Venue" style={{ ...S.input, width: 120 }} />
          <button style={S.btn()} onClick={setQuote}>Set Quote</button>
          <button style={S.btn("#58a6ff")} onClick={ingestTick}>Ingest Tick</button>
        </div>
        {msg && <div style={{ fontSize: 12, color: "#8b949e" }}>{msg}</div>}
      </div>

      <div style={S.section}>
        <div style={S.sHdr}>Live Quotes</div>
        {Object.keys(quotes).length === 0 ? (
          <div style={{ color: "#8b949e", fontSize: 12 }}>No quotes available. Inject quotes above.</div>
        ) : (
          <table style={S.table}>
            <thead><tr>{["Ticker","Bid","Ask","Spread bps","Mid","Venue"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr></thead>
            <tbody>
              {Object.values(quotes).map(q => (
                <tr key={q.ticker}>
                  <td style={{ ...S.td, color: "#58a6ff" }}>{q.ticker}</td>
                  <td style={{ ...S.td, color: "#3fb950" }}>{q.bid?.toFixed(4)}</td>
                  <td style={{ ...S.td, color: "#ff7b72" }}>{q.ask?.toFixed(4)}</td>
                  <td style={S.td}>{q.spread_bps?.toFixed(2)}</td>
                  <td style={S.td}>{q.mid?.toFixed(4)}</td>
                  <td style={S.td}>{q.venue}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div style={S.section}>
        <div style={S.sHdr}>Venue Status</div>
        {venueList.length === 0 ? <div style={{ color: "#8b949e", fontSize: 12 }}>No venues registered.</div> : (
          <table style={S.table}>
            <thead><tr>{["Venue","Asset Class","Connected","Latency ms"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr></thead>
            <tbody>
              {venueList.map(v => (
                <tr key={v.venue}>
                  <td style={{ ...S.td, color: "#f0f6fc" }}>{v.venue}</td>
                  <td style={S.td}>{v.asset_class}</td>
                  <td style={S.td}><span style={S.badge(v.connected)}>{v.connected ? "YES" : "NO"}</span></td>
                  <td style={S.td}>{v.latency_ms?.toFixed(2) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
