import { useState } from "react";
import { useNotificationLogs, useNotificationTemplates, useSendNotification, useCreateTemplate, useDeleteTemplate } from "../hooks/useNotifications";

const S = {
  page: { padding: 24, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" },
  title: { fontSize: 22, fontWeight: 700, marginBottom: 20 },
  grid: { display: "grid", gridTemplateColumns: "340px 1fr", gap: 16 },
  card: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sectionTitle: { fontSize: 11, color: "#8b949e", fontWeight: 700, marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.08em" },
  input: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "8px 12px", color: "#e6edf3", fontSize: 13, width: "100%", outline: "none", marginBottom: 8, boxSizing: "border-box" },
  select: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "8px 12px", color: "#e6edf3", fontSize: 13, width: "100%", outline: "none", marginBottom: 8, boxSizing: "border-box" },
  textarea: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "8px 12px", color: "#e6edf3", fontSize: 12, width: "100%", outline: "none", marginBottom: 8, boxSizing: "border-box", height: 72, resize: "vertical" },
  btn: (c = "#238636") => ({ background: c, border: "none", borderRadius: 6, padding: "8px 16px", color: "#fff", cursor: "pointer", fontSize: 12, fontWeight: 600, marginRight: 6, marginBottom: 6 }),
  tab: (active) => ({ padding: "8px 16px", cursor: "pointer", fontSize: 13, fontWeight: 600, borderBottom: `2px solid ${active ? "#58a6ff" : "transparent"}`, color: active ? "#58a6ff" : "#8b949e", marginBottom: -1 }),
  row: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", padding: "10px 0", borderBottom: "1px solid #21262d" },
  badge: (s) => {
    const colors = { DELIVERED: "#3fb950", FAILED: "#f85149", PENDING: "#d29922", RETRYING: "#79c0ff" };
    return { background: (colors[s] || "#8b949e") + "22", color: colors[s] || "#8b949e", padding: "2px 8px", borderRadius: 10, fontSize: 11, fontWeight: 600 };
  },
  chBadge: (ch) => {
    const c = { EMAIL: "#58a6ff", SLACK: "#3fb950", DISCORD: "#d2a8ff", WEBHOOK: "#f0883e", CONSOLE: "#8b949e" };
    return { background: (c[ch] || "#8b949e") + "22", color: c[ch] || "#8b949e", padding: "2px 6px", borderRadius: 4, fontSize: 10, fontWeight: 600, marginRight: 6 };
  },
};

const CHANNELS = ["CONSOLE", "WEBHOOK", "SLACK", "DISCORD", "EMAIL"];

