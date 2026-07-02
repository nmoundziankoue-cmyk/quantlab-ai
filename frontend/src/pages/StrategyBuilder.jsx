import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import axios from "axios";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8001";
const card = { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20 };
const input = {
  background: "#0d1117", border: "1px solid #30363d", borderRadius: 6,
  color: "#e6edf3", padding: "8px 12px", fontSize: 13, width: "100%", boxSizing: "border-box",
};
const btn = {
  background: "#238636", border: "none", borderRadius: 6, color: "#fff",
  padding: "10px 20px", cursor: "pointer", fontSize: 13, fontWeight: 600,
};

const STRATEGIES = ["covered_call","protective_put","bull_call_spread","bear_put_spread","straddle","strangle","iron_condor","butterfly"];

function PayoffChart({ curve }) {
  if (!curve?.length) return null;
  const payoffs = curve.map(p => p.payoff);
  const spots = curve.map(p => p.spot);
  const minP = Math.min(...payoffs);
  const maxP = Math.max(...payoffs);
  const range = maxP - minP || 1;
  const w = 600, h = 160, pad = 40;

  return (
    <svg width={w} height={h} style={{ display: "block", overflow: "visible" }}>
      <line x1={pad} y1={0} x2={pad} y2={h} stroke="#30363d" strokeWidth={1} />
      <line x1={pad} y1={h - pad} x2={w} y2={h - pad} stroke="#30363d" strokeWidth={1} />
      {/* zero line */}
      {(() => {
        const zeroY = h - pad - ((0 - minP) / range) * (h - pad - 10);
        return <line x1={pad} y1={zeroY} x2={w} y2={zeroY} stroke="#8b949e" strokeWidth={1} strokeDasharray="4 4" />;
      })()}
      <polyline
        fill="none"
        stroke="#58a6ff"
        strokeWidth={2}
        points={curve.map((p, i) => {
          const x = pad + (i / (curve.length - 1)) * (w - pad - 10);
          const y = h - pad - ((p.payoff - minP) / range) * (h - pad - 10);
          return `${x},${y}`;
        }).join(" ")}
      />
      {spots.filter((_, i) => i % 2 === 0).map((s, i) => {
        const actualIdx = i * 2;
        const x = pad + (actualIdx / (curve.length - 1)) * (w - pad - 10);
        return <text key={s} x={x} y={h - 2} fontSize={10} fill="#8b949e" textAnchor="middle">{s}</text>;
      })}
    </svg>
  );
}

export default function StrategyBuilder() {
  const [form, setForm] = useState({ strategy: "straddle", spot: "150", strike: "150", expiry_T: "0.25", risk_free_rate: "0.05", volatility: "0.20" });
  const [result, setResult] = useState(null);

  const build = useMutation({
    mutationFn: () => axios.post(`${API}/options/strategies/build`, {
      strategy: form.strategy,
      spot: +form.spot,
      strike: +form.strike,
      expiry_T: +form.expiry_T,
      risk_free_rate: +form.risk_free_rate,
      volatility: +form.volatility,
    }).then(r => r.data),
    onSuccess: setResult,
  });

  const field = (label, key) => (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 4 }}>{label}</div>
      <input style={input} value={form[key]} onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))} />
    </div>
  );

  return (
    <div style={{ padding: 28, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Options Strategy Builder</h1>
        <p style={{ color: "#8b949e", margin: "4px 0 0", fontSize: 13 }}>Price and visualize 8 classic options strategies</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: 20 }}>
        {/* Controls */}
        <div style={card}>
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 4 }}>Strategy</div>
            <select
              style={{ ...input, cursor: "pointer" }}
              value={form.strategy}
              onChange={e => setForm(f => ({ ...f, strategy: e.target.value }))}
            >
              {STRATEGIES.map(s => <option key={s} value={s}>{s.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}</option>)}
            </select>
          </div>
          {field("Spot Price", "spot")}
          {field("Strike Price", "strike")}
          {field("Time to Expiry (years)", "expiry_T")}
          {field("Risk-Free Rate", "risk_free_rate")}
          {field("Implied Volatility", "volatility")}
          <button style={btn} onClick={() => build.mutate()} disabled={build.isPending}>
            {build.isPending ? "Pricing…" : "Build Strategy"}
          </button>
        </div>

        {/* Results */}
        <div>
          {result && (
            <>
              <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
                {[
                  ["Net Cost", result.net_cost],
                  ["Max Profit", result.max_profit],
                  ["Max Loss", result.max_loss],
                  ["Delta", result.greeks?.delta],
                  ["Theta", result.greeks?.theta],
                  ["Vega", result.greeks?.vega],
                ].map(([k, v]) => (
                  <div key={k} style={{ ...card, flex: "1 1 120px" }}>
                    <div style={{ fontSize: 11, color: "#8b949e" }}>{k}</div>
                    <div style={{ fontSize: 20, fontWeight: 700, color: typeof v === "number" && v < 0 ? "#f85149" : "#3fb950" }}>
                      {typeof v === "number" ? v.toFixed(3) : "—"}
                    </div>
                  </div>
                ))}
              </div>

              <div style={{ ...card, marginBottom: 16 }}>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>P&L at Expiry</div>
                <PayoffChart curve={result.payoff_curve} />
              </div>

              <div style={card}>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Legs ({result.legs?.length})</div>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead><tr style={{ borderBottom: "1px solid #30363d" }}>
                    {["Type","Action","Strike","Premium"].map(h => <th key={h} style={{ textAlign: "left", padding: "6px 10px", color: "#8b949e", fontWeight: 500 }}>{h}</th>)}
                  </tr></thead>
                  <tbody>
                    {result.legs.map((l, i) => (
                      <tr key={i} style={{ borderBottom: "1px solid #21262d" }}>
                        <td style={{ padding: "8px 10px" }}>{l.type}</td>
                        <td style={{ padding: "8px 10px", color: l.action === "buy" ? "#3fb950" : "#f85149" }}>{l.action}</td>
                        <td style={{ padding: "8px 10px" }}>{l.strike}</td>
                        <td style={{ padding: "8px 10px" }}>{l.premium?.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
          {!result && !build.isPending && (
            <div style={{ ...card, textAlign: "center", padding: 60, color: "#8b949e" }}>
              Configure parameters and click "Build Strategy"
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
