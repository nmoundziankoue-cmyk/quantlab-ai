import { useState } from "react";
import { eventsApi } from "../api/eventsApi";

const CARD = { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" };
const INPUT = { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", padding: "6px 10px", fontSize: 12, fontFamily: "monospace" };
const BTN = (a) => ({ padding: "7px 16px", borderRadius: 6, border: "none", cursor: "pointer", fontSize: 12, background: a ? "#1f6feb" : "#21262d", color: "#f0f6fc", fontFamily: "monospace" });

const SAMPLE_PRE = [-0.005, 0.002, -0.001, 0.003, -0.002];
const SAMPLE_POST = [0.04, 0.015, -0.002, 0.008, 0.005, 0.003, -0.001, 0.002, 0.004, 0.001];

function BarChart({ label, value, max, color }) {
  const pct = max > 0 ? Math.abs(value) / max : 0;
  const isNeg = value < 0;
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 3 }}>
        <span style={{ color: "#8b949e" }}>{label}</span>
        <span style={{ color: isNeg ? "#f85149" : color || "#3fb950", fontWeight: 700 }}>
          {typeof value === "number" ? (Number.isInteger(value) ? value : value.toFixed(4)) : value ?? "—"}
        </span>
      </div>
      <div style={{ background: "#161b22", borderRadius: 3, height: 6, overflow: "hidden" }}>
        <div style={{ width: `${Math.min(100, pct * 100)}%`, height: "100%", background: isNeg ? "#f85149" : color || "#3fb950", borderRadius: 3 }} />
      </div>
    </div>
  );
}

export default function EventImpactAnalysis() {
  const [eventId, setEventId] = useState("impact_001");
  const [ticker, setTicker] = useState("AAPL");
  const [preReturnsStr, setPreReturnsStr] = useState(JSON.stringify(SAMPLE_PRE));
  const [postReturnsStr, setPostReturnsStr] = useState(JSON.stringify(SAMPLE_POST));
  const [gapReturn, setGapReturn] = useState("0.025");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await eventsApi.computeImpact({
        event_id: eventId,
        ticker,
        pre_returns: JSON.parse(preReturnsStr),
        post_returns: JSON.parse(postReturnsStr),
        gap_return: parseFloat(gapReturn) || 0,
      });
      setResult(r.data);
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const maxVal = result
    ? Math.max(Math.abs(result.pre_return), Math.abs(result.post_return), result.volume_spike, result.volatility_spike, 0.1)
    : 1;

  return (
    <div style={{ padding: 24, color: "#f0f6fc", fontFamily: "monospace" }}>
      <div style={{ fontSize: 11, color: "#58a6ff", letterSpacing: "0.1em", marginBottom: 4 }}>M15</div>
      <h1 style={{ margin: "0 0 4px", fontSize: 22 }}>Event Impact Analysis</h1>
      <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 20 }}>Pre/post return attribution, volume spike, volatility, drawdown, momentum persistence</div>

      <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: 16 }}>
        <div style={CARD}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "#58a6ff", marginBottom: 14 }}>Parameters</div>
          {[["Event ID","eventId",setEventId],["Ticker","ticker",setTicker],["Gap Return","gapReturn",setGapReturn]].map(([l,k,set]) => (
            <div key={k} style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>{l}</div>
              <input style={{ ...INPUT, width: "100%" }} value={k === "eventId" ? eventId : k === "ticker" ? ticker : gapReturn}
                onChange={(e) => set(e.target.value)} />
            </div>
          ))}
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>Pre-Event Returns (JSON array)</div>
            <textarea style={{ ...INPUT, width: "100%", height: 60, resize: "vertical", fontSize: 11 }}
              value={preReturnsStr} onChange={(e) => setPreReturnsStr(e.target.value)} />
          </div>
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>Post-Event Returns (JSON array)</div>
            <textarea style={{ ...INPUT, width: "100%", height: 80, resize: "vertical", fontSize: 11 }}
              value={postReturnsStr} onChange={(e) => setPostReturnsStr(e.target.value)} />
          </div>
          {error && <div style={{ color: "#f85149", fontSize: 12, marginBottom: 10 }}>{error}</div>}
          <button style={{ ...BTN(true), width: "100%" }} disabled={loading} onClick={run}>
            {loading ? "Computing…" : "Compute Impact"}
          </button>
        </div>

        <div>
          {!result ? (
            <div style={{ ...CARD, color: "#8b949e" }}>Run the analysis to see impact metrics here.</div>
          ) : (
            <>
              <div style={{ ...CARD, marginBottom: 16 }}>
                <div style={{ fontWeight: 700, color: "#58a6ff", fontSize: 14, marginBottom: 16 }}>
                  Impact: {result.ticker} ({result.event_id})
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                  <div>
                    <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 8 }}>RETURN METRICS</div>
                    <BarChart label="Pre-Event Return" value={result.pre_return} max={maxVal} />
                    <BarChart label="Post-Event Return" value={result.post_return} max={maxVal} color="#3fb950" />
                    <BarChart label="Gap %" value={result.gap_pct} max={maxVal} />
                    <BarChart label="Abnormal Return" value={result.abnormal_return} max={maxVal} color="#e3b341" />
                    <BarChart label="Relative Return" value={result.relative_return} max={maxVal} color="#58a6ff" />
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 8 }}>RISK & LIQUIDITY</div>
                    <BarChart label="Volume Spike" value={result.volume_spike} max={Math.max(result.volume_spike, 3)} color="#e3b341" />
                    <BarChart label="Volatility Spike" value={result.volatility_spike} max={Math.max(result.volatility_spike, 3)} color="#f85149" />
                    <BarChart label="Max Drawdown" value={Math.abs(result.max_drawdown)} max={0.1} color="#f85149" />
                    <BarChart label="Liquidity Change" value={result.liquidity_change} max={1} color="#58a6ff" />
                    <BarChart label="Risk Contribution" value={result.risk_contribution} max={Math.max(result.risk_contribution, 0.1)} color="#e3b341" />
                  </div>
                </div>
              </div>
              <div style={{ ...CARD }}>
                <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 10 }}>MOMENTUM & RECOVERY</div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
                  {[
                    ["Momentum Persistence", `${(result.momentum_persistence * 100).toFixed(1)}%`, result.momentum_persistence > 0.5 ? "#3fb950" : "#f85149"],
                    ["Recovery Days", result.recovery_days ?? "Not recovered", "#58a6ff"],
                  ].map(([l, v, c]) => (
                    <div key={l} style={{ background: "#161b22", borderRadius: 6, padding: "10px 14px" }}>
                      <div style={{ fontSize: 11, color: "#8b949e" }}>{l}</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: c, marginTop: 4 }}>{v}</div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
