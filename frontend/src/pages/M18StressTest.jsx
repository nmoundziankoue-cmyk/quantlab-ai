import { useState } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 18, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 18, marginBottom: 14 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#ff7b72", marginBottom: 12 },
  row2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 },
  input: { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, padding: "6px 10px", color: "#f0f6fc", fontSize: 12, width: "100%", boxSizing: "border-box", marginBottom: 6 },
  btn: (c = "#ff7b72") => ({ background: c + "22", border: `1px solid ${c}55`, borderRadius: 6, padding: "6px 14px", color: c, fontSize: 12, cursor: "pointer", fontFamily: "monospace", marginRight: 6, marginTop: 4 }),
  kv: { display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: "1px solid #21262d33", fontSize: 12 },
  pill: (c) => ({ display: "inline-block", fontSize: 10, padding: "1px 6px", borderRadius: 4, background: c + "22", color: c, fontWeight: 700, marginRight: 4 }),
};

const PRESET_SCENARIOS = [
  {
    label: "2008 Financial Crisis",
    scenario_name: "GFC_2008",
    description: "Simulate 2008 global financial crisis shock",
    equity_shock: -0.45, credit_spread_shock: 0.04, rate_shock: -0.02,
    fx_shock: -0.12, commodity_shock: -0.35, sector_shocks: { Financials: -0.65, Real_Estate: -0.55, Consumer: -0.30 },
  },
  {
    label: "COVID-19 Crash",
    scenario_name: "COVID_2020",
    description: "Q1 2020 pandemic market crash",
    equity_shock: -0.35, credit_spread_shock: 0.025, rate_shock: -0.015,
    fx_shock: -0.05, commodity_shock: -0.40, sector_shocks: { Travel: -0.70, Energy: -0.55, Retail: -0.40 },
  },
  {
    label: "Rate Shock +200bps",
    scenario_name: "RATE_SHOCK_200BPS",
    description: "Rapid 200bp rate increase",
    equity_shock: -0.15, credit_spread_shock: 0.015, rate_shock: 0.02,
    fx_shock: 0.05, commodity_shock: -0.10, sector_shocks: { Tech: -0.25, Utilities: -0.20 },
  },
  {
    label: "Mild Recession",
    scenario_name: "MILD_RECESSION",
    description: "Moderate economic downturn",
    equity_shock: -0.20, credit_spread_shock: 0.01, rate_shock: -0.01,
    fx_shock: -0.03, commodity_shock: -0.15, sector_shocks: { Consumer_Disc: -0.25, Industrials: -0.22 },
  },
];

