import { useState } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 20, fontWeight: 700, color: "#f0f6fc", marginBottom: 4 },
  sub: { fontSize: 12, color: "#8b949e", marginBottom: 24 },
  grid2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 },
  grid4: { display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sHdr: { fontSize: 14, fontWeight: 700, color: "#e3b341", marginBottom: 12 },
  label: { fontSize: 11, color: "#8b949e", marginBottom: 4, display: "block" },
  input: { width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", padding: "6px 10px", fontSize: 13, boxSizing: "border-box" },
  select: { width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", padding: "6px 10px", fontSize: 13 },
  btn: { background: "#238636", color: "#fff", border: "none", borderRadius: 6, padding: "8px 18px", fontSize: 13, cursor: "pointer", fontWeight: 600, marginTop: 8 },
  card: { background: "#161b22", borderRadius: 6, padding: "10px 14px" },
  cardLabel: { fontSize: 10, color: "#8b949e", textTransform: "uppercase" },
  cardVal: { fontSize: 16, fontWeight: 700, color: "#f0f6fc", marginTop: 2 },
  tag: (c) => ({ display: "inline-block", fontSize: 10, padding: "2px 6px", borderRadius: 4, background: c + "22", color: c, fontWeight: 700 }),
  err: { color: "#ff7b72", fontSize: 12, marginTop: 8 },
  pre: { background: "#161b22", borderRadius: 6, padding: 12, fontSize: 11, color: "#c9d1d9", overflowX: "auto" },
};

export default function M19ExecutionSimulator() {
  const [ticker, setTicker] = useState("AAPL");
  const [side, setSide] = useState("BUY");
  const [qty, setQty] = useState("1000");
  const [price, setPrice] = useState("150.0");
  const [orderType, setOrderType] = useState("MARKET");
  const [limitPrice, setLimitPrice] = useState("");
  const [stopPrice, setStopPrice] = useState("");
  const [slipModel, setSlipModel] = useState("FIXED_BPS");
  const [slipBps, setSlipBps] = useState("5");
  const [fill, setFill] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const simulate = async () => {
    setLoading(true); setErr("");
    const order = {
      ticker, side, quantity: parseFloat(qty), order_type: orderType,
      ...(limitPrice ? { limit_price: parseFloat(limitPrice) } : {}),
      ...(stopPrice ? { stop_price: parseFloat(stopPrice) } : {}),
    };
    try {
      const r = await fetch("/quant/execution/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          order,
          market_price: parseFloat(price),
          slippage_model: slipModel,
          fixed_slippage_bps: parseFloat(slipBps),
        }),
      });
      const d = await r.json();
      if (!r.ok) setErr(JSON.stringify(d));
      else setFill(d);
    } catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  };

  const getReport = async () => {
    const r = await fetch("/quant/execution/slippage-report");
    if (r.ok) setReport(await r.json());
  };

  const statusColor = { FILLED: "#3fb950", PARTIAL: "#e3b341", CANCELLED: "#ff7b72", PENDING: "#8b949e", REJECTED: "#ff7b72" };

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Execution Simulator</div>
      <div style={S.sub}>Simulate realistic order fills with slippage, market impact, and commission models.</div>

      <div style={S.section}>
        <div style={S.sHdr}>Order Configuration</div>
        <div style={S.grid2}>
          <div>
            <label style={S.label}>Ticker</label>
            <input style={S.input} value={ticker} onChange={e => setTicker(e.target.value)} />
          </div>
          <div>
            <label style={S.label}>Side</label>
            <select style={S.select} value={side} onChange={e => setSide(e.target.value)}>
              <option>BUY</option><option>SELL</option>
            </select>
          </div>
          <div>
            <label style={S.label}>Quantity (shares)</label>
            <input style={S.input} value={qty} onChange={e => setQty(e.target.value)} />
          </div>
          <div>
            <label style={S.label}>Market Price</label>
            <input style={S.input} value={price} onChange={e => setPrice(e.target.value)} />
          </div>
          <div>
            <label style={S.label}>Order Type</label>
            <select style={S.select} value={orderType} onChange={e => setOrderType(e.target.value)}>
              <option>MARKET</option><option>LIMIT</option><option>STOP</option><option>STOP_LIMIT</option>
            </select>
          </div>
          <div>
            <label style={S.label}>Slippage Model</label>
            <select style={S.select} value={slipModel} onChange={e => setSlipModel(e.target.value)}>
              <option>FIXED_BPS</option><option>VOLUME_WEIGHTED</option><option>SQRT</option>
            </select>
          </div>
          {(orderType === "LIMIT" || orderType === "STOP_LIMIT") && (
            <div>
              <label style={S.label}>Limit Price</label>
              <input style={S.input} value={limitPrice} onChange={e => setLimitPrice(e.target.value)} />
            </div>
          )}
          {(orderType === "STOP" || orderType === "STOP_LIMIT") && (
            <div>
              <label style={S.label}>Stop Price</label>
              <input style={S.input} value={stopPrice} onChange={e => setStopPrice(e.target.value)} />
            </div>
          )}
          <div>
            <label style={S.label}>Slippage (bps)</label>
            <input style={S.input} value={slipBps} onChange={e => setSlipBps(e.target.value)} />
          </div>
        </div>
        <button style={S.btn} onClick={simulate} disabled={loading}>{loading ? "Simulating…" : "Simulate Order"}</button>
        {err && <div style={S.err}>{err}</div>}
      </div>

      {fill && (
        <div style={S.section}>
          <div style={S.sHdr}>Fill Result <span style={S.tag(statusColor[fill.status] || "#8b949e")}>{fill.status}</span></div>
          <div style={S.grid4}>
            {[
              ["Fill Qty", fill.fill_qty?.toFixed(2)],
              ["Fill Price", fill.fill_price?.toFixed(4)],
              ["Commission", fill.commission?.toFixed(4)],
              ["Market Impact", fill.market_impact?.toFixed(6)],
              ["Slippage (bps)", fill.slippage_bps?.toFixed(2)],
              ["Total Cost", fill.total_cost?.toFixed(2)],
              ["Fill Rate", fill.fill_rate?.toFixed(3)],
              ["Gross Cost", fill.gross_cost?.toFixed(2)],
            ].map(([label, val]) => (
              <div key={label} style={S.card}>
                <div style={S.cardLabel}>{label}</div>
                <div style={S.cardVal}>{val ?? "—"}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={S.section}>
        <div style={S.sHdr}>Session Slippage Report</div>
        <button style={{ ...S.btn, background: "#1f6feb" }} onClick={getReport}>Refresh Report</button>
        {report && (
          <div style={{ ...S.pre, marginTop: 12 }}>
            {`Fills: ${report.num_fills} | Avg Slippage: ${report.avg_slippage_bps?.toFixed(2)} bps | Max: ${report.max_slippage_bps?.toFixed(2)} bps\nFill Rate: ${(report.fill_rate * 100).toFixed(1)}% | Total Commission: ${report.total_commission?.toFixed(4)}`}
          </div>
        )}
      </div>
    </div>
  );
}
