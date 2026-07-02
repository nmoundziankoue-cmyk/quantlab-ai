import { useState } from "react";
import { useAgents, useRunAgent, useRunWorkflow } from "../hooks/useAgents";

const S = {
  page: { padding: 24, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" },
  title: { fontSize: 22, fontWeight: 700, marginBottom: 20 },
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 12, marginBottom: 24 },
  card: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20 },
  cardTitle: { fontSize: 13, color: "#8b949e", fontWeight: 600, marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.05em" },
  agentCard: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 16, cursor: "pointer", transition: "border-color 0.1s" },
  agentCardActive: { background: "#161b22", border: "1px solid #1f6feb", borderRadius: 8, padding: 16, cursor: "pointer", boxShadow: "0 0 0 1px #1f6feb" },
  agentName: { fontSize: 14, fontWeight: 700, marginBottom: 4 },
  agentCategory: { fontSize: 11, color: "#8b949e", marginBottom: 8 },
  capItem: { fontSize: 11, color: "#58a6ff", background: "#1c2128", borderRadius: 4, padding: "2px 6px", marginRight: 4, marginBottom: 4, display: "inline-block" },
  input: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "8px 12px", color: "#e6edf3", fontSize: 13, width: "100%", outline: "none", marginBottom: 8, boxSizing: "border-box" },
  btn: (color = "#238636") => ({ background: color, border: "none", borderRadius: 6, padding: "8px 16px", color: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 600, marginRight: 8 }),
  resultBox: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: 16, marginTop: 16, fontSize: 13, lineHeight: 1.6, color: "#e6edf3", maxHeight: 500, overflowY: "auto" },
  resultKey: { color: "#58a6ff", fontWeight: 600 },
};

const CATEGORY_COLORS = {
  MARKET: "#58a6ff", MACRO: "#a5d6ff", FUNDAMENTAL: "#3fb950",
  TECHNICAL: "#f0883e", PORTFOLIO: "#d2a8ff", RISK: "#f85149",
  NEWS: "#79c0ff", EARNINGS: "#56d364", SECTOR: "#ffa657",
  OPTIONS: "#ff7b72", CRYPTO: "#f8f9fa", ORCHESTRATION: "#d2a8ff",
};

function ResultTree({ data, depth = 0 }) {
  if (!data || typeof data !== "object") return <span style={{ color: "#3fb950" }}>{String(data)}</span>;
  return (
    <div style={{ marginLeft: depth * 12 }}>
      {Object.entries(data).map(([k, v]) => (
        <div key={k} style={{ marginBottom: 4 }}>
          <span style={S.resultKey}>{k}: </span>
          {Array.isArray(v) ? (
            <span style={{ color: "#8b949e" }}>[{v.slice(0, 5).join(", ")}{v.length > 5 ? `... +${v.length - 5}` : ""}]</span>
          ) : typeof v === "object" && v !== null ? (
            <ResultTree data={v} depth={depth + 1} />
          ) : (
            <span style={{ color: "#e6edf3" }}>{String(v)}</span>
          )}
        </div>
      ))}
    </div>
  );
}

