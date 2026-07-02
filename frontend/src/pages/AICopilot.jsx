import { useState, useRef, useEffect } from "react";
import { useCopilotSessions, useCreateCopilotSession, useCopilotSession, useSendMessage, useGenerateThesis, useGenerateMemo, usePromptTemplates } from "../hooks/useAICopilot";
import useCopilotStore from "../store/useCopilotStore";

const S = {
  page: { display: "flex", height: "100vh", background: "#0d1117", color: "#e6edf3" },
  sidebar: { width: 260, background: "#161b22", borderRight: "1px solid #30363d", display: "flex", flexDirection: "column" },
  sideTop: { padding: "16px", borderBottom: "1px solid #30363d" },
  sessionList: { flex: 1, overflowY: "auto", padding: 8 },
  sessionItem: (active) => ({ padding: "10px 12px", borderRadius: 6, cursor: "pointer", marginBottom: 4, background: active ? "#21262d" : "transparent", color: active ? "#e6edf3" : "#8b949e", fontSize: 13, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }),
  main: { flex: 1, display: "flex", flexDirection: "column" },
  header: { padding: "16px 20px", borderBottom: "1px solid #30363d", display: "flex", gap: 12, alignItems: "center" },
  messages: { flex: 1, overflowY: "auto", padding: 20 },
  bubble: (role) => ({ maxWidth: "75%", padding: "12px 16px", borderRadius: 12, marginBottom: 12, fontSize: 14, lineHeight: 1.6, alignSelf: role === "user" ? "flex-end" : "flex-start", background: role === "user" ? "#1f6feb" : "#21262d", color: "#e6edf3", whiteSpace: "pre-wrap" }),
  bubbleWrap: (role) => ({ display: "flex", justifyContent: role === "user" ? "flex-end" : "flex-start" }),
  inputRow: { padding: 16, borderTop: "1px solid #30363d", display: "flex", gap: 8 },
  input: { flex: 1, background: "#21262d", border: "1px solid #30363d", borderRadius: 8, padding: "10px 14px", color: "#e6edf3", fontSize: 14, outline: "none", resize: "none" },
  btn: (color = "#238636") => ({ background: color, border: "none", borderRadius: 6, padding: "8px 14px", color: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 600, whiteSpace: "nowrap" }),
  genPanel: { padding: 20, background: "#161b22", borderLeft: "1px solid #30363d", width: 280, overflowY: "auto" },
  genTitle: { fontSize: 13, fontWeight: 700, marginBottom: 12, color: "#8b949e", textTransform: "uppercase", letterSpacing: "0.05em" },
  smallInput: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "7px 10px", color: "#e6edf3", fontSize: 13, width: "100%", outline: "none", marginBottom: 8 },
};

function ChatPanel({ sessionId }) {
  const { data: session } = useCopilotSession(sessionId);
  const sendMessage = useSendMessage(sessionId);
  const [msg, setMsg] = useState("");
  const bottomRef = useRef();

  const messages = session?.messages || [];

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages.length]);

  const handleSend = () => {
    if (!msg.trim()) return;
    sendMessage.mutate({ content: msg });
    setMsg("");
  };

  return (
    <>
      <div style={S.messages}>
        {messages.length === 0 && (
          <div style={{ color: "#8b949e", fontSize: 14, textAlign: "center", marginTop: 60 }}>
            Ask me anything about a company, ticker, or research topic.
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} style={S.bubbleWrap(m.role)}>
            <div style={S.bubble(m.role)}>{m.content}</div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <div style={S.inputRow}>
        <textarea
          style={S.input}
          rows={2}
          placeholder="Ask a research question... (e.g. 'Bull case for AAPL', 'SWOT for MSFT')"
          value={msg}
          onChange={(e) => setMsg(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
        />
        <button style={S.btn()} onClick={handleSend} disabled={sendMessage.isPending}>
          {sendMessage.isPending ? "..." : "Send"}
        </button>
      </div>
    </>
  );
}

function GenerationPanel() {
  const [ticker, setTicker] = useState("AAPL");
  const genThesis = useGenerateThesis();
  const genMemo = useGenerateMemo();
  const { data: templates = [] } = usePromptTemplates();
  const [output, setOutput] = useState("");

  return (
    <div style={S.genPanel}>
      <div style={S.genTitle}>Generate</div>
      <input style={S.smallInput} placeholder="Ticker (e.g. AAPL)" value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} />
      <button style={{ ...S.btn("#1f6feb"), marginBottom: 8, width: "100%" }} onClick={() => genThesis.mutate({ ticker }, { onSuccess: (r) => setOutput(r.content || "") })}>
        Investment Thesis
      </button>
      <button style={{ ...S.btn("#2d333b"), marginBottom: 16, width: "100%", border: "1px solid #30363d" }} onClick={() => genMemo.mutate({ ticker }, { onSuccess: (r) => setOutput(r.content || "") })}>
        Research Memo
      </button>
      {output && (
        <div style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: 12, fontSize: 12, color: "#e6edf3", whiteSpace: "pre-wrap", maxHeight: 400, overflowY: "auto", lineHeight: 1.6 }}>
          {output}
        </div>
      )}
      {templates.length > 0 && (
        <>
          <div style={{ ...S.genTitle, marginTop: 16 }}>Templates ({templates.length})</div>
          {templates.slice(0, 6).map((t) => (
            <div key={t.key || t.id} style={{ fontSize: 12, color: "#8b949e", padding: "4px 0", borderBottom: "1px solid #21262d" }}>{t.name}</div>
          ))}
        </>
      )}
    </div>
  );
}

export default function AICopilot() {
  const { data: sessions = [] } = useCopilotSessions();
  const createSession = useCreateCopilotSession();
  const { activeSessionId, setActiveSessionId } = useCopilotStore();

  const handleNewSession = () => {
    createSession.mutate({ title: `Session ${sessions.length + 1}` }, { onSuccess: (s) => setActiveSessionId(s.id) });
  };

  return (
    <div style={S.page}>
      <div style={S.sidebar}>
        <div style={S.sideTop}>
          <div style={{ fontWeight: 700, fontSize: 16, color: "#e6edf3", marginBottom: 12 }}>AI Research Copilot</div>
          <button style={{ ...S.btn(), width: "100%" }} onClick={handleNewSession}>+ New Session</button>
        </div>
        <div style={S.sessionList}>
          {sessions.map((s) => (
            <div key={s.id} style={S.sessionItem(s.id === activeSessionId)} onClick={() => setActiveSessionId(s.id)}>
              {s.title}
            </div>
          ))}
        </div>
      </div>
      <div style={S.main}>
        <div style={S.header}>
          <span style={{ fontSize: 14, color: "#8b949e" }}>
            {activeSessionId ? "Active research session" : "Select or create a session"}
          </span>
        </div>
        {activeSessionId ? <ChatPanel sessionId={activeSessionId} /> : (
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#8b949e", fontSize: 14 }}>
            Start a new session or select one from the sidebar
          </div>
        )}
      </div>
      <GenerationPanel />
    </div>
  );
}
