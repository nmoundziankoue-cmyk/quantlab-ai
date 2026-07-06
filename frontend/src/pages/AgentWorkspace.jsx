import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";

const API = "";
const card = { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20 };
const AGENT_COLORS = {
  macro_economist: "#58a6ff",
  equity_researcher: "#3fb950",
  options_strategist: "#d29922",
  portfolio_manager: "#a371f7",
  risk_officer: "#f85149",
  quant_researcher: "#79c0ff",
  news_analyst: "#56d364",
};

export default function AgentWorkspace() {
  const qc = useQueryClient();
  const [topic, setTopic] = useState("");
  const [tickers, setTickers] = useState("AAPL");
  const [query, setQuery] = useState("");
  const [activeSession, setActiveSession] = useState(null);

  const { data: agentList } = useQuery({
    queryKey: ["agents-list"],
    queryFn: () => axios.get(`${API}/agents/research/agents`).then(r => r.data),
  });

  const { data: sessions } = useQuery({
    queryKey: ["agent-sessions"],
    queryFn: () => axios.get(`${API}/agents/research/sessions`).then(r => r.data),
    refetchInterval: 10000,
  });

  const { data: sessionDetail } = useQuery({
    queryKey: ["agent-session", activeSession],
    queryFn: () => axios.get(`${API}/agents/research/sessions/${activeSession}`).then(r => r.data),
    enabled: !!activeSession,
    refetchInterval: 5000,
  });

  const { data: synthesis } = useQuery({
    queryKey: ["agent-synthesis", activeSession],
    queryFn: () => axios.get(`${API}/agents/research/sessions/${activeSession}/synthesis`).then(r => r.data),
    enabled: !!activeSession && (sessionDetail?.response_count ?? 0) > 0,
  });

  const createSession = useMutation({
    mutationFn: () => axios.post(`${API}/agents/research/sessions`, {
      topic, tickers: tickers.split(",").map(t => t.trim().toUpperCase()),
    }).then(r => r.data),
    onSuccess: (data) => { setActiveSession(data.id); qc.invalidateQueries({ queryKey: ["agent-sessions"] }); },
  });

  const runAll = useMutation({
    mutationFn: () => axios.post(`${API}/agents/research/sessions/${activeSession}/query/all`, { query }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agent-session", activeSession] }),
  });

  return (
    <div style={{ padding: 28, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Agent Workspace</h1>
        <p style={{ color: "#8b949e", margin: "4px 0 0", fontSize: 13 }}>Multi-agent AI research — 7 specialized analysts</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 20 }}>
        {/* Left: sessions + new */}
        <div>
          <div style={{ ...card, marginBottom: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>New Research Session</div>
            <input value={topic} onChange={e => setTopic(e.target.value)} placeholder="Research topic…"
              style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "8px 10px", fontSize: 13, width: "100%", boxSizing: "border-box", marginBottom: 8 }} />
            <input value={tickers} onChange={e => setTickers(e.target.value)} placeholder="Tickers (CSV)…"
              style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "8px 10px", fontSize: 13, width: "100%", boxSizing: "border-box", marginBottom: 10 }} />
            <button onClick={() => createSession.mutate()} disabled={!topic || createSession.isPending}
              style={{ background: "#238636", border: "none", borderRadius: 6, color: "#fff", padding: "8px 14px", cursor: "pointer", fontSize: 13, width: "100%" }}>
              {createSession.isPending ? "Creating…" : "Create Session"}
            </button>
          </div>

          <div style={card}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>Sessions</div>
            {(sessions?.sessions ?? []).map(s => (
              <div key={s.id} onClick={() => setActiveSession(s.id)}
                style={{ padding: "8px 10px", borderRadius: 6, cursor: "pointer", marginBottom: 4, background: activeSession === s.id ? "#1f3a1f" : "transparent", border: activeSession === s.id ? "1px solid #3fb950" : "1px solid transparent" }}>
                <div style={{ fontSize: 13, fontWeight: 500, color: "#e6edf3" }}>{s.topic?.slice(0, 30) || "Untitled"}</div>
                <div style={{ fontSize: 11, color: "#8b949e" }}>{s.message_count} messages</div>
              </div>
            ))}
            {!sessions?.sessions?.length && <div style={{ color: "#8b949e", fontSize: 12 }}>No sessions yet</div>}
          </div>
        </div>

        {/* Right: active session */}
        <div>
          {activeSession ? (
            <>
              <div style={{ ...card, marginBottom: 16 }}>
                <div style={{ display: "flex", gap: 8 }}>
                  <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Research query…"
                    style={{ flex: 1, background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "8px 12px", fontSize: 13 }} />
                  <button onClick={() => runAll.mutate()} disabled={!query || runAll.isPending}
                    style={{ background: "#1f6feb", border: "none", borderRadius: 6, color: "#fff", padding: "8px 16px", cursor: "pointer", fontSize: 13 }}>
                    {runAll.isPending ? "Running…" : "Ask All Agents"}
                  </button>
                </div>
              </div>

              {/* Agent responses */}
              {(sessionDetail?.messages ?? []).filter(m => m.role === "agent").map((m, i) => (
                <div key={i} style={{ ...card, marginBottom: 12, borderLeft: `3px solid ${AGENT_COLORS[m.agent_type] ?? "#8b949e"}` }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: AGENT_COLORS[m.agent_type] ?? "#8b949e", textTransform: "uppercase", letterSpacing: 1 }}>
                      {m.agent_type?.replace(/_/g, " ")}
                    </span>
                    <span style={{ fontSize: 11, color: "#8b949e" }}>Confidence: {((m.confidence ?? 0) * 100).toFixed(0)}%</span>
                  </div>
                  <div style={{ fontSize: 13, color: "#c9d1d9", lineHeight: 1.6 }}>{m.content}</div>
                </div>
              ))}

              {synthesis && (
                <div style={{ ...card, borderLeft: "3px solid #a371f7" }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: "#a371f7", marginBottom: 8 }}>SYNTHESIS</div>
                  <div style={{ fontSize: 14, color: "#e6edf3", fontWeight: 600, marginBottom: 8 }}>{synthesis.recommendation}</div>
                  <div style={{ fontSize: 12, color: "#8b949e" }}>
                    Consensus confidence: {((synthesis.consensus_confidence ?? 0) * 100).toFixed(0)}% from {synthesis.agent_count} agents
                  </div>
                </div>
              )}
            </>
          ) : (
            <div style={{ ...card, textAlign: "center", padding: 80, color: "#8b949e" }}>
              Create or select a session to start researching
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
