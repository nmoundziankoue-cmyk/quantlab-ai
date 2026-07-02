import { useState } from "react";
import {
  useBrokerTypes,
  useBrokerConnections,
  useCreateBrokerConnection,
  useDeleteBrokerConnection,
  useTestBrokerConnection,
} from "../hooks/useBrokers";
import useTradingStore from "../store/useTradingStore";

const BROKER_COLORS = {
  PAPER: "#2563eb",
  ALPACA: "#f59e0b",
  IBKR: "#10b981",
  BINANCE: "#f7931a",
  KRAKEN: "#5741d9",
  OANDA: "#dc2626",
};

function StatusDot({ status }) {
  const color = status === "CONNECTED" ? "#4ade80" : status === "ERROR" ? "#f87171" : "#475569";
  return (
    <span style={{
      display: "inline-block",
      width: 8, height: 8,
      borderRadius: "50%",
      background: color,
      marginRight: 6,
      boxShadow: status === "CONNECTED" ? `0 0 6px ${color}` : "none",
    }} />
  );
}

function BrokerCard({ connection, onDelete, onTest, testing }) {
  const color = BROKER_COLORS[connection.broker_type] || "#2563eb";
  return (
    <div style={styles.card}>
      <div style={styles.cardHeader}>
        <div style={{ ...styles.brokerBadge, background: `${color}22`, color }}>
          {connection.broker_type}
        </div>
        <div style={styles.connStatus}>
          <StatusDot status={connection.status} />
          <span style={{ fontSize: 11, color: connection.status === "CONNECTED" ? "#4ade80" : "#64748b" }}>
            {connection.status || "DISCONNECTED"}
          </span>
        </div>
      </div>
      <div style={styles.connName}>{connection.name}</div>
      {connection.account_id && <div style={styles.connMeta}>Account: {connection.account_id}</div>}
      {connection.environment && (
        <span style={{ ...styles.envBadge, background: connection.environment === "LIVE" ? "#2a1a1a" : "#1e2a1a", color: connection.environment === "LIVE" ? "#f87171" : "#4ade80", borderColor: connection.environment === "LIVE" ? "#b91c1c" : "#16a34a" }}>
          {connection.environment}
        </span>
      )}
      {connection.last_ping_at && (
        <div style={styles.connMeta}>
          Last ping: {new Date(connection.last_ping_at).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
        </div>
      )}
      <div style={styles.cardActions}>
        <button style={styles.btnTest} onClick={() => onTest(connection.id)} disabled={testing}>
          {testing ? "Testing…" : "Test"}
        </button>
        <button style={styles.btnDelete} onClick={() => onDelete(connection.id)}>Remove</button>
      </div>
    </div>
  );
}

function NewConnectionForm({ brokerTypes, onClose }) {
  const [brokerType, setBrokerType] = useState("PAPER");
  const [name, setName] = useState("");
  const [env, setEnv] = useState("PAPER");
  const [accountId, setAccountId] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [error, setError] = useState(null);
  const addNotification = useTradingStore((s) => s.addNotification);
  const create = useCreateBrokerConnection();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    const credentials = {};
    if (apiKey) credentials.api_key = apiKey;
    if (apiSecret) credentials.api_secret = apiSecret;
    try {
      await create.mutateAsync({
        broker_type: brokerType,
        name: name.trim(),
        environment: env,
        account_id: accountId || undefined,
        credentials,
        config: {},
      });
      addNotification({ type: "success", message: `Broker connection "${name}" created` });
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  return (
    <div style={styles.modal}>
      <div style={styles.modalBox}>
        <div style={styles.modalTitle}>Add Broker Connection</div>
        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.formRow}>
            <div style={styles.field}>
              <label style={styles.fl}>Broker</label>
              <select style={styles.sel} value={brokerType} onChange={(e) => setBrokerType(e.target.value)}>
                {(brokerTypes ?? []).map((t) => <option key={t.type} value={t.type}>{t.name}</option>)}
              </select>
            </div>
            <div style={styles.field}>
              <label style={styles.fl}>Environment</label>
              <select style={styles.sel} value={env} onChange={(e) => setEnv(e.target.value)}>
                <option value="PAPER">Paper</option>
                <option value="SANDBOX">Sandbox</option>
                <option value="LIVE">Live</option>
              </select>
            </div>
          </div>
          <div style={styles.field}>
            <label style={styles.fl}>Connection Name</label>
            <input style={styles.inp} value={name} onChange={(e) => setName(e.target.value)} placeholder="My IB Account" required />
          </div>
          <div style={styles.field}>
            <label style={styles.fl}>Account ID (optional)</label>
            <input style={styles.inp} value={accountId} onChange={(e) => setAccountId(e.target.value)} placeholder="DU123456" />
          </div>
          {brokerType !== "PAPER" && (
            <>
              <div style={styles.field}>
                <label style={styles.fl}>API Key</label>
                <input style={styles.inp} value={apiKey} onChange={(e) => setApiKey(e.target.value)} type="password" placeholder="••••••••••" />
              </div>
              <div style={styles.field}>
                <label style={styles.fl}>API Secret</label>
                <input style={styles.inp} value={apiSecret} onChange={(e) => setApiSecret(e.target.value)} type="password" placeholder="••••••••••" />
              </div>
            </>
          )}
          {error && <div style={styles.err}>{error}</div>}
          <div style={styles.modalActions}>
            <button type="button" style={styles.btnCancel} onClick={onClose}>Cancel</button>
            <button type="submit" style={styles.btnCreate} disabled={create.isPending}>
              {create.isPending ? "Adding…" : "Add Connection"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function BrokerConnections() {
  const [showForm, setShowForm] = useState(false);
  const [testingId, setTestingId] = useState(null);
  const addNotification = useTradingStore((s) => s.addNotification);

  const { data: brokerTypes = [] } = useBrokerTypes();
  const { data: connections = [], isLoading } = useBrokerConnections();
  const deleteConn = useDeleteBrokerConnection();
  const testConn = useTestBrokerConnection();

  const handleDelete = async (id) => {
    if (!window.confirm("Remove this broker connection?")) return;
    try {
      await deleteConn.mutateAsync(id);
      addNotification({ type: "info", message: "Connection removed" });
    } catch (err) {
      addNotification({ type: "error", message: err.response?.data?.detail || err.message });
    }
  };

  const handleTest = async (id) => {
    setTestingId(id);
    try {
      const result = await testConn.mutateAsync(id);
      addNotification({ type: result.status === "CONNECTED" ? "success" : "warning", title: "Connection Test", message: result.message || (result.status === "CONNECTED" ? "Connected" : "Failed") });
    } catch (err) {
      addNotification({ type: "error", message: err.response?.data?.detail || err.message });
    } finally {
      setTestingId(null);
    }
  };

  const connectedCount = connections.filter((c) => c.status === "CONNECTED").length;

  return (
    <div style={styles.root}>
      {showForm && <NewConnectionForm brokerTypes={brokerTypes} onClose={() => setShowForm(false)} />}

      <div style={styles.headerRow}>
        <div>
          <h1 style={styles.h1}>Broker Connections</h1>
          <p style={styles.sub}>{connectedCount}/{connections.length} connected — refreshes every 30 s</p>
        </div>
        <button style={styles.btnNew} onClick={() => setShowForm(true)}>+ Add Connection</button>
      </div>

      {isLoading && <div style={styles.loading}>Loading connections…</div>}

      {!isLoading && connections.length === 0 && (
        <div style={styles.empty}>
          <div style={styles.emptyTitle}>No broker connections configured</div>
          <div style={styles.emptyHint}>Add a connection to route live orders to your broker.</div>
          <button style={{ ...styles.btnNew, marginTop: 16 }} onClick={() => setShowForm(true)}>Add Your First Connection</button>
        </div>
      )}

      <div style={styles.grid}>
        {connections.map((conn) => (
          <BrokerCard
            key={conn.id}
            connection={conn}
            onDelete={handleDelete}
            onTest={handleTest}
            testing={testingId === conn.id}
          />
        ))}
      </div>

      {brokerTypes.length > 0 && (
        <div style={styles.typesSection}>
          <div style={styles.typesTitle}>Supported Brokers</div>
          <div style={styles.typesGrid}>
            {brokerTypes.map((bt) => (
              <div key={bt.type} style={styles.typeCard}>
                <div style={{ ...styles.typeName, color: BROKER_COLORS[bt.type] || "#94a3b8" }}>{bt.name}</div>
                <div style={styles.typeStatus}>{bt.status}</div>
                {bt.description && <div style={styles.typeDesc}>{bt.description}</div>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  root: { padding: "28px 32px", minHeight: "100vh" },
  headerRow: { display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 24 },
  h1: { fontSize: 22, fontWeight: 700, color: "#e2e8f0", margin: "0 0 4px" },
  sub: { fontSize: 13, color: "#475569", margin: 0 },
  btnNew: { background: "#1d4ed8", border: "none", borderRadius: 6, color: "#fff", fontSize: 13, fontWeight: 600, padding: "9px 16px", cursor: "pointer" },
  loading: { color: "#475569", fontSize: 13, padding: "24px 0" },
  empty: { textAlign: "center", padding: "80px 0" },
  emptyTitle: { fontSize: 16, fontWeight: 600, color: "#94a3b8", marginBottom: 8 },
  emptyHint: { fontSize: 13, color: "#475569" },
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16, marginBottom: 32 },
  card: { background: "#111318", border: "1px solid #1e2230", borderRadius: 10, padding: "18px 20px" },
  cardHeader: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 },
  brokerBadge: { fontSize: 11, fontWeight: 700, letterSpacing: "0.06em", padding: "3px 10px", borderRadius: 4 },
  connStatus: { display: "flex", alignItems: "center" },
  connName: { fontSize: 15, fontWeight: 700, color: "#e2e8f0", marginBottom: 4 },
  connMeta: { fontSize: 11, color: "#475569", marginBottom: 4 },
  envBadge: { display: "inline-block", fontSize: 10, fontWeight: 700, letterSpacing: "0.06em", padding: "2px 8px", borderRadius: 3, border: "1px solid", marginTop: 4, marginBottom: 8 },
  cardActions: { display: "flex", gap: 8, marginTop: 14 },
  btnTest: { background: "#1e2230", border: "1px solid #2d3748", borderRadius: 5, color: "#94a3b8", fontSize: 12, fontWeight: 600, padding: "5px 14px", cursor: "pointer", flex: 1 },
  btnDelete: { background: "none", border: "1px solid #374151", borderRadius: 5, color: "#6b7280", fontSize: 12, fontWeight: 600, padding: "5px 14px", cursor: "pointer" },
  typesSection: { borderTop: "1px solid #1e2230", paddingTop: 24 },
  typesTitle: { fontSize: 12, fontWeight: 600, color: "#475569", letterSpacing: "0.06em", marginBottom: 14 },
  typesGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 10 },
  typeCard: { background: "#0d0f14", border: "1px solid #1e2230", borderRadius: 7, padding: "12px 14px" },
  typeName: { fontSize: 13, fontWeight: 700, marginBottom: 2 },
  typeStatus: { fontSize: 10, color: "#475569", letterSpacing: "0.04em", marginBottom: 4 },
  typeDesc: { fontSize: 11, color: "#374151" },
  modal: { position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", zIndex: 999, display: "flex", alignItems: "center", justifyContent: "center" },
  modalBox: { background: "#111318", border: "1px solid #1e2230", borderRadius: 10, padding: "24px 28px", width: 480, maxWidth: "90vw" },
  modalTitle: { fontSize: 16, fontWeight: 700, color: "#e2e8f0", marginBottom: 20 },
  form: { display: "flex", flexDirection: "column", gap: 12 },
  formRow: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 },
  field: { display: "flex", flexDirection: "column", gap: 4 },
  fl: { fontSize: 11, fontWeight: 600, color: "#475569", letterSpacing: "0.04em" },
  inp: { background: "#1a1d24", border: "1px solid #2d3748", borderRadius: 5, color: "#e2e8f0", fontSize: 13, padding: "8px 10px", outline: "none" },
  sel: { background: "#1a1d24", border: "1px solid #2d3748", borderRadius: 5, color: "#e2e8f0", fontSize: 13, padding: "8px 10px", outline: "none", cursor: "pointer" },
  err: { background: "#2a1a1a", border: "1px solid #b91c1c", borderRadius: 5, color: "#f87171", fontSize: 12, padding: "8px 10px" },
  modalActions: { display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 8 },
  btnCancel: { background: "#1e2230", border: "1px solid #2d3748", borderRadius: 6, color: "#94a3b8", fontSize: 13, fontWeight: 600, padding: "8px 20px", cursor: "pointer" },
  btnCreate: { background: "#1d4ed8", border: "none", borderRadius: 6, color: "#fff", fontSize: 13, fontWeight: 700, padding: "8px 20px", cursor: "pointer" },
};
