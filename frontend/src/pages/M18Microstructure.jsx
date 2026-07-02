import { useState, useEffect } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 18, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 18, marginBottom: 14 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#e3b341", marginBottom: 12 },
  row: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 },
  input: { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, padding: "6px 10px", color: "#f0f6fc", fontSize: 12, marginRight: 8, width: 110 },
  btn: (c="#e3b341") => ({ background: c + "22", border: `1px solid ${c}55`, borderRadius: 6, padding: "6px 14px", color: c, fontSize: 12, cursor: "pointer", fontFamily: "monospace", marginRight: 6 }),
  badge: (ok, c="#3fb950") => ({ display: "inline-block", fontSize: 10, padding: "1px 6px", borderRadius: 4, background: (ok ? c : "#8b949e") + "22", color: ok ? c : "#8b949e", fontWeight: 700 }),
  dataBox: { background: "#161b22", borderRadius: 6, padding: 12, fontSize: 12 },
  kv: { display: "flex", justifyContent: "space-between", padding: "3px 0", borderBottom: "1px solid #21262d33" },
};

export default function M18Microstructure() {
  const [ticker, setTicker] = useState("AAPL");
  const [bid, setBid] = useState("175.40");
  const [ask, setAsk] = useState("175.42");
  const [bSize, setBSize] = useState("500");
  const [aSize, setASize] = useState("400");
  const [tradePrice, setTradePrice] = useState("175.41");
  const [tradeVol, setTradeVol] = useState("200");
  const [level1, setLevel1] = useState(null);
  const [spread, setSpread] = useState(null);
  const [imbalance, setImbalance] = useState(null);
  const [spoofing, setSpoofing] = useState(null);
  const [sweep, setSweep] = useState(null);
  const [vwapBands, setVwapBands] = useState(null);
  const [msg, setMsg] = useState("");

  const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const get = (url) => fetch(url).then(r => r.ok ? r.json() : null);

  const ingestQuote = async () => {
    await post("/m18/microstructure/quote/ingest", { ticker, bid: parseFloat(bid), ask: parseFloat(ask), bid_size: parseFloat(bSize), ask_size: parseFloat(aSize) });
    setMsg(`Quote ingested for ${ticker}`);
    refreshData();
  };

  const ingestTrade = async () => {
    await post("/m18/microstructure/trade/ingest", { ticker, price: parseFloat(tradePrice), volume: parseFloat(tradeVol), aggressor_side: "BUY" });
    setMsg(`Trade ingested for ${ticker}`);
    refreshData();
  };

  const refreshData = async () => {
    const t = ticker.toUpperCase();
    setLevel1(await get(`/m18/microstructure/level1/${t}`));
    setSpread(await get(`/m18/microstructure/spread/${t}`));
    const imb = await get(`/m18/microstructure/imbalance/${t}`);
    setImbalance(imb);
    setSpoofing(await get(`/m18/microstructure/detect/spoofing/${t}`));
    setSweep(await get(`/m18/microstructure/detect/sweep/${t}`));
    setVwapBands(await get(`/m18/microstructure/vwap-bands/${t}`));
  };

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Market Microstructure Engine</div>

      <div style={S.section}>
        <div style={S.sHdr}>Ingest Market Data</div>
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 10 }}>
          <input style={S.input} value={ticker} onChange={e => setTicker(e.target.value.toUpperCase())} placeholder="Ticker" />
          <input style={S.input} value={bid} onChange={e => setBid(e.target.value)} placeholder="Bid" />
          <input style={S.input} value={ask} onChange={e => setAsk(e.target.value)} placeholder="Ask" />
          <input style={S.input} value={bSize} onChange={e => setBSize(e.target.value)} placeholder="Bid Size" />
          <input style={S.input} value={aSize} onChange={e => setASize(e.target.value)} placeholder="Ask Size" />
          <button style={S.btn()} onClick={ingestQuote}>Ingest Quote</button>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input style={S.input} value={tradePrice} onChange={e => setTradePrice(e.target.value)} placeholder="Trade Price" />
          <input style={S.input} value={tradeVol} onChange={e => setTradeVol(e.target.value)} placeholder="Volume" />
          <button style={S.btn("#58a6ff")} onClick={ingestTrade}>Ingest Trade</button>
        </div>
        {msg && <div style={{ marginTop: 8, fontSize: 11, color: "#8b949e" }}>{msg}</div>}
      </div>

      <div style={S.row}>
        <div style={S.section}>
          <div style={S.sHdr}>Level 1 Data</div>
          {!level1 ? <div style={{ color: "#8b949e", fontSize: 12 }}>No data — ingest a quote first.</div> : (
            <div style={S.dataBox}>
              {[["Bid", `$${level1.bid?.toFixed(4)}`], ["Ask", `$${level1.ask?.toFixed(4)}`], ["Bid Size", level1.bid_size], ["Ask Size", level1.ask_size], ["Spread", `$${level1.spread?.toFixed(4)}`], ["Spread bps", level1.spread_bps?.toFixed(2)], ["Mid", `$${level1.mid?.toFixed(4)}`]].map(([k, v]) => (
                <div key={k} style={S.kv}><span style={{ color: "#8b949e" }}>{k}</span><span style={{ color: "#f0f6fc" }}>{v}</span></div>
              ))}
            </div>
          )}
        </div>

        <div style={S.section}>
          <div style={S.sHdr}>Spread Analytics</div>
          {!spread ? <div style={{ color: "#8b949e", fontSize: 12 }}>No spread data yet.</div> : (
            <div style={S.dataBox}>
              {[["Current Spread bps", spread.current_spread_bps?.toFixed(2)], ["Avg Spread bps", spread.avg_spread_bps?.toFixed(2)], ["Min Spread bps", spread.min_spread_bps?.toFixed(2)], ["Max Spread bps", spread.max_spread_bps?.toFixed(2)], ["Effective Spread bps", spread.effective_spread_bps?.toFixed(2)]].map(([k, v]) => (
                <div key={k} style={S.kv}><span style={{ color: "#8b949e" }}>{k}</span><span style={{ color: "#e3b341" }}>{v}</span></div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div style={S.row}>
        <div style={S.section}>
          <div style={S.sHdr}>Manipulation Detection</div>
          {[
            { label: "Spoofing", data: spoofing },
            { label: "Sweep", data: sweep },
          ].map(({ label, data }) => (
            <div key={label} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <span style={{ fontSize: 12, color: "#c9d1d9", width: 100 }}>{label}:</span>
              {!data ? <span style={{ color: "#8b949e", fontSize: 11 }}>No data</span> : (
                <span style={S.badge(data.detected, "#ff7b72")}>{data.detected ? "DETECTED" : "CLEAR"}</span>
              )}
              {data?.confidence && <span style={{ fontSize: 11, color: "#8b949e" }}>conf={data.confidence?.toFixed(2)}</span>}
            </div>
          ))}
          {imbalance && (
            <div style={{ fontSize: 12, color: "#c9d1d9", marginTop: 8 }}>
              Bid/Ask Imbalance: <b style={{ color: imbalance.imbalance > 0 ? "#3fb950" : "#ff7b72" }}>{imbalance.imbalance?.toFixed(4)}</b>
            </div>
          )}
        </div>

        <div style={S.section}>
          <div style={S.sHdr}>VWAP Bands</div>
          {!vwapBands ? <div style={{ color: "#8b949e", fontSize: 12 }}>No VWAP data — ingest trades first.</div> : (
            <div style={S.dataBox}>
              {Object.entries(vwapBands).filter(([k]) => !["ticker"].includes(k)).map(([k, v]) => (
                <div key={k} style={S.kv}><span style={{ color: "#8b949e" }}>{k}</span><span style={{ color: "#79c0ff" }}>{typeof v === "number" ? v.toFixed(4) : String(v)}</span></div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