export default function M18StressTest() {
  const [positions, setPositions] = useState([
    { ticker: "AAPL", market_value: 2000000, sector: "Technology" },
    { ticker: "JPM", market_value: 1500000, sector: "Financials" },
    { ticker: "XOM", market_value: 800000, sector: "Energy" },
  ]);
  const [custom, setCustom] = useState({ scenario_name: "CUSTOM", description: "Custom scenario", equity_shock: "-0.20", credit_spread_shock: "0.015", rate_shock: "0.01", fx_shock: "-0.05", commodity_shock: "-0.10" });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [newPos, setNewPos] = useState({ ticker: "", market_value: "", sector: "" });

  const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  const runScenario = async (scenario) => {
    setLoading(true);
    const r = await post("/m18/risk/stress-test", {
      positions: positions.map(p => ({ ticker: p.ticker, quantity: 100, current_price: p.market_value / 100, sector: p.sector, country: "US" })),
      ...scenario,
      sector_shocks: scenario.sector_shocks || {},
    });
    if (r.ok) setResult(await r.json());
    setLoading(false);
  };

  const runCustom = () => runScenario({
    ...custom,
    equity_shock: parseFloat(custom.equity_shock),
    credit_spread_shock: parseFloat(custom.credit_spread_shock),
    rate_shock: parseFloat(custom.rate_shock),
    fx_shock: parseFloat(custom.fx_shock),
    commodity_shock: parseFloat(custom.commodity_shock),
    sector_shocks: {},
  });

  const addPosition = () => {
    if (!newPos.ticker || !newPos.market_value) return;
    setPositions(p => [...p, { ...newPos, market_value: parseFloat(newPos.market_value) }]);
    setNewPos({ ticker: "", market_value: "", sector: "" });
  };

  const totalMV = positions.reduce((s, p) => s + p.market_value, 0);

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Stress Test Engine</div>

      <div style={S.row2}>
        <div>
          <div style={S.section}>
            <div style={S.sHdr}>Portfolio Positions ({positions.length})</div>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11, marginBottom: 12 }}>
              <thead><tr>{["Ticker","Market Value","Sector",""].map(h => <th key={h} style={{ color: "#8b949e", textAlign: "left", padding: "4px 8px", borderBottom: "1px solid #21262d" }}>{h}</th>)}</tr></thead>
              <tbody>
                {positions.map((p, i) => (
                  <tr key={i}>
                    <td style={{ padding: "5px 8px", color: "#58a6ff", borderBottom: "1px solid #161b22" }}>{p.ticker}</td>
                    <td style={{ padding: "5px 8px", color: "#f0f6fc", borderBottom: "1px solid #161b22" }}>${p.market_value.toLocaleString()}</td>
                    <td style={{ padding: "5px 8px", color: "#8b949e", borderBottom: "1px solid #161b22" }}>{p.sector}</td>
                    <td style={{ padding: "5px 8px", borderBottom: "1px solid #161b22" }}><button onClick={() => setPositions(prev => prev.filter((_, j) => j !== i))} style={{ background: "none", border: "none", color: "#ff7b72", cursor: "pointer", fontSize: 11 }}>✕</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr auto", gap: 6 }}>
              {["ticker", "market_value", "sector"].map(f => (
                <input key={f} style={{ ...S.input, marginBottom: 0 }} value={newPos[f]} onChange={e => setNewPos(p => ({ ...p, [f]: e.target.value }))} placeholder={f} />
              ))}
              <button style={S.btn("#56d364")} onClick={addPosition}>+</button>
            </div>
            <div style={{ fontSize: 11, color: "#8b949e", marginTop: 8 }}>Total NAV: ${totalMV.toLocaleString()}</div>
          </div>

          <div style={S.section}>
            <div style={S.sHdr}>Custom Scenario</div>
            {[["scenario_name","Scenario Name"],["description","Description"],["equity_shock","Equity Shock (e.g. -0.20)"],["credit_spread_shock","Credit Spread Shock"],["rate_shock","Rate Shock"],["fx_shock","FX Shock"],["commodity_shock","Commodity Shock"]].map(([f, l]) => (
              <div key={f}>
                <div style={{ fontSize: 10, color: "#8b949e", marginBottom: 2 }}>{l}</div>
                <input style={S.input} value={custom[f]} onChange={e => setCustom(p => ({ ...p, [f]: e.target.value }))} />
              </div>
            ))}
            <button style={S.btn()} onClick={runCustom} disabled={loading}>Run Custom</button>
          </div>
        </div>

        <div>
          <div style={S.section}>
            <div style={S.sHdr}>Preset Scenarios</div>
            {PRESET_SCENARIOS.map(sc => (
              <div key={sc.scenario_name} style={{ background: "#161b22", borderRadius: 6, padding: "10px 14px", marginBottom: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: "#f0f6fc" }}>{sc.label}</div>
                    <div style={{ fontSize: 10, color: "#8b949e", marginTop: 2 }}>{sc.description}</div>
                    <div style={{ marginTop: 4 }}>
                      <span style={S.pill(sc.equity_shock < -0.3 ? "#ff7b72" : "#f0883e")}>Equity {(sc.equity_shock * 100).toFixed(0)}%</span>
                      <span style={S.pill("#58a6ff")}>Rates {(sc.rate_shock * 100).toFixed(0)}bp</span>
                    </div>
                  </div>
                  <button style={S.btn()} onClick={() => runScenario(sc)} disabled={loading}>{loading ? "…" : "Run"}</button>
                </div>
              </div>
            ))}
          </div>

          {result && (
            <div style={S.section}>
              <div style={S.sHdr}>Result: {result.scenario_name}</div>
              {[
                ["Portfolio P&L", `$${result.portfolio_pnl?.toLocaleString(undefined, { maximumFractionDigits: 0 })}`, result.portfolio_pnl >= 0 ? "#3fb950" : "#ff7b72"],
                ["P&L %", `${(result.portfolio_pnl_pct * 100)?.toFixed(2)}%`, result.portfolio_pnl_pct >= 0 ? "#3fb950" : "#ff7b72"],
                ["Worst Position", result.worst_position_ticker, "#ff7b72"],
                ["Best Position", result.best_position_ticker, "#3fb950"],
                ["Surviving Positions", result.positions_surviving, "#f0f6fc"],
              ].map(([k, v, c]) => (
                <div key={k} style={S.kv}><span style={{ color: "#8b949e" }}>{k}</span><span style={{ color: c, fontWeight: 700 }}>{v}</span></div>
              ))}
              {result.position_impacts?.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 6 }}>Position Impact Breakdown</div>
                  {result.position_impacts.map(p => (
                    <div key={p.ticker} style={{ display: "flex", justifyContent: "space-between", fontSize: 11, padding: "2px 0" }}>
                      <span style={{ color: "#c9d1d9" }}>{p.ticker}</span>
                      <span style={{ color: p.pnl >= 0 ? "#3fb950" : "#ff7b72" }}>{(p.pnl_pct * 100)?.toFixed(2)}%</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
