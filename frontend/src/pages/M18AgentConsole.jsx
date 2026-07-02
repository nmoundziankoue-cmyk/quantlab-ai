import { useState, useEffect } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 18, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 18, marginBottom: 14 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#ff9f43", marginBottom: 12 },
  row2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 },
  btn: (c="#ff9f43") => ({ background: c + "22", border: `1px solid ${c}55`, borderRadius: 6, padding: "7px 16px", color: c, fontSize: 12, cursor: "pointer", fontFamily: "monospace", marginRight: 6 }),
  badge: (c) => ({ display: "inline-block", fontSize: 10, padding: "1px 6px", borderRadius: 4, background: c + "22", color: c, fontWeight: 700, marginRight: 4 }),
  agentCard: (c="#ff9f43") => ({ background: "#0d1117", border: `1px solid ${c}33`, borderRadius: 8, padding: "12px 16px", cursor: "pointer" }),
  result: { background: "#161b22", borderRadius: 8, padding: 16, marginTop: 14 },
  kv: { display: "flex", justifyContent: "space-between", padding: "3px 0", borderBottom: "1px solid #21262d33", fontSize: 12 },
};

const AGENTS = [
  { type: "MARKET_ANALYST", color: "#58a6ff", desc: "Market trend & momentum" },
  { type: "RISK_MONITOR", color: "#ff7b72", desc: "Portfolio risk flags" },
  { type: "PORTFOLIO_OPTIMIZER", color: "#a371f7", desc: "Rebalancing recommendations" },
  { type: "NEWS_SCOUT", color: "#56d364", desc: "News sentiment signals" },
  { type: "EARNINGS_WATCHER", color: "#d2a8ff", desc: "Earnings event signals" },
  { type: "MACRO_STRATEGIST", color: "#79c0ff", desc: "Macro environment score" },
  { type: "TECHNICAL_ANALYST", color: "#e3b341", desc: "Technical indicator signals" },
  { type: "EXECUTION_ADVISOR", color: "#ffa657", desc: "Optimal execution strategy" },
  { type: "COMPLIANCE_GUARD", color: "#f0883e", desc: "Compliance rule checks" },
  { type: "REPORT_GENERATOR", color: "#48dbfb", desc: "Consolidated research report" },
];

const SAMPLE_PAYLOADS = {
  MARKET_ANALYST: { ticker: "AAPL", price: 175.50, sma_20: 172.30, rsi_14: 58.5, volume_ratio: 1.3 },
  RISK_MONITOR: { var_95_pct: 0.015, gross_leverage: 1.5, concentration_hhi: 0.12, margin_usage_pct: 0.35, max_drawdown: 0.06 },
  PORTFOLIO_OPTIMIZER: { current_weights: { AAPL: 0.20, MSFT: 0.18 }, target_weights: { AAPL: 0.15, MSFT: 0.20 }, portfolio_sharpe: 1.2, nav: 10000000 },
  NEWS_SCOUT: { ticker: "AAPL", avg_sentiment_score: 0.35, article_count: 12, positive_count: 9, negative_count: 2, trend: "IMPROVING" },
  EARNINGS_WATCHER: { ticker: "AAPL", eps_surprise_pct: 0.08, revenue_surprise_pct: 0.07, guidance_direction: "RAISED", beat_rate: 0.87, post_drift_avg: 0.035 },
  MACRO_STRATEGIST: { gdp_growth: 0.028, inflation: 0.032, yield_spread_2s10s: 0.008, recession_prob_12m: 0.12, pmi: 52.4 },
  TECHNICAL_ANALYST: { ticker: "AAPL", rsi: 58.5, macd: 1.2, macd_signal: 0.8, atr: 2.5, price: 175.50, bollinger_upper: 180, bollinger_lower: 168, volume_ratio: 1.3 },
  EXECUTION_ADVISOR: { ticker: "AAPL", side: "BUY", quantity: 5000, adv: 8000000, volatility: 0.22, urgency: "MEDIUM" },
  COMPLIANCE_GUARD: { ticker: "AAPL", position_pct: 0.08, sector_concentration_pct: 0.25, gross_leverage: 1.5, num_positions: 22, is_restricted: false },
  REPORT_GENERATOR: { ticker: "AAPL", agent_results: [] },
};

