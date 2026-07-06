import { useQuery } from "@tanstack/react-query";
import axios from "axios";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8001";

const card = { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20 };
const label = { color: "#8b949e", fontSize: 12, marginBottom: 4 };
const val = { color: "#e6edf3", fontSize: 24, fontWeight: 700 };
const section = { marginBottom: 24 };

function StatCard({ title, value, unit = "" }) {
  return (
    <div style={{ ...card, minWidth: 160 }}>
      <div style={label}>{title}</div>
      <div style={val}>{value ?? "—"}<span style={{ fontSize: 13, color: "#8b949e", marginLeft: 4 }}>{unit}</span></div>
    </div>
  );
}

export default function SystemMetrics() {
  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ["sys-health"],
    queryFn: () => axios.get(`${API}/system/health/detailed`).then(r => r.data),
    refetchInterval: 15000,
    retry: 1,
  });
  const { data: metrics } = useQuery({
    queryKey: ["sys-metrics"],
    queryFn: () => axios.get(`${API}/system/metrics`).then(r => r.data),
    refetchInterval: 30000,
    retry: 1,
  });
  const { data: tasks } = useQuery({
    queryKey: ["sys-tasks"],
    queryFn: () => axios.get(`${API}/system/tasks`).then(r => r.data),
    refetchInterval: 10000,
    retry: 1,
  });
  const { data: slowOps } = useQuery({
    queryKey: ["slow-ops"],
    queryFn: () => axios.get(`${API}/observability/slow-queries`).then(r => r.data),
    refetchInterval: 30000,
    retry: 1,
  });

  return (
    <div style={{ padding: 28, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>System Metrics</h1>
        <p style={{ color: "#8b949e", margin: "4px 0 0", fontSize: 13 }}>Real-time observability dashboard</p>
      </div>

      {/* Health */}
      <div style={section}>
        <div style={{ fontSize: 13, fontWeight: 600, color: "#8b949e", marginBottom: 12, textTransform: "uppercase", letterSpacing: 1 }}>Health</div>
        {healthLoading ? (
          <div style={{ color: "#8b949e", fontSize: 13 }}>Connecting to backend…</div>
        ) : (
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <StatCard title="API Status" value={health?.status ?? "—"} />
            <StatCard title="Database" value={health?.checks?.database ?? "—"} />
            <StatCard title="Cache" value={health?.checks?.cache ?? "—"} />
            <StatCard title="Uptime" value={health?.uptime_s ? Math.floor(health.uptime_s / 60) : "—"} unit={health?.uptime_s ? "min" : ""} />
          </div>
        )}
      </div>

      {/* Tasks */}
      <div style={section}>
        <div style={{ fontSize: 13, fontWeight: 600, color: "#8b949e", marginBottom: 12, textTransform: "uppercase", letterSpacing: 1 }}>Background Tasks</div>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <StatCard title="Pending" value={tasks?.stats?.pending ?? "—"} />
          <StatCard title="Running" value={tasks?.stats?.running ?? "—"} />
          <StatCard title="Completed" value={tasks?.stats?.completed ?? "—"} />
          <StatCard title="Failed" value={tasks?.stats?.failed ?? "—"} />
        </div>
      </div>

      {/* Slow queries */}
      <div style={section}>
        <div style={{ fontSize: 13, fontWeight: 600, color: "#8b949e", marginBottom: 12, textTransform: "uppercase", letterSpacing: 1 }}>Slow Operations (≥200ms)</div>
        <div style={card}>
          {slowOps?.slow_queries?.length === 0 && <div style={{ color: "#8b949e", fontSize: 13 }}>No slow operations recorded.</div>}
          {(slowOps?.slow_queries ?? []).slice(0, 10).map((op, i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #21262d", fontSize: 13 }}>
              <span style={{ color: "#e6edf3" }}>{op.operation}</span>
              <span style={{ color: "#f85149" }}>{op.duration_ms}ms</span>
            </div>
          ))}
        </div>
      </div>

      {/* Raw metrics */}
      {metrics && (
        <div style={section}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#8b949e", marginBottom: 12, textTransform: "uppercase", letterSpacing: 1 }}>Prometheus Metrics (raw)</div>
          <div style={{ ...card, maxHeight: 300, overflow: "auto" }}>
            <pre style={{ fontSize: 11, color: "#8b949e", margin: 0, whiteSpace: "pre-wrap" }}>
              {typeof metrics === "string" ? metrics.slice(0, 2000) : JSON.stringify(metrics, null, 2).slice(0, 2000)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
