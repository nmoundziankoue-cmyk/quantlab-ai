import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";

const API = "";
const card = { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20 };

function HealthBar({ score }) {
  const pct = Math.round(score * 100);
  const color = pct > 80 ? "#3fb950" : pct > 50 ? "#d29922" : "#f85149";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1, background: "#21262d", borderRadius: 4, height: 6 }}>
        <div style={{ width: `${pct}%`, height: 6, background: color, borderRadius: 4, transition: "width 0.4s" }} />
      </div>
      <span style={{ fontSize: 12, color, minWidth: 36 }}>{pct}%</span>
    </div>
  );
}

export default function ProviderDashboard() {
  const qc = useQueryClient();

  const { data: healthData } = useQuery({
    queryKey: ["provider-health"],
    queryFn: () => axios.get(`${API}/providers/health`).then(r => r.data),
    refetchInterval: 20000,
  });

  const { data: ranking } = useQuery({
    queryKey: ["provider-ranking"],
    queryFn: () => axios.get(`${API}/providers/ranking`).then(r => r.data),
    refetchInterval: 30000,
  });

  const invalidate = useMutation({
    mutationFn: () => axios.delete(`${API}/providers/cache`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["provider-health"] }),
  });

  const providers = healthData?.ranked ?? [];

  return (
    <div style={{ padding: 28, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Provider Dashboard</h1>
          <p style={{ color: "#8b949e", margin: "4px 0 0", fontSize: 13 }}>Market data provider health and ranking</p>
        </div>
        <button
          onClick={() => invalidate.mutate()}
          style={{ background: "#21262d", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "8px 16px", cursor: "pointer", fontSize: 13 }}
        >
          Invalidate Cache
        </button>
      </div>

      {/* Summary */}
      <div style={{ display: "flex", gap: 12, marginBottom: 24 }}>
        {[
          { label: "Total Providers", value: healthData?.provider_count ?? "—" },
          { label: "Healthy (>80%)", value: healthData?.healthy_count ?? "—" },
        ].map(s => (
          <div key={s.label} style={{ ...card, minWidth: 160 }}>
            <div style={{ color: "#8b949e", fontSize: 12 }}>{s.label}</div>
            <div style={{ fontSize: 28, fontWeight: 700, color: "#e6edf3" }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Provider table */}
      <div style={card}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #30363d" }}>
              {["Rank", "Provider", "Health Score", "Avg Latency", "P95 Latency", "Success Rate", "Total Calls", "Errors"].map(h => (
                <th key={h} style={{ textAlign: "left", padding: "8px 12px", color: "#8b949e", fontWeight: 500 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(ranking?.ranked ?? providers).map((p, i) => (
              <tr key={p.name} style={{ borderBottom: "1px solid #21262d" }}>
                <td style={{ padding: "10px 12px", color: "#8b949e" }}>#{i + 1}</td>
                <td style={{ padding: "10px 12px", fontWeight: 600, color: "#58a6ff" }}>{p.name}</td>
                <td style={{ padding: "10px 12px", minWidth: 160 }}><HealthBar score={p.health_score ?? 0} /></td>
                <td style={{ padding: "10px 12px" }}>{p.latency?.avg_latency_ms ?? "—"}ms</td>
                <td style={{ padding: "10px 12px" }}>{p.latency?.p95_latency_ms ?? "—"}ms</td>
                <td style={{ padding: "10px 12px", color: p.latency?.success_rate > 0.9 ? "#3fb950" : "#d29922" }}>
                  {p.latency?.success_rate != null ? `${(p.latency.success_rate * 100).toFixed(1)}%` : "—"}
                </td>
                <td style={{ padding: "10px 12px" }}>{p.total_calls ?? "—"}</td>
                <td style={{ padding: "10px 12px", color: "#f85149" }}>{p.error_count ?? "—"}</td>
              </tr>
            ))}
            {providers.length === 0 && (
              <tr><td colSpan={8} style={{ padding: 20, textAlign: "center", color: "#8b949e" }}>No provider data yet — make some API calls first.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