export default function NotificationCenter() {
  const [tab, setTab] = useState("logs");
  const [channel, setChannel] = useState("CONSOLE");
  const [recipient, setRecipient] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [sendMsg, setSendMsg] = useState("");

  const [tplName, setTplName] = useState("");
  const [tplChannel, setTplChannel] = useState("CONSOLE");
  const [tplSubject, setTplSubject] = useState("");
  const [tplBody, setTplBody] = useState("");
  const [tplMsg, setTplMsg] = useState("");

  const { data: logsData, refetch: refetchLogs } = useNotificationLogs({ limit: 50 });
  const { data: tplData } = useNotificationTemplates({ active_only: false });
  const sendNotification = useSendNotification();
  const createTemplate = useCreateTemplate();
  const deleteTemplate = useDeleteTemplate();

  const logs = logsData?.logs || [];
  const templates = tplData?.templates || [];

  const handleSend = () => {
    if (!recipient.trim() || !body.trim()) return;
    sendNotification.mutate({ channel, recipient: recipient.trim(), subject: subject.trim() || undefined, body: body.trim() }, {
      onSuccess: (r) => { setSendMsg(`Sent — status: ${r.status}`); refetchLogs(); },
      onError: (e) => setSendMsg(`Error: ${e.message}`),
    });
  };

  const handleCreateTpl = () => {
    if (!tplName.trim() || !tplBody.trim()) return;
    createTemplate.mutate({ name: tplName.trim(), channel: tplChannel, subject_template: tplSubject || undefined, body_template: tplBody }, {
      onSuccess: () => { setTplMsg("Template created"); setTplName(""); setTplBody(""); setTplSubject(""); },
      onError: (e) => setTplMsg(`Error: ${e.message}`),
    });
  };

  return (
    <div style={S.page}>
      <div style={S.title}>Notification Center</div>
      <div style={S.grid}>

        {/* Left panel — Send */}
        <div>
          <div style={S.card}>
            <div style={S.sectionTitle}>Send Notification</div>
            <select style={S.select} value={channel} onChange={(e) => setChannel(e.target.value)}>
              {CHANNELS.map((c) => <option key={c}>{c}</option>)}
            </select>
            <input style={S.input} placeholder="Recipient (email, webhook URL, etc.)" value={recipient} onChange={(e) => setRecipient(e.target.value)} />
            <input style={S.input} placeholder="Subject (optional)" value={subject} onChange={(e) => setSubject(e.target.value)} />
            <textarea style={S.textarea} placeholder="Message body" value={body} onChange={(e) => setBody(e.target.value)} />
            <button style={S.btn()} onClick={handleSend} disabled={sendNotification.isPending}>
              {sendNotification.isPending ? "Sending…" : "Send"}
            </button>
            {sendMsg && <div style={{ fontSize: 12, color: sendMsg.startsWith("Error") ? "#f85149" : "#3fb950", marginTop: 6 }}>{sendMsg}</div>}
          </div>

          <div style={S.card}>
            <div style={S.sectionTitle}>Create Template</div>
            <input style={S.input} placeholder="Template name" value={tplName} onChange={(e) => setTplName(e.target.value)} />
            <select style={S.select} value={tplChannel} onChange={(e) => setTplChannel(e.target.value)}>
              {CHANNELS.map((c) => <option key={c}>{c}</option>)}
            </select>
            <input style={S.input} placeholder="Subject template (use $var)" value={tplSubject} onChange={(e) => setTplSubject(e.target.value)} />
            <textarea style={S.textarea} placeholder="Body template (use $variable for substitution)" value={tplBody} onChange={(e) => setTplBody(e.target.value)} />
            <button style={S.btn("#1f6feb")} onClick={handleCreateTpl} disabled={createTemplate.isPending}>
              {createTemplate.isPending ? "Creating…" : "Create Template"}
            </button>
            {tplMsg && <div style={{ fontSize: 12, color: tplMsg.startsWith("Error") ? "#f85149" : "#3fb950", marginTop: 6 }}>{tplMsg}</div>}
          </div>
        </div>

        {/* Right panel — tabs */}
        <div>
          <div style={{ display: "flex", gap: 4, marginBottom: 16, borderBottom: "1px solid #30363d" }}>
            {[["logs", "Delivery Logs"], ["templates", "Templates"]].map(([k, l]) => (
              <div key={k} style={S.tab(tab === k)} onClick={() => setTab(k)}>{l}</div>
            ))}
          </div>

          {tab === "logs" && (
            <div style={S.card}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
                <div style={S.sectionTitle}>Recent Deliveries ({logs.length})</div>
                <button style={S.btn("#21262d")} onClick={refetchLogs}>Refresh</button>
              </div>
              {logs.length === 0 ? (
                <div style={{ color: "#8b949e", fontSize: 13, textAlign: "center", padding: 24 }}>No notifications sent yet.</div>
              ) : logs.map((log) => (
                <div key={log.id} style={S.row}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                      <span style={S.chBadge(log.channel)}>{log.channel}</span>
                      <span style={{ fontSize: 12, color: "#e6edf3", fontWeight: 600 }}>{log.recipient}</span>
                    </div>
                    {log.subject && <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 2 }}>{log.subject}</div>}
                    <div style={{ fontSize: 11, color: "#6e7681" }}>{log.body?.substring(0, 80)}{log.body?.length > 80 ? "…" : ""}</div>
                    <div style={{ fontSize: 10, color: "#484f58", marginTop: 4 }}>{log.created_at?.substring(0, 19)}</div>
                  </div>
                  <span style={S.badge(log.status)}>{log.status}</span>
                </div>
              ))}
            </div>
          )}

          {tab === "templates" && (
            <div style={S.card}>
              <div style={S.sectionTitle}>Templates ({templates.length})</div>
              {templates.length === 0 ? (
                <div style={{ color: "#8b949e", fontSize: 13, textAlign: "center", padding: 24 }}>No templates yet.</div>
              ) : templates.map((tpl) => (
                <div key={tpl.id} style={S.row}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                      <span style={S.chBadge(tpl.channel)}>{tpl.channel}</span>
                      <span style={{ fontSize: 13, fontWeight: 700, color: "#e6edf3" }}>{tpl.name}</span>
                      {!tpl.is_active && <span style={{ fontSize: 10, color: "#f85149" }}>INACTIVE</span>}
                    </div>
                    {tpl.subject_template && <div style={{ fontSize: 12, color: "#8b949e" }}>Subject: {tpl.subject_template}</div>}
                    <div style={{ fontSize: 11, color: "#6e7681" }}>{tpl.body_template?.substring(0, 100)}</div>
                  </div>
                  <button
                    style={{ background: "#b91c1c22", border: "1px solid #f85149", borderRadius: 4, padding: "3px 10px", color: "#f85149", cursor: "pointer", fontSize: 11 }}
                    onClick={() => deleteTemplate.mutate(tpl.id)}
                  >Del</button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