export default function M18AgentConsole() {
  const [agents, setAgents] = useState([]);
  const [selected, setSelected] = useState(null);
  const [result, setResult] = useState(null);
  const [orchResult, setOrchResult] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch("/m18/agents/list").then(r => r.json()).then(setAgents).catch(() => {});
  }, []);

  const runAgent = async (type) => {
    setSelected(type);
    setLoading(true);
    const r = await fetch("/m18/agents/run", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ agent_type: type, payload: SAMPLE_PAYLOADS[type] || {} }),
    });
    if (r.ok) setResult(await r.json());
    setLoading(false);
  };

  const runAll = async () => {
    setLoading(true);
    const payloads = {};
    AGENTS.filter(a => a.type !== "REPORT_GENERATOR").forEach(a => { payloads[a.type] = SAMPLE_PAYLOADS[a.type]; });
    const r = await fetch("/m18/agents/run-all", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ payloads, include_report: true }),
    });
    if (r.ok) setOrchResult(await r.json());
    setLoading(false);
    setResult(null);
  };

  const actionColor = { BUY: "#3fb950", SELL: "#ff7b72", HOLD: "#8b949e", REDUCE: "#f0883e", HEDGE: "#e3b341", REBALANCE: "#a371f7", REVIEW: "#ffa657", ALERT: "#ff7b72", NO_ACTION: "#8b949e" };

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>AI Agent Console — 10 Autonomous Agents</div>

      <div style={{ marginBottom: 14 }}>
        <button style={S.btn()} onClick={runAll} disabled={loading}>{loading ? "Running…" : "Run All Agents"}</button>
        <span style={{ fontSize: 11, color: "#8b949e" }}>Runs all 9 specialist agents + Report Generator</span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 10, marginBottom: 16 }}>
        {AGENTS.map(a => (
          <div key={a.type} style={S.agentCard(a.color)} onClick={() => runAgent(a.type)}>
            <div style={{ fontSize: 11, fontWeight: 700, color: a.color, marginBottom: 4 }}>{a.type.replace(/_/g, " ")}</div>
            <div style={{ fontSize: 10, color: "#8b949e" }}>{a.desc}</div>
            {selected === a.type && loading && <div style={{ fontSize: 10, color: "#e3b341", marginTop: 4 }}>Running…</div>}
          </div>
        ))}
      </div>

      {result && (
        <div style={S.section}>
          <div style={S.sHdr}>{result.agent_type?.replace(/_/g, " ")} Result</div>
          <div style={S.result}>
            <div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
              <span style={S.badge(actionColor[result.action] || "#8b949e")}>{result.action}</span>
              <span style={{ fontSize: 12, color: "#8b949e" }}>Confidence: {(result.confidence * 100).toFixed(1)}%</span>
              <span style={{ fontSize: 12, color: "#8b949e" }}>{result.duration_ms?.toFixed(0)}ms</span>
            </div>
            <div style={{ fontSize: 12, color: "#c9d1d9", marginBottom: 10 }}>{result.summary}</div>
            {result.recommendations?.length > 0 && (
              <div style={{ marginBottom: 8 }}>
                {result.recommendations.map((r, i) => <div key={i} style={{ fontSize: 11, color: "#8b949e", marginBottom: 2 }}>• {r}</div>)}
              </div>
            )}
            {result.risk_flags?.length > 0 && result.risk_flags.map((f, i) => (
              <div key={i} style={{ fontSize: 11, color: "#ff7b72", marginBottom: 2 }}>⚠ {f}</div>
            ))}
          </div>
        </div>
      )}

      {orchResult && (
        <div style={S.section}>
          <div style={S.sHdr}>Orchestration Result — {orchResult.agent_results ? Object.keys(orchResult.agent_results).length : 0} agents</div>
          <div style={{ display: "flex", gap: 12, marginBottom: 14, flexWrap: "wrap" }}>
            <div style={{ background: "#161b22", borderRadius: 6, padding: "8px 14px" }}>
              <div style={{ fontSize: 10, color: "#8b949e" }}>Consensus</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: actionColor[orchResult.consensus_action] || "#8b949e" }}>{orchResult.consensus_action}</div>
            </div>
            <div style={{ background: "#161b22", borderRadius: 6, padding: "8px 14px" }}>
              <div style={{ fontSize: 10, color: "#8b949e" }}>Confidence</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: "#f0f6fc" }}>{(orchResult.consensus_confidence * 100).toFixed(1)}%</div>
            </div>
            <div style={{ background: "#161b22", borderRadius: 6, padding: "8px 14px" }}>
              <div style={{ fontSize: 10, color: "#8b949e" }}>Duration</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: "#f0f6fc" }}>{orchResult.total_duration_ms?.toFixed(0)}ms</div>
            </div>
          </div>
          {orchResult.agent_results && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 8 }}>
              {Object.entries(orchResult.agent_results).map(([type, r]) => (
                <div key={type} style={{ background: "#161b22", borderRadius: 6, padding: "8px 10px" }}>
                  <div style={{ fontSize: 10, color: "#8b949e", marginBottom: 4 }}>{type.replace(/_/g, " ")}</div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: actionColor[r.action] || "#8b949e" }}>{r.action}</div>
                  <div style={{ fontSize: 10, color: "#8b949e" }}>{(r.confidence * 100).toFixed(0)}%</div>
                </div>
              ))}
            </div>
          )}
          {orchResult.agent_results?.REPORT_GENERATOR?.data?.report && (
            <div style={{ marginTop: 14, background: "#010409", borderRadius: 6, padding: 12, fontSize: 11, color: "#7ee787", whiteSpace: "pre-wrap", maxHeight: 300, overflow: "auto" }}>
              {orchResult.agent_results.REPORT_GENERATOR.data.report}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
