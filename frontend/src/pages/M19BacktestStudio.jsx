import { useState } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 20, fontWeight: 700, color: "#f0f6fc", marginBottom: 4 },
  sub: { fontSize: 12, color: "#8b949e", marginBottom: 24 },
  row: { display: "flex", gap: 16, marginBottom: 16 },
  col: { flex: 1 },
  label: { fontSize: 11, color: "#8b949e", marginBottom: 4, display: "block" },
  input: { width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", padding: "6px 10px", fontSize: 13, boxSizing: "border-box" },
  btn: { background: "#238636", color: "#fff", border: "none", borderRadius: 6, padding: "8px 20px", fontSize: 13, cursor: "pointer", fontWeight: 600 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sHdr: { fontSize: 14, fontWeight: 700, color: "#58a6ff", marginBottom: 12 },
  result: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 8, padding: 16, marginTop: 16 },
  grid4: { display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12 },
  card: { background: "#161b22", borderRadius: 6, padding: "10px 14px" },
  cardLabel: { fontSize: 10, color: "#8b949e", textTransform: "uppercase", letterSpacing: "0.05em" },
  cardVal: { fontSize: 16, fontWeight: 700, color: "#f0f6fc", marginTop: 2 },
  badge: (ok) => ({ display: "inline-block", fontSize: 10, padding: "2px 6px", borderRadius: 4, background: ok ? "#1b4721" : "#3d1a1a", color: ok ? "#3fb950" : "#ff7b72" }),
  err: { color: "#ff7b72", fontSize: 12, marginTop: 8 },
  pre: { background: "#161b22", borderRadius: 6, padding: 12, fontSize: 11, color: "#8b949e", overflow: "auto", maxHeight: 200 },
};

const DEFAULT_PRICES = "100,101,102,104,103,105,107,106,108,110,109,112,115,113,116";

export default function M19BacktestStudio() {
  const [strategy, setStrategy] = useState("momentum");
  const [ticker, setTicker] = useState("AAPL");
  const [pricesText, setPricesText] = useState(DEFAULT_PRICES);
  const [commission, setCommission] = useState("0.001");
  const [slippage, setSlippage] = useState("5");
  const [posSize, setPosSize] = useState("0.1");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [backtests, setBacktests] = useState([]);

  const runBacktest = async () => {
    setLoading(true); setErr("");
    const prices = pricesText.split(",").map(p => parseFloat(p.trim())).filter(p => !isNaN(p));
    const bars = prices.map((p, i) => ({
      date: `2024-01-${String(i + 1).padStart(2, "0")}`,
      open: p, high: p * 1.01, low: p * 0.99, close: p, volume: 10000,
    }));
    const signals = [{ date: bars[0].date, ticker, signal_type: "LONG" }];
    try {
      const r = await fetch("/quant/backtest/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          strategy_name: strategy,
          signals,
          price_data: { [ticker]: bars },
          commission_rate: parseFloat(commission),
          slippage_bps: parseFloat(slippage),
          position_size_pct: parseFloat(posSize),
        }),
      });
      const d = await r.json();
      if (!r.ok) { setErr(JSON.stringify(d)); }
      else { setResult(d); }
    } catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  };

  const loadList = async () => {
    const r = await fetch("/quant/backtest/list");
    if (r.ok) setBacktests(await r.json());
  };

  const m = result?.metrics;

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Backtest Studio</div>
      <div style={S.sub}>Design, run, and inspect signal-driven strategy simulations.</div>

      <div style={S.section}>
        <div style={S.sHdr}>Strategy Configuration</div>
        <div style={S.row}>
          <div style={S.col}>
            <label style={S.label}>Strategy Name</label>
            <input style={S.input} value={strategy} onChange={e => setStrategy(e.target.value)} />
          </div>
          <div style={S.col}>
            <label style={S.label}>Ticker</label>
            <input style={S.input} value={ticker} onChange={e => setTicker(e.target.value)} />
          </div>
        </div>
        <div>
          <label style={S.label}>Daily Close Prices (comma-separated)</label>
          <input style={S.input} value={pricesText} onChange={e => setPricesText(e.target.value)} />
        </div>
        <div style={{ ...S.row, marginTop: 12 }}>
          <div style={S.col}>
            <label style={S.label}>Commission Rate</label>
            <input style={S.input} value={commission} onChange={e => setCommission(e.target.value)} />
          </div>
          <div style={S.col}>
            <label style={S.label}>Slippage (bps)</label>
            <input style={S.input} value={slippage} onChange={e => setSlippage(e.target.value)} />
          </div>
          <div style={S.col}>
            <label style={S.label}>Position Size %</label>
            <input style={S.input} value={posSize} onChange={e => setPosSize(e.target.value)} />
          </div>
        </div>
        <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
          <button style={S.btn} onClick={runBacktest} disabled={loading}>{loading ? "Running…" : "Run Backtest"}</button>
          <button style={{ ...S.btn, background: "#1f6feb" }} onClick={loadList}>Load History</button>
        </div>
        {err && <div style={S.err}>{err}</div>}
      </div>

      {result && (
        <div style={S.section}>
          <div style={S.sHdr}>Results — {result.strategy_name} <span style={S.badge(m.total_return >= 0)}>{m.total_return >= 0 ? "PROFIT" : "LOSS"}</span></div>
          <div style={S.grid4}>
            {[
              ["Total Return", `${(m.total_return * 100).toFixed(2)}%`],
              ["Ann. Return", `${(m.annualized_return * 100).toFixed(2)}%`],
              ["Sharpe", m.sharpe_ratio.toFixed(3)],
              ["Max Drawdown", `${(m.max_drawdown * 100).toFixed(2)}%`],
              ["Volatility", `${(m.volatility * 100).toFixed(2)}%`],
              ["Sortino", m.sortino_ratio.toFixed(3)],
              ["Win Rate", `${(m.win_rate * 100).toFixed(1)}%`],
              ["Trades", m.num_trades],
            ].map(([label, val]) => (
              <div key={label} style={S.card}>
                <div style={S.cardLabel}>{label}</div>
                <div style={S.cardVal}>{val}</div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 12, fontSize: 11, color: "#8b949e" }}>ID: {result.backtest_id}</div>
        </div>
      )}

      {backtests.length > 0 && (
        <div style={S.section}>
          <div style={S.sHdr}>Backtest History</div>
          <div style={S.pre}>
            {backtests.map(b => `${b.backtest_id.slice(0, 8)} | ${b.strategy_name} | Sharpe ${b.sharpe_ratio?.toFixed(2)} | ${(b.total_return * 100).toFixed(2)}%`).join("\n")}
          </div>
        </div>
      )}
    </div>
  );
}
