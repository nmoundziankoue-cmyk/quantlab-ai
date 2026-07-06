import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import axios from "axios";

const API = "";
const card = { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20, marginBottom: 16 };

export default function ResearchNotebook() {
  const [params, setParams] = useState({ prices: "100,102,101,103,105,104,107,108,110,109,112,111,113,115,114", fast: "5", slow: "10" });
  const [result, setResult] = useState(null);
  const [kelly, setKelly] = useState({ win_prob: "0.55", win_return: "0.08", loss_return: "0.04" });
  const [kellyResult, setKellyResult] = useState(null);

  const runWF = useMutation({
    mutationFn: () => {
      const prices = params.prices.split(",").map(Number).filter(n => !isNaN(n));
      return axios.post(`${API}/backtest/walkforward/run`, {
        prices,
        fast_window: +params.fast,
        slow_window: +params.slow,
        in_sample_size: Math.floor(prices.length * 0.6),
        out_sample_size: Math.floor(prices.length * 0.2),
      }).then(r => r.data);
    },
    onSuccess: setResult,
  });

  const runKelly = useMutation({
    mutationFn: () => axios.post(`${API}/backtest/walkforward/kelly`, kelly).then(r => r.data),
    onSuccess: setKellyResult,
  });

  return (
    <div style={{ padding: 28, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Research Notebook</h1>
        <p style={{ color: "#8b949e", margin: "4px 0 0", fontSize: 13 }}>Walk-forward backtesting and Kelly Criterion sizing</p>
      </div>

      {/* Walk-forward */}
      <div style={card}>
        <div style={{ fontWeight: 600, marginBottom: 16 }}>Walk-Forward Test (SMA Crossover)</div>
        <div style={{ display: "flex", gap: 12, marginBottom: 14, flexWrap: "wrap" }}>
          {[["Prices (CSV)", "prices"], ["Fast Window", "fast"], ["Slow Window", "slow"]].map(([label, key]) => (
            <div key={key} style={{ flex: "1 1 200px" }}>
              <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 4 }}>{label}</div>
              <input
                style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "8px 10px", fontSize: 13, width: "100%", boxSizing: "border-box" }}
                value={params[key]} onChange={e => setParams(p => ({ ...p, [key]: e.target.value }))}
              />
            </div>
          ))}
        </div>
        <button onClick={() => runWF.mutate()} style={{ background: "#238636", border: "none", borderRadius: 6, color: "#fff", padding: "8px 18px", cursor: "pointer", fontSize: 13 }}>
          {runWF.isPending ? "Running…" : "Run Walk-Forward"}
        </button>

        {result && (
          <div style={{ marginTop: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10, color: "#8b949e" }}>Aggregate OOS Results</div>
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              {[
                ["Sharpe", result.aggregate?.oos_combined?.sharpe],
                ["CAGR", result.aggregate?.oos_combined?.cagr ? `${(result.aggregate.oos_combined.cagr * 100).toFixed(1)}%` : "—"],
                ["Max DD", result.aggregate?.oos_combined?.max_drawdown ? `${(result.aggregate.oos_combined.max_drawdown * 100).toFixed(1)}%` : "—"],
                ["Return", result.aggregate?.oos_combined?.total_return ? `${(result.aggregate.oos_combined.total_return * 100).toFixed(2)}%` : "—"],
                ["Windows", result.aggregate?.n_windows],
                ["Consistency", result.aggregate?.consistency ? `${(result.aggregate.consistency * 100).toFixed(0)}%` : "—"],
              ].map(([k, v]) => (
                <div key={k} style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "10px 16px" }}>
                  <div style={{ fontSize: 11, color: "#8b949e" }}>{k}</div>
                  <div style={{ fontSize: 18, fontWeight: 700 }}>{v ?? "—"}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Kelly */}
      <div style={card}>
        <div style={{ fontWeight: 600, marginBottom: 16 }}>Kelly Criterion Position Sizing</div>
        <div style={{ display: "flex", gap: 12, marginBottom: 14 }}>
          {[["Win Probability", "win_prob"], ["Win Return", "win_return"], ["Loss Return (abs)", "loss_return"]].map(([label, key]) => (
            <div key={key} style={{ flex: 1 }}>
              <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 4 }}>{label}</div>
              <input
                style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "8px 10px", fontSize: 13, width: "100%", boxSizing: "border-box" }}
                value={kelly[key]} onChange={e => setKelly(k => ({ ...k, [key]: e.target.value }))}
              />
            </div>
          ))}
        </div>
        <button onClick={() => runKelly.mutate()} style={{ background: "#1f6feb", border: "none", borderRadius: 6, color: "#fff", padding: "8px 18px", cursor: "pointer", fontSize: 13 }}>
          Calculate Kelly
        </button>

        {kellyResult && (
          <div style={{ marginTop: 16, display: "flex", gap: 12 }}>
            {[
              ["Full Kelly", kellyResult.full_kelly ? `${(kellyResult.full_kelly * 100).toFixed(1)}%` : "—"],
              ["Half Kelly", kellyResult.half_kelly ? `${(kellyResult.half_kelly * 100).toFixed(1)}%` : "—"],
              ["Quarter Kelly", kellyResult.quarter_kelly ? `${(kellyResult.quarter_kelly * 100).toFixed(1)}%` : "—"],
              ["Exp Log Growth", kellyResult.expected_log_growth?.toFixed(6)],
            ].map(([k, v]) => (
              <div key={k} style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "10px 16px", flex: 1 }}>
                <div style={{ fontSize: 11, color: "#8b949e" }}>{k}</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: "#58a6ff" }}>{v ?? "—"}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
