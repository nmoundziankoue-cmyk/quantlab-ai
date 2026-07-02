import { useState } from "react";
import { useOptionsChain, useExpectedMove, useVolatilitySkew, useIVSurface } from "../hooks/useOptions";

const S = {
  page: { padding: 24, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" },
  title: { fontSize: 22, fontWeight: 700, marginBottom: 20 },
  grid2: { display: "grid", gridTemplateColumns: "340px 1fr", gap: 16 },
  card: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20, marginBottom: 16 },
  label: { fontSize: 12, color: "#8b949e", marginBottom: 4, display: "block" },
  input: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "8px 12px", color: "#e6edf3", fontSize: 13, width: "100%", outline: "none", marginBottom: 10, boxSizing: "border-box" },
  btn: (c = "#238636") => ({ background: c, border: "none", borderRadius: 6, padding: "8px 16px", color: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 600, marginRight: 8, marginBottom: 8 }),
  sectionTitle: { fontSize: 13, color: "#8b949e", fontWeight: 600, marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.05em" },
  table: { width: "100%", borderCollapse: "collapse" },
  th: { padding: "8px 10px", textAlign: "right", fontSize: 11, color: "#8b949e", fontWeight: 600, borderBottom: "1px solid #30363d" },
  td: { padding: "7px 10px", textAlign: "right", fontSize: 12, borderBottom: "1px solid #21262d" },
  metricRow: { display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #21262d" },
  metricLabel: { fontSize: 12, color: "#8b949e" },
  metricVal: { fontSize: 13, fontWeight: 600 },
  badge: (c) => ({ background: c + "22", color: c, borderRadius: 4, padding: "2px 8px", fontSize: 11, fontWeight: 600 }),
  tabs: { display: "flex", gap: 4, marginBottom: 20, borderBottom: "1px solid #30363d" },
  tab: (active) => ({ padding: "8px 16px", cursor: "pointer", fontSize: 13, fontWeight: 600, borderBottom: `2px solid ${active ? "#f0883e" : "transparent"}`, color: active ? "#f0883e" : "#8b949e", marginBottom: -1 }),
};

const CALL_COLOR = "#3fb950";
const PUT_COLOR = "#f85149";

function greekCell(val) {
  const v = typeof val === "number" ? val.toFixed(4) : "—";
  return v;
}

export default function OptionsDesk() {
  const [ticker, setTicker] = useState("AAPL");
  const [price, setPrice] = useState(150);
  const [atmIv, setAtmIv] = useState(0.25);
  const [expiry, setExpiry] = useState(30);
  const [tab, setTab] = useState("chain");
  const [chainData, setChainData] = useState(null);
  const [moveData, setMoveData] = useState(null);
  const [skewData, setSkewData] = useState(null);
  const [surfaceData, setSurfaceData] = useState(null);

  const getChain = useOptionsChain();
  const getExpectedMove = useExpectedMove();
  const getSkew = useVolatilitySkew();
  const getIVSurface = useIVSurface();

  const handleLoad = () => {
    getChain.mutate({ ticker, underlying_price: price, expiry_days_list: [7, 14, 30, 60, 90] }, { onSuccess: setChainData });
    getExpectedMove.mutate({ underlying_price: price, atm_iv: atmIv, expiry_days: expiry }, { onSuccess: setMoveData });
    getSkew.mutate({ underlying_price: price, atm_iv: atmIv, expiry_days: expiry }, { onSuccess: setSkewData });
    getIVSurface.mutate({ ticker, underlying_price: price }, { onSuccess: setSurfaceData });
  };

  const isLoading = getChain.isPending || getExpectedMove.isPending;

  const tabs = [
    { k: "chain", l: "Options Chain" },
    { k: "move", l: "Expected Move" },
    { k: "skew", l: "Vol Skew" },
    { k: "surface", l: "IV Surface" },
  ];

  const filteredChain = chainData?.chain?.filter((c) => c.expiry_days === expiry) || [];
  const calls = filteredChain.filter((c) => c.option_type === "CALL").slice(0, 9);
  const puts = filteredChain.filter((c) => c.option_type === "PUT").slice(0, 9);

  return (
    <div style={S.page}>
      <div style={S.title}>Options Desk</div>
      <div style={S.grid2}>
        <div>
          <div style={S.card}>
            <div style={S.sectionTitle}>Configuration</div>
            <label style={S.label}>Ticker</label>
            <input style={S.input} value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} />
            <label style={S.label}>Underlying Price</label>
            <input type="number" style={S.input} value={price} onChange={(e) => setPrice(parseFloat(e.target.value))} />
            <label style={S.label}>ATM IV (decimal)</label>
            <input type="number" step="0.01" style={S.input} value={atmIv} onChange={(e) => setAtmIv(parseFloat(e.target.value))} />
            <label style={S.label}>Expiry (days)</label>
            <input type="number" style={S.input} value={expiry} onChange={(e) => setExpiry(parseInt(e.target.value))} />
            <button style={S.btn("#f0883e")} onClick={handleLoad} disabled={isLoading}>
              {isLoading ? "Loading..." : "Load Options Data"}
            </button>
          </div>

          {moveData && (
            <div style={S.card}>
              <div style={S.sectionTitle}>Expected Move ({expiry}D)</div>
              {[
                ["Underlying", `$${moveData.underlying_price}`],
                ["ATM IV", `${(moveData.atm_iv * 100).toFixed(1)}%`],
                ["1σ Move", `±$${moveData.expected_move_1sigma?.toFixed(2)}`],
                ["1σ Upper", `$${moveData.upper_bound_1sigma?.toFixed(2)}`],
                ["1σ Lower", `$${moveData.lower_bound_1sigma?.toFixed(2)}`],
                ["% Move 1σ", `${moveData.pct_move_1sigma?.toFixed(2)}%`],
              ].map(([k, v]) => (
                <div key={k} style={S.metricRow}><span style={S.metricLabel}>{k}</span><span style={S.metricVal}>{v}</span></div>
              ))}
            </div>
          )}

          {skewData && (
            <div style={S.card}>
              <div style={S.sectionTitle}>Volatility Skew</div>
              {[
                ["ATM IV", `${(skewData.atm_iv * 100).toFixed(1)}%`],
                ["25Δ Put IV", `${(skewData.put_25d_iv * 100).toFixed(1)}%`],
                ["25Δ Call IV", `${(skewData.call_25d_iv * 100).toFixed(1)}%`],
                ["Risk Reversal", `${(skewData.risk_reversal_25d * 100).toFixed(2)}%`],
                ["Put Strike", `$${skewData.put_25d_strike}`],
                ["Call Strike", `$${skewData.call_25d_strike}`],
              ].map(([k, v]) => (
                <div key={k} style={S.metricRow}><span style={S.metricLabel}>{k}</span><span style={S.metricVal}>{v}</span></div>
              ))}
            </div>
          )}
        </div>

        <div>
          <div style={S.tabs}>
            {tabs.map(({ k, l }) => (
              <div key={k} style={S.tab(tab === k)} onClick={() => setTab(k)}>{l}</div>
            ))}
          </div>

          {tab === "chain" && chainData && (
            <div style={S.card}>
              <div style={S.sectionTitle}>{ticker} Options Chain — {expiry}D Expiry</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div>
                  <div style={{ ...S.sectionTitle, color: CALL_COLOR }}>Calls</div>
                  <table style={S.table}>
                    <thead><tr>
                      <th style={{ ...S.th, textAlign: "left" }}>Strike</th>
                      <th style={S.th}>Price</th>
                      <th style={S.th}>IV</th>
                      <th style={S.th}>Δ</th>
                      <th style={S.th}>Γ</th>
                      <th style={S.th}>OI</th>
                    </tr></thead>
                    <tbody>
                      {calls.map((c) => (
                        <tr key={c.strike}>
                          <td style={{ ...S.td, textAlign: "left", fontWeight: 700, color: "#58a6ff" }}>${c.strike}</td>
                          <td style={{ ...S.td, color: CALL_COLOR }}>${c.theoretical_price?.toFixed(3)}</td>
                          <td style={S.td}>{(c.implied_vol * 100).toFixed(1)}%</td>
                          <td style={S.td}>{greekCell(c.delta)}</td>
                          <td style={S.td}>{greekCell(c.gamma)}</td>
                          <td style={S.td}>{(c.open_interest || 0).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div>
                  <div style={{ ...S.sectionTitle, color: PUT_COLOR }}>Puts</div>
                  <table style={S.table}>
                    <thead><tr>
                      <th style={{ ...S.th, textAlign: "left" }}>Strike</th>
                      <th style={S.th}>Price</th>
                      <th style={S.th}>IV</th>
                      <th style={S.th}>Δ</th>
                      <th style={S.th}>Γ</th>
                      <th style={S.th}>OI</th>
                    </tr></thead>
                    <tbody>
                      {puts.map((p) => (
                        <tr key={p.strike}>
                          <td style={{ ...S.td, textAlign: "left", fontWeight: 700, color: "#58a6ff" }}>${p.strike}</td>
                          <td style={{ ...S.td, color: PUT_COLOR }}>${p.theoretical_price?.toFixed(3)}</td>
                          <td style={S.td}>{(p.implied_vol * 100).toFixed(1)}%</td>
                          <td style={S.td}>{greekCell(p.delta)}</td>
                          <td style={S.td}>{greekCell(p.gamma)}</td>
                          <td style={S.td}>{(p.open_interest || 0).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {tab === "surface" && surfaceData && (
            <div style={S.card}>
              <div style={S.sectionTitle}>Implied Volatility Surface — {ticker}</div>
              <div style={{ overflowX: "auto" }}>
                <table style={S.table}>
                  <thead>
                    <tr>
                      <th style={{ ...S.th, textAlign: "left" }}>Expiry</th>
                      {surfaceData.strike_pcts?.map((p) => (
                        <th key={p} style={S.th}>{(p * 100).toFixed(0)}%</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {surfaceData.expiry_days?.map((d, i) => (
                      <tr key={d}>
                        <td style={{ ...S.td, textAlign: "left", fontWeight: 600, color: "#8b949e" }}>{d}D</td>
                        {surfaceData.surface?.[i]?.map((iv, j) => {
                          const hue = iv < 0.2 ? "#3fb950" : iv < 0.3 ? "#f0883e" : "#f85149";
                          return <td key={j} style={{ ...S.td, color: hue }}>{(iv * 100).toFixed(1)}%</td>;
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {tab === "move" && !moveData && (
            <div style={{ ...S.card, textAlign: "center", padding: 60 }}>
              <div style={{ fontSize: 36, marginBottom: 12 }}>📊</div>
              <div style={{ color: "#8b949e" }}>Load options data to see expected move analysis</div>
            </div>
          )}

          {tab === "skew" && !skewData && (
            <div style={{ ...S.card, textAlign: "center", padding: 60 }}>
              <div style={{ fontSize: 36, marginBottom: 12 }}>📉</div>
              <div style={{ color: "#8b949e" }}>Load options data to see volatility skew</div>
            </div>
          )}

          {!chainData && tab === "chain" && (
            <div style={{ ...S.card, textAlign: "center", padding: 60 }}>
              <div style={{ fontSize: 36, marginBottom: 12 }}>📈</div>
              <div style={{ color: "#8b949e" }}>Enter a ticker and underlying price, then click "Load Options Data"</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
