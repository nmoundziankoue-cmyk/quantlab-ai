import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import axios from "axios";

const API = "";
const card = { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20, marginBottom: 20 };

function RiskGauge({ label, value, max, unit = "", color = "#d29922" }) {
  const pct = max ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, fontSize: 13 }}>
        <span style={{ color: "#8b949e" }}>{label}</span>
        <span style={{ color: "#e6edf3", fontWeight: 600 }}>{typeof value === "number" ? value.toFixed(2) : value}{unit}</span>
      </div>
      <div style={{ background: "#21262d", borderRadius: 4, height: 8 }}>
        <div style={{ width: `${pct}%`, height: 8, background: color, borderRadius: 4 }} />
      </div>
    </div>
  );
}

export default function RiskCenter() {
  const [ticker, setTicker] = useState("AAPL");
  const [result, setResult] = useState(null);

  const analyze = useMutation({
    mutationFn: () => axios.get(`${API}/analytics/risk/ticker/${ticker.toUpperCase()}`).then(r => r.data),
    onSuccess: setResult,
  });

  return (
    <div style={{ padding: 28, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Risk Center</h1>
        <p style={{ color: "#8b949e", margin: "4px 0 0", fontSize: 13 }}>VaR, CVaR, drawdown, and factor risk analysis</p>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
        <input
          value={ticker}
          onChange={e => setTicker(e.target.value.toUpperCase())}
          style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "10px 14px", fontSize: 14, width: 160 }}
          placeholder="Ticker"
        />
        <button
          onClick={() => analyze.mutate()}
          style={{ background: "#238636", border: "none", borderRadius: 6, color: "#fff", padding: "10px 20px", cursor: "pointer", fontSize: 13, fontWeight: 600 }}
          disabled={analyze.isPending}
        >
          {analyze.isPending ? "Analyzing…" : "Analyze Risk"}
        </button>
      </div>

      {result && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          <div style={card}>
            <div style={{ fontWeight: 600, marginBottom: 16, fontSize: 14 }}>Value at Risk</div>
            <RiskGauge label="VaR 95% (1-day)" value={+result.var_95} max={10} unit="%" color="#d29922" />
            <RiskGauge label="CVaR 95% (Expected Shortfall)" value={+result.cvar_95} max={10} unit="%" color="#f85149" />
            <RiskGauge label="Max Drawdown" value={+result.max_drawdown} max={50} unit="%" color="#f85149" />
          </div>
          <div style={card}>
            <div style={{ fontWeight: 600, marginBottom: 16, fontSize: 14 }}>Return Metrics</div>
            <RiskGauge label="Beta" value={+result.beta} max={3} color="#58a6ff" />
            <RiskGauge label="Sharpe Ratio" value={+result.sharpe} max={3} color="#3fb950" />
            <RiskGauge label="Annualized Volatility" value={+result.volatility * 100} max={100} unit="%" color="#d29922" />
          </div>
        </div>
      )}

      {!result && (
        <div style={{ ...card, textAlign: "center", padding: 60, color: "#8b949e" }}>
          Enter a ticker and click "Analyze Risk" to view risk metrics
        </div>
      )}

      {/* Stress Scenarios */}
      <div style={card}>
        <div style={{ fontWeight: 600, marginBottom: 16, fontSize: 14 }}>Historical Stress Scenarios</div>
        {[
          { name: "2008 Financial Crisis", impact: "-38.5%", duration: "17 months" },
          { name: "2020 COVID Crash", impact: "-33.9%", duration: "1 month" },
          { name: "2022 Rate Hike Cycle", impact: "-25.4%", duration: "12 months" },
          { name: "Dot-com Bubble (2000–02)", impact: "-49.1%", duration: "30 months" },
        ].map(s => (
          <div key={s.name} style={{ display: "flex", justifyContent: "space-between", padding: "10px 0", borderBottom: "1px solid #21262d", fontSize: 13 }}>
            <span style={{ color: "#e6edf3" }}>{s.name}</span>
            <span style={{ color: "#f85149", fontWeight: 600 }}>{s.impact}</span>
            <span style={{ color: "#8b949e" }}>{s.duration}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