export default function AgentDashboard() {
  const { data: agents = [] } = useAgents();
  const runAgent = useRunAgent();
  const runWorkflow = useRunWorkflow();

  const [selectedAgentId, setSelectedAgentId] = useState(null);
  const [ticker, setTicker] = useState("AAPL");
  const [workflowTickers, setWorkflowTickers] = useState("AAPL,MSFT,NVDA");
  const [singleResult, setSingleResult] = useState(null);
  const [workflowResult, setWorkflowResult] = useState(null);
  const [activeTab, setActiveTab] = useState("agents");

  const selectedAgent = agents.find((a) => a.id === selectedAgentId);

  const handleRunAgent = () => {
    if (!selectedAgentId) return;
    runAgent.mutate({ agent_id: selectedAgentId, ticker }, { onSuccess: setSingleResult });
  };

  const handleRunWorkflow = () => {
    const tickers = workflowTickers.split(",").map((t) => t.trim().toUpperCase()).filter(Boolean);
    const agentIds = agents.filter((a) => a.id !== "research_coordinator").map((a) => a.id);
    runWorkflow.mutate({ tickers, agent_ids: agentIds.slice(0, 5) }, { onSuccess: setWorkflowResult });
  };

  const tabs = [{ k: "agents", l: "Agents" }, { k: "workflow", l: "Multi-Agent Workflow" }];

  return (
    <div style={S.page}>
      <div style={S.title}>AI Agent Framework</div>

      <div style={{ display: "flex", gap: 4, marginBottom: 20, borderBottom: "1px solid #30363d" }}>
        {tabs.map(({ k, l }) => (
          <div key={k} style={{ padding: "8px 16px", cursor: "pointer", fontSize: 13, fontWeight: 600, borderBottom: `2px solid ${activeTab === k ? "#58a6ff" : "transparent"}`, color: activeTab === k ? "#58a6ff" : "#8b949e", marginBottom: -1 }} onClick={() => setActiveTab(k)}>{l}</div>
        ))}
      </div>

      {activeTab === "agents" && (
        <>
          <div style={S.grid}>
            {agents.map((agent) => (
              <div key={agent.id}
                style={agent.id === selectedAgentId ? S.agentCardActive : S.agentCard}
                onClick={() => setSelectedAgentId(agent.id)}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div style={S.agentName}>{agent.name}</div>
                  <span style={{ ...S.capItem, background: (CATEGORY_COLORS[agent.category] || "#1c2128") + "22", color: CATEGORY_COLORS[agent.category] || "#8b949e" }}>{agent.category}</span>
                </div>
                <div style={S.agentCategory}>{agent.id}</div>
                <div>
                  {(agent.capabilities || []).slice(0, 3).map((c) => (
                    <span key={c} style={S.capItem}>{c}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {selectedAgent && (
            <div style={S.card}>
              <div style={S.cardTitle}>Run: {selectedAgent.name}</div>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <input style={{ ...S.input, marginBottom: 0, flex: 1 }} placeholder="Ticker (e.g. AAPL)" value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} />
                <button style={S.btn()} onClick={handleRunAgent} disabled={runAgent.isPending}>{runAgent.isPending ? "Running..." : "Run Agent"}</button>
              </div>
              {singleResult && (
                <div style={S.resultBox}>
                  <ResultTree data={singleResult} />
                </div>
              )}
            </div>
          )}
        </>
      )}

      {activeTab === "workflow" && (
        <div style={S.card}>
          <div style={S.cardTitle}>Multi-Agent Research Workflow</div>
          <div style={{ fontSize: 13, color: "#8b949e", marginBottom: 12 }}>
            Run all specialized agents on multiple tickers simultaneously. The research coordinator synthesizes findings.
          </div>
          <input style={S.input} placeholder="Tickers (comma-separated, max 10)" value={workflowTickers} onChange={(e) => setWorkflowTickers(e.target.value.toUpperCase())} />
          <button style={S.btn()} onClick={handleRunWorkflow} disabled={runWorkflow.isPending}>
            {runWorkflow.isPending ? "Running workflow..." : "Launch Multi-Agent Workflow"}
          </button>

          {workflowResult && (
            <div>
              <div style={{ fontSize: 13, color: "#3fb950", marginTop: 12, marginBottom: 8 }}>{workflowResult.summary}</div>
              {Object.entries(workflowResult.results || {}).map(([t, agentResults]) => (
                <div key={t} style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 14, fontWeight: 700, color: "#58a6ff", marginBottom: 8 }}>{t}</div>
                  {Object.entries(agentResults).map(([agentId, result]) => (
                    <div key={agentId} style={{ background: "#0d1117", border: "1px solid #21262d", borderRadius: 6, padding: 12, marginBottom: 6 }}>
                      <div style={{ fontSize: 12, fontWeight: 700, color: "#8b949e", marginBottom: 4 }}>{agentId.replace(/_/g, " ").toUpperCase()}</div>
                      <ResultTree data={result} />
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
