import { useState, useEffect } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 18, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 18, marginBottom: 14 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#a371f7", marginBottom: 12 },
  row2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 },
  input: { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, padding: "6px 10px", color: "#f0f6fc", fontSize: 12, width: "100%", boxSizing: "border-box", marginBottom: 6 },
  btn: (c="#a371f7") => ({ background: c + "22", border: `1px solid ${c}55`, borderRadius: 6, padding: "7px 16px", color: c, fontSize: 12, cursor: "pointer", fontFamily: "monospace", marginRight: 8, marginTop: 6 }),
  kv: { display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: "1px solid #21262d33", fontSize: 12 },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 11 },
  th: { color: "#8b949e", textAlign: "left", padding: "4px 8px", borderBottom: "1px solid #21262d" },
  td: { padding: "5px 8px", color: "#c9d1d9", borderBottom: "1px solid #161b22" },
};

export default function M18PortfolioIntel() {
  const [summary, setSummary] = useState(null);
  const [score, setScore] = useState(null);
  const [holdings, setHoldings] = useState([]);
  const [attribution, setAttribution] = useState(null);
  const [rebalance, setRebalance] = useState([]);
  const [nav, setNav] = useState("10000000");
  const [holdingForm, setHoldingForm] = useState({ ticker: "AAPL", weight: "0.20", sector: "Technology", expected_return: "0.12", volatility: "0.22", cost_basis: "150.00", current_price: "175.50", quantity: "1143" });

  const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  const refresh = () => {
    fetch("/m18/portfolio-intel/summary").then(r => r.json()).then(setSummary).catch(() => {});
    fetch("/m18/portfolio-intel/score").then(r => r.json()).then(setScore).catch(() => {});
    fetch("/m18/portfolio-intel/holdings").then(r => r.json()).then(setHoldings).catch(() => {});
  };
  useEffect(() => { refresh(); }, []);

  const setNavFn = async () => { await post("/m18/portfolio-intel/nav", { nav: parseFloat(nav) }); refresh(); };
  const addHolding = async () => {
    await post("/m18/portfolio-intel/holdings", {
      ...holdingForm,
      weight: parseFloat(holdingForm.weight), expected_return: parseFloat(holdingForm.expected_return),
      volatility: parseFloat(holdingForm.volatility), cost_basis: parseFloat(holdingForm.cost_basis),
      current_price: parseFloat(holdingForm.current_price), quantity: parseFloat(holdingForm.quantity),
    });
    refresh();
  };
  const computeRebalance = async () => {
    const targets = Object.fromEntries(holdings.map(h => [h.ticker, h.weight + 0.01]));
    const r = await post("/m18/portfolio-intel/rebalance", { target_weights: targets, tolerance: 0.005 });
    if (r.ok) setRebalance(await r.json());
  };
  const computeAttrib = async () => {
    const r = await post("/m18/portfolio-intel/attribution/brinson", {
      portfolio_sector_weights: { Technology: 0.35, Financials: 0.25, Healthcare: 0.20, Energy: 0.20 },
      benchmark_sector_weights: { Technology: 0.30, Financials: 0.25, Healthcare: 0.25, Energy: 0.20 },
      portfolio_sector_returns: { Technology: 0.15, Financials: 0.08, Healthcare: 0.12, Energy: 0.04 },
      benchmark_sector_returns: { Technology: 0.12, Financials: 0.07, Healthcare: 0.10, Energy: 0.03 },
      benchmark_total_return: 0.085,
    });
    if (r.ok) setAttribution(await r.json());
  };
  const addObs = async () => {
    await post("/m18/portfolio-intel/returns", { portfolio_return: 0.003 + (Math.random() - 0.5) * 0.01, benchmark_return: 0.002 });
  };

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Portfolio Intelligence</div>

      {score && (
        <div style={S.section}>
          <div style={S.sHdr}>Portfolio Score</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(6,1fr)", gap: 10 }}>
            {[["Overall", score.overall], ["Diversification", score.diversification], ["Momentum", score.momentum], ["Quality", score.quality], ["Value", score.value], ["Risk-Adj", score.risk_adjusted]].map(([l, v]) => (
              <div key={l} style={{ background: "#161b22", borderRadius: 6, padding: "8px 10px", textAlign: "center" }}>
                <div style={{ fontSize: 10, color: "#8b949e" }}>{l}</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: v > 60 ? "#3fb950" : v > 40 ? "#e3b341" : "#ff7b72" }}>{v?.toFixed(1)}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={S.row2}>
        <div style={S.section}>
          <div style={S.sHdr}>Add Holding</div>
          {["ticker","weight","sector","expected_return","volatility","cost_basis","current_price","quantity"].map(f => (
            <div key={f}>
              <div style={{ fontSize: 10, color: "#8b949e", marginBottom: 2 }}>{f}</div>
              <input style={S.input} value={holdingForm[f]} onChange={e => setHoldingForm(p => ({ ...p, [f]: e.target.value }))} />
            </div>
          ))}
          <div style={{ display: "flex", gap: 8, marginTop: 4, flexWrap: "wrap" }}>
            <div style={{ fontSize: 10, color: "#8b949e", marginBottom: 2, width: "100%" }}>NAV</div>
            <input style={{ ...S.input, width: 160 }} value={nav} onChange={e => setNav(e.target.value)} placeholder="NAV" />
            <button style={S.btn()} onClick={setNavFn}>Set NAV</button>
          </div>
          <button style={S.btn()} onClick={addHolding}>Add Holding</button>
          <button style={S.btn("#3fb950")} onClick={addObs}>Add Return Obs</button>
        </div>

        <div>
          <div style={S.section}>
            <div style={S.sHdr}>Analytics</div>
            <button style={S.btn()} onClick={computeAttrib}>Run Brinson Attribution</button>
            <button style={S.btn("#58a6ff")} onClick={computeRebalance}>Compute Rebalance</button>
            {attribution && (
              <div style={{ marginTop: 12 }}>
                {[["Allocation Effect", attribution.allocation_effect], ["Selection Effect", attribution.selection_effect], ["Interaction Effect", attribution.interaction_effect], ["Total Active Return", attribution.total_active_return]].map(([k, v]) => (
                  <div key={k} style={S.kv}>
                    <span style={{ color: "#8b949e" }}>{k}</span>
                    <span style={{ color: v >= 0 ? "#3fb950" : "#ff7b72" }}>{v != null ? (v * 100).toFixed(3) + "%" : "—"}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
          {rebalance.length > 0 && (
            <div style={S.section}>
              <div style={S.sHdr}>Rebalancing Trades</div>
              <table style={S.table}>
                <thead><tr>{["Ticker","Current %","Target %","Trade $","Reason"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr></thead>
                <tbody>
                  {rebalance.map(t => (
                    <tr key={t.ticker}>
                      <td style={{ ...S.td, color: "#58a6ff" }}>{t.ticker}</td>
                      <td style={S.td}>{(t.current_weight * 100).toFixed(1)}%</td>
                      <td style={S.td}>{(t.target_weight * 100).toFixed(1)}%</td>
                      <td style={{ ...S.td, color: t.trade_usd >= 0 ? "#3fb950" : "#ff7b72" }}>${t.trade_usd?.toFixed(0)}</td>
                      <td style={{ ...S.td, fontSize: 10 }}>{t.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <div style={S.section}>
        <div style={S.sHdr}>Holdings ({holdings.length})</div>
        {holdings.length === 0 ? <div style={{ color: "#8b949e", fontSize: 12 }}>No holdings. Add above.</div> : (
          <table style={S.table}>
            <thead><tr>{["Ticker","Weight","Sector","Exp Return","Volatility","Sharpe","P&L $"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr></thead>
            <tbody>
              {holdings.map(h => (
                <tr key={h.ticker}>
                  <td style={{ ...S.td, color: "#58a6ff" }}>{h.ticker}</td>
                  <td style={S.td}>{(h.weight * 100).toFixed(1)}%</td>
                  <td style={S.td}>{h.sector}</td>
                  <td style={{ ...S.td, color: "#3fb950" }}>{(h.expected_return * 100).toFixed(1)}%</td>
                  <td style={S.td}>{(h.volatility * 100).toFixed(1)}%</td>
                  <td style={{ ...S.td, color: h.sharpe >= 1 ? "#3fb950" : "#e3b341" }}>{h.sharpe?.toFixed(2)}</td>
                  <td style={{ ...S.td, color: h.pnl_usd >= 0 ? "#3fb950" : "#ff7b72" }}>${h.pnl_usd?.toFixed(0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
