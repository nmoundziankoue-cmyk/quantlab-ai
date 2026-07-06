import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as authApi from "../api/authEnterpriseApi";
import * as sysApi from "../api/systemApi";

const S = {
  page: { padding: 24, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" },
  title: { fontSize: 22, fontWeight: 700, marginBottom: 20 },
  grid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 },
  card: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sectionTitle: { fontSize: 11, color: "#8b949e", fontWeight: 700, marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.08em" },
  row: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid #21262d" },
  label: { fontSize: 13, color: "#8b949e" },
  value: { fontSize: 13, color: "#e6edf3", fontWeight: 600 },
  input: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "8px 12px", color: "#e6edf3", fontSize: 13, width: "100%", outline: "none", marginBottom: 8, boxSizing: "border-box" },
  btn: (c = "#238636") => ({ background: c, border: "none", borderRadius: 6, padding: "7px 14px", color: "#fff", cursor: "pointer", fontSize: 12, fontWeight: 600, marginRight: 6, marginBottom: 4 }),
  statusDot: (ok) => ({ width: 8, height: 8, borderRadius: "50%", background: ok ? "#3fb950" : "#f85149", display: "inline-block", marginRight: 6 }),
};

function HealthPanel() {
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["system-health"], queryFn: sysApi.getSystemHealth, refetchInterval: 30000, retry: 1 });
  const { data: info } = useQuery({ queryKey: ["system-info"], queryFn: sysApi.getSystemInfo, retry: 1 });

  if (isLoading) return <div style={{ color: "#8b949e", padding: 16 }}>Checking system health…</div>;

  if (isError || !data) return (
    <div style={S.card}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div style={S.sectionTitle}>System Health</div>
        <button style={S.btn("#21262d")} onClick={refetch}>Refresh</button>
      </div>
      <div style={{ color: "#8b949e", fontSize: 13, padding: "8px 0" }}>Backend not reachable — health data unavailable.</div>
    </div>
  );

  const components = data?.components || {};
  const overall = data?.status || "unknown";

  return (
    <div style={S.card}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div style={S.sectionTitle}>System Health</div>
        <button style={S.btn("#21262d")} onClick={refetch}>Refresh</button>
      </div>

      <div style={S.row}>
        <span style={S.label}>Overall</span>
        <span style={{ ...S.value, color: overall === "ok" ? "#3fb950" : "#f85149" }}>{overall.toUpperCase()}</span>
      </div>
      <div style={S.row}>
        <span style={S.label}>Uptime</span>
        <span style={S.value}>{data?.uptime_s ? `${Math.floor(data.uptime_s / 60)}m ${Math.floor(data.uptime_s % 60)}s` : "—"}</span>
      </div>
      {info && (
        <>
          <div style={S.row}>
            <span style={S.label}>Version</span>
            <span style={S.value}>{info.version}</span>
          </div>
          <div style={S.row}>
            <span style={S.label}>Milestone</span>
            <span style={{ ...S.value, color: "#58a6ff" }}>{info.milestone}</span>
          </div>
        </>
      )}

      <div style={{ marginTop: 12 }}>
        <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.06em" }}>Components</div>
        {Object.entries(components).map(([name, comp]) => (
          <div key={name} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0" }}>
            <span style={{ display: "flex", alignItems: "center", fontSize: 13 }}>
              <span style={S.statusDot(comp.status === "ok")} />
              {name}
            </span>
            <span style={{ fontSize: 11, color: comp.status === "ok" ? "#3fb950" : "#f85149" }}>
              {comp.backend || comp.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SessionsPanel() {
  const [token] = useState(() => localStorage.getItem("access_token") || "");
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["sessions"],
    queryFn: () => authApi.listSessions(token),
    enabled: !!token,
  });
  const [revoking, setRevoking] = useState(null);

  const sessions = data?.sessions || [];

  const handleRevoke = async (sessionId) => {
    setRevoking(sessionId);
    try {
      await authApi.revokeSession(sessionId, token);
      refetch();
    } catch (e) {
      alert("Failed to revoke session: " + e.message);
    } finally {
      setRevoking(null);
    }
  };

  if (!token) return (
    <div style={S.card}>
      <div style={S.sectionTitle}>Active Sessions</div>
      <div style={{ color: "#8b949e", fontSize: 13, padding: "12px 0" }}>Log in to view sessions.</div>
    </div>
  );

  return (
    <div style={S.card}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div style={S.sectionTitle}>Active Sessions ({sessions.length})</div>
        <button style={S.btn("#21262d")} onClick={refetch}>Refresh</button>
      </div>
      {isLoading ? <div style={{ color: "#8b949e" }}>Loading…</div> :
        sessions.length === 0 ? <div style={{ color: "#8b949e", fontSize: 13 }}>No active sessions.</div> :
          sessions.map((s) => (
            <div key={s.id} style={S.row}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#e6edf3" }}>{s.device_name || "Unknown Device"}</div>
                <div style={{ fontSize: 11, color: "#8b949e" }}>{s.ip_address} · {s.last_used_at?.substring(0, 16)}</div>
              </div>
              <button
                style={{ background: "#b91c1c22", border: "1px solid #f85149", borderRadius: 4, padding: "3px 10px", color: "#f85149", cursor: "pointer", fontSize: 11 }}
                onClick={() => handleRevoke(s.id)}
                disabled={revoking === s.id}
              >{revoking === s.id ? "…" : "Revoke"}</button>
            </div>
          ))
      }
    </div>
  );
}

function MFAPanel() {
  const [token] = useState(() => localStorage.getItem("access_token") || "");
  const [tab, setTab] = useState("status");
  const [setupData, setSetupData] = useState(null);
  const [code, setCode] = useState("");
  const [msg, setMsg] = useState("");
  const [backupCodes, setBackupCodes] = useState([]);

  const { data: mfaStatus, refetch } = useQuery({
    queryKey: ["mfa-status"],
    queryFn: () => authApi.getMFAStatus(token),
    enabled: !!token,
  });

  const handleSetup = async () => {
    try {
      const data = await authApi.setupMFA(token);
      setSetupData(data);
      setTab("setup");
      setMsg("");
    } catch (e) { setMsg("Error: " + e.message); }
  };

  const handleEnable = async () => {
    if (!code.trim()) return;
    try {
      const r = await authApi.enableMFA(code.trim(), token);
      setBackupCodes(r.backup_codes || []);
      setMsg("MFA enabled successfully!");
      setCode("");
      setSetupData(null);
      setTab("backup");
      refetch();
    } catch (e) { setMsg("Error: " + e.message); }
  };

  const handleDisable = async () => {
    if (!code.trim()) return;
    try {
      await authApi.disableMFA(code.trim(), token);
      setMsg("MFA disabled.");
      setCode("");
      refetch();
    } catch (e) { setMsg("Error: " + e.message); }
  };

  if (!token) return (
    <div style={S.card}>
      <div style={S.sectionTitle}>Two-Factor Authentication</div>
      <div style={{ color: "#8b949e", fontSize: 13 }}>Log in to manage MFA.</div>
    </div>
  );

  const enabled = mfaStatus?.enabled;
  const configured = mfaStatus?.configured;

  return (
    <div style={S.card}>
      <div style={S.sectionTitle}>Two-Factor Authentication (TOTP)</div>

      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
        <span style={{ width: 10, height: 10, borderRadius: "50%", background: enabled ? "#3fb950" : "#f85149" }} />
        <span style={{ fontSize: 14, fontWeight: 600 }}>{enabled ? "Enabled" : "Disabled"}</span>
        {configured && !enabled && <span style={{ fontSize: 11, color: "#d29922" }}>(configured but not active)</span>}
      </div>

      {tab === "status" && !enabled && (
        <>
          <button style={S.btn()} onClick={handleSetup}>Set Up TOTP</button>
          {msg && <div style={{ fontSize: 12, color: "#f85149", marginTop: 6 }}>{msg}</div>}
        </>
      )}

      {tab === "setup" && setupData && (
        <>
          <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 8 }}>
            Scan this provisioning URI with your authenticator app, then enter the 6-digit code:
          </div>
          <div style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "10px 12px", fontSize: 11, wordBreak: "break-all", color: "#3fb950", marginBottom: 12 }}>
            {setupData.provisioning_uri}
          </div>
          <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 8 }}>
            Secret: <code style={{ color: "#d2a8ff" }}>{setupData.secret}</code>
          </div>
          <input style={S.input} placeholder="Enter 6-digit TOTP code" value={code} onChange={(e) => setCode(e.target.value)} maxLength={6} />
          <button style={S.btn()} onClick={handleEnable} disabled={code.length < 6}>Verify & Enable</button>
          <button style={S.btn("#21262d")} onClick={() => { setTab("status"); setSetupData(null); }}>Cancel</button>
          {msg && <div style={{ fontSize: 12, color: msg.startsWith("Error") ? "#f85149" : "#3fb950", marginTop: 6 }}>{msg}</div>}
        </>
      )}

      {tab === "backup" && backupCodes.length > 0 && (
        <>
          <div style={{ fontSize: 12, color: "#d29922", marginBottom: 8 }}>Save these backup codes securely — they won't be shown again:</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4, marginBottom: 12 }}>
            {backupCodes.map((c) => (
              <code key={c} style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: 4, padding: "4px 8px", fontSize: 12, color: "#e6edf3" }}>{c}</code>
            ))}
          </div>
          <button style={S.btn("#21262d")} onClick={() => { setTab("status"); setMsg(""); }}>Done</button>
        </>
      )}

      {enabled && tab === "status" && (
        <>
          <div style={{ marginTop: 8, paddingTop: 8, borderTop: "1px solid #30363d" }}>
            <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 8 }}>To disable, enter your current TOTP code:</div>
            <input style={S.input} placeholder="6-digit TOTP code" value={code} onChange={(e) => setCode(e.target.value)} maxLength={6} />
            <button style={S.btn("#b91c1c")} onClick={handleDisable} disabled={code.length < 6}>Disable MFA</button>
          </div>
          {msg && <div style={{ fontSize: 12, color: msg.startsWith("Error") ? "#f85149" : "#3fb950", marginTop: 6 }}>{msg}</div>}
        </>
      )}
    </div>
  );
}

