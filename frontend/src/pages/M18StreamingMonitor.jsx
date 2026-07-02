import { useState, useEffect, useRef } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 18, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  grid4: { display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginBottom: 20 },
  card: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "14px 18px" },
  label: { fontSize: 11, color: "#8b949e", textTransform: "uppercase", marginBottom: 4 },
  val: { fontSize: 18, fontWeight: 700, color: "#f0f6fc" },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 18, marginBottom: 14 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#58a6ff", marginBottom: 12 },
  input: { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, padding: "6px 10px", color: "#f0f6fc", fontSize: 12, marginRight: 8, width: 140 },
  btn: (c="#58a6ff") => ({ background: c + "22", border: `1px solid ${c}55`, borderRadius: 6, padding: "6px 14px", color: c, fontSize: 12, cursor: "pointer", fontFamily: "monospace" }),
  row: { display: "flex", alignItems: "center", gap: 8, marginBottom: 14 },
  log: { background: "#010409", borderRadius: 6, padding: 12, maxHeight: 220, overflowY: "auto", fontSize: 11, color: "#7ee787", lineHeight: 1.8 },
  badge: (c) => ({ display: "inline-block", fontSize: 10, padding: "1px 6px", borderRadius: 4, background: c + "22", color: c, fontWeight: 700, marginRight: 4 }),
};

const EVENT_TYPES = ["TICK","QUOTE","TRADE","ORDER_BOOK","NEWS","ECONOMIC","CORPORATE_ACTION","ALERT","PORTFOLIO","RISK","EXECUTION"];
const TYPE_COLORS = { TICK:"#58a6ff", QUOTE:"#3fb950", TRADE:"#e3b341", NEWS:"#a371f7", RISK:"#ff7b72", ALERT:"#ffa657", ECONOMIC:"#79c0ff" };

export default function M18StreamingMonitor() {
  const [metrics, setMetrics] = useState(null);
  const [log, setLog] = useState([]);
  const [ticker, setTicker] = useState("AAPL");
  const [price, setPrice] = useState("175.50");
  const [volume, setVolume] = useState("1000");
  const [history, setHistory] = useState([]);
  const [selType, setSelType] = useState("TICK");
  const logRef = useRef(null);

  const refresh = () => {
    fetch("/m18/streaming/metrics").then(r => r.json()).then(setMetrics).catch(() => {});
    fetch(`/m18/streaming/history/${selType}?limit=20`).then(r => r.json()).then(setHistory).catch(() => {});
  };

  useEffect(() => { refresh(); const t = setInterval(refresh, 3000); return () => clearInterval(t); }, [selType]);

  useEffect(() => { if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight; }, [log]);

  const publishTick = async () => {
    const r = await fetch("/m18/streaming/publish/tick", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticker, price: parseFloat(price), volume: parseFloat(volume), venue: "NYSE" }),
    });
    const d = await r.json();
    setLog(l => [...l, `[TICK] ${ticker} @ $${price} vol=${volume} → seq#${d.sequence}`]);
    refresh();
  };

  const publishNews = async () => {
    const r = await fetch("/m18/streaming/publish/news", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticker, headline: `${ticker} reports strong quarterly results`, source: "Reuters", sentiment_score: 0.45 }),
    });
    const d = await r.json();
    setLog(l => [...l, `[NEWS] ${ticker} positive headline → seq#${d.sequence}`]);
    refresh();
  };

  const resetMetrics = async () => {
    await fetch("/m18/streaming/reset-metrics", { method: "POST" });
    setLog(l => [...l, "[SYSTEM] Metrics reset"]);
    refresh();
  };

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Streaming Engine Monitor</div>

      <div style={S.grid4}>
        {[
          { label: "Total Published", val: metrics?.total_published ?? "—" },
          { label: "Sequence #", val: metrics?.sequence ?? "—" },
          { label: "Subscribers", val: metrics?.subscribers ?? "—" },
          { label: "Event Types", val: Object.keys(metrics?.by_type ?? {}).length || "—" },
        ].map(k => (
          <div key={k.label} style={S.card}>
            <div style={S.label}>{k.label}</div>
            <div style={S.val}>{k.val}</div>
          </div>
        ))}
      </div>

      {metrics?.by_type && (
        <div style={S.section}>
          <div style={S.sHdr}>Event Distribution</div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {Object.entries(metrics.by_type).map(([t, c]) => (
              <div key={t} style={{ background: "#161b22", borderRadius: 6, padding: "5px 12px" }}>
                <span style={S.badge(TYPE_COLORS[t] || "#8b949e")}>{t}</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: "#f0f6fc" }}>{c}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={S.section}>
        <div style={S.sHdr}>Publish Events</div>
        <div style={S.row}>
          <input style={S.input} value={ticker} onChange={e => setTicker(e.target.value.toUpperCase())} placeholder="Ticker" />
          <input style={S.input} value={price} onChange={e => setPrice(e.target.value)} placeholder="Price" />
          <input style={S.input} value={volume} onChange={e => setVolume(e.target.value)} placeholder="Volume" />
          <button style={S.btn()} onClick={publishTick}>Publish Tick</button>
          <button style={S.btn("#a371f7")} onClick={publishNews}>Publish News</button>
          <button style={S.btn("#ff7b72")} onClick={resetMetrics}>Reset Metrics</button>
        </div>
        <div style={S.log} ref={logRef}>
          {log.length === 0 ? "Events will appear here…" : log.map((l, i) => <div key={i}>{l}</div>)}
        </div>
      </div>

      <div style={S.section}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
          <div style={S.sHdr}>Event History</div>
          <select style={{ ...S.input, width: 160 }} value={selType} onChange={e => setSelType(e.target.value)}>
            {EVENT_TYPES.map(t => <option key={t}>{t}</option>)}
          </select>
        </div>
        {history.length === 0 ? (
          <div style={{ color: "#8b949e", fontSize: 12 }}>No {selType} events recorded yet.</div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
            <thead>
              <tr>{["Seq#","Event ID","Ticker","Timestamp"].map(h => (
                <th key={h} style={{ color: "#8b949e", textAlign: "left", padding: "4px 8px", borderBottom: "1px solid #21262d" }}>{h}</th>
              ))}</tr>
            </thead>
            <tbody>
              {history.map(e => (
                <tr key={e.sequence}>
                  <td style={{ padding: "5px 8px", color: "#58a6ff" }}>{e.sequence}</td>
                  <td style={{ padding: "5px 8px", color: "#8b949e" }}>{e.event_id?.slice(0,8)}…</td>
                  <td style={{ padding: "5px 8px", color: "#f0f6fc" }}>{e.ticker || "—"}</td>
                  <td style={{ padding: "5px 8px", color: "#8b949e" }}>{e.timestamp?.slice(11,19)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