function LoginHistoryPanel() {
  const [token] = useState(() => localStorage.getItem("access_token") || "");
  const { data, isLoading } = useQuery({
    queryKey: ["login-history"],
    queryFn: () => authApi.getLoginHistory(token, 20),
    enabled: !!token,
  });

  const history = data?.history || [];

  return (
    <div style={S.card}>
      <div style={S.sectionTitle}>Login History</div>
      {!token ? (
        <div style={{ color: "#8b949e", fontSize: 13 }}>Log in to view history.</div>
      ) : isLoading ? (
        <div style={{ color: "#8b949e" }}>Loading…</div>
      ) : history.length === 0 ? (
        <div style={{ color: "#8b949e", fontSize: 13 }}>No login history.</div>
      ) : history.map((h) => (
        <div key={h.id} style={S.row}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: h.success ? "#3fb950" : "#f85149" }} />
              <span style={{ fontSize: 13, color: "#e6edf3" }}>{h.ip_address || "Unknown IP"}</span>
            </div>
            {h.failure_reason && <div style={{ fontSize: 11, color: "#f85149" }}>{h.failure_reason}</div>}
            <div style={{ fontSize: 10, color: "#484f58" }}>{h.created_at?.substring(0, 19)}</div>
          </div>
          <span style={{ fontSize: 11, fontWeight: 600, color: h.success ? "#3fb950" : "#f85149" }}>
            {h.success ? "SUCCESS" : "FAILED"}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function SecuritySettings() {
  return (
    <div style={S.page}>
      <div style={S.title}>Security Settings</div>
      <div style={S.grid}>
        <div>
          <HealthPanel />
          <MFAPanel />
        </div>
        <div>
          <SessionsPanel />
          <LoginHistoryPanel />
        </div>
      </div>
    </div>
  );
}
