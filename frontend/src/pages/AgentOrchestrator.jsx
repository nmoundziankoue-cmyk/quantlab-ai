import { useState } from "react";
import { useWorkflows, useOrchestratorHealth, useCreateWorkflow, useExecuteWorkflow, useCancelWorkflow, useDeleteWorkflow, useQuickRun } from "../hooks/useOrchestrator";

const S = {
  page: { padding: 24, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" },
  title: { fontSize: 22, fontWeight: 700, marginBottom: 20 },
  grid2: { display: "grid", gridTemplateColumns: "320px 1fr", gap: 16 },
  card: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sectionTitle: { fontSize: 12, color: "#8b949e", fontWeight: 600, marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.05em" },
  input: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "8px 12px", color: "#e6edf3", fontSize: 13, width: "100%", outline: "none", marginBottom: 8, boxSizing: "border-box" },
  btn: (c = "#238636") => ({ background: c, border: "none", borderRadius: 6, padding: "7px 14px", color: "#fff", cursor: "pointer", fontSize: 12, fontWeight: 600, marginRight: 6, marginBottom: 6 }),
  statusBadge: (s) => {
    const c = { COMPLETED: "#3fb950", RUNNING: "#58a6ff", FAILED: "#f85149", PENDING: "#8b949e", CANCELLED: "#6e7681" }[s] || "#8b949e";
    return { background: c + "22", color: c, borderRadius: 4, padding: "2px 8px", fontSize: 11, fontWeight: 600, display: "inline-block" };
  },
  wfRow: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 6, padding: 14, marginBottom: 8 },
  taskRow: { background: "#161b22", border: "1px solid #21262d", borderRadius: 4, padding: "8px 12px", marginBottom: 4, display: "flex", justifyContent: "space-between", alignItems: "center" },
  metricCard: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 16, textAlign: "center" },
  metricVal: { fontSize: 28, fontWeight: 700, marginBottom: 4 },
  metricLabel: { fontSize: 12, color: "#8b949e" },
};

function MetricCard({ val, label, color = "#e6edf3" }) {
  return (
    <div style={S.metricCard}>
      <div style={{ ...S.metricVal, color }}>{val}</div>
      <div style={S.metricLabel}>{label}</div>
    </div>
  );
}

export default function AgentOrchestrator() {
  const { data: workflows = [] } = useWorkflows();
  const { data: health } = useOrchestratorHealth();
  const createWorkflow = useCreateWorkflow();
  const executeWorkflow = useExecuteWorkflow();
  const cancelWorkflow = useCancelWorkflow();
  const deleteWorkflow = useDeleteWorkflow();
  const quickRun = useQuickRun();

  const [quickTicker, setQuickTicker] = useState("AAPL");
  const [quickAgents, setQuickAgents] = useState("market_analyst,fundamental_analyst,risk_analyst");
  const [selectedWF, setSelectedWF] = useState(null);
  const [quickResult, setQuickResult] = useState(null);

  const handleQuickRun = () => {
    quickRun.mutate(
      { ticker: quickTicker, agentIds: quickAgents },
      { onSuccess: (d) => { setQuickResult(d); setSelectedWF(d.workflow_id); } }
    );
  };

  const selectedWorkflow = workflows.find((w) => w.id === selectedWF);

  return (
    <div style={S.page}>
      <div style={S.title}>Agent Orchestrator</div>

      {health && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 20 }}>
          <MetricCard val={health.total_workflows} label="Total Workflows" />
          <MetricCard val={health.active_workflows} label="Active" color="#58a6ff" />
          <MetricCard val={`${health.success_rate}%`} label="Success Rate" color="#3fb950" />
          <MetricCard val={health.by_status?.COMPLETED || 0} label="Completed" color="#3fb950" />
        </div>
      )}

      <div style={S.grid2}>
        <div>
          <div style={S.card}>
            <div style={S.sectionTitle}>Quick Run</div>
            <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 10 }}>Create and execute a workflow instantly</div>
            <label style={{ fontSize: 12, color: "#8b949e", display: "block", marginBottom: 4 }}>Ticker</label>
            <input style={S.input} value={quickTicker} onChange={(e) => setQuickTicker(e.target.value.toUpperCase())} />
            <label style={{ fontSize: 12, color: "#8b949e", display: "block", marginBottom: 4 }}>Agents (comma-separated)</label>
            <input style={S.input} value={quickAgents} onChange={(e) => setQuickAgents(e.target.value)} />
            <button style={S.btn("#1f6feb")} onClick={handleQuickRun} disabled={quickRun.isPending}>
              {quickRun.isPending ? "Running..." : "⚡ Quick Run"}
            </button>
          </div>

          {workflows.length > 0 && (
            <div style={S.card}>
              <div style={S.sectionTitle}>Workflows ({workflows.length})</div>
              {workflows.slice(0, 15).map((wf) => (
                <div key={wf.id} style={{ ...S.wfRow, cursor: "pointer", border: selectedWF === wf.id ? "1px solid #1f6feb" : "1px solid #21262d" }} onClick={() => setSelectedWF(wf.id)}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>{wf.name}</div>
                    <span style={S.statusBadge(wf.status)}>{wf.status}</span>
                  </div>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    {wf.status === "PENDING" && (
                      <button style={S.btn()} onClick={(e) => { e.stopPropagation(); executeWorkflow.mutate({ id: wf.id, body: { ticker: quickTicker } }); }}>Run</button>
                    )}
                    {wf.status === "RUNNING" && (
                      <button style={S.btn("#b91c1c")} onClick={(e) => { e.stopPropagation(); cancelWorkflow.mutate(wf.id); }}>Cancel</button>
                    )}
                    <button style={S.btn("#21262d")} onClick={(e) => { e.stopPropagation(); deleteWorkflow.mutate(wf.id); }}>Delete</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div>
          {quickResult && (
            <div style={S.card}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <div style={S.sectionTitle}>Execution Results</div>
                <span style={S.statusBadge(quickResult.status)}>{quickResult.status}</span>
              </div>
              {quickResult.summary && (
                <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 12 }}>
                  {quickResult.summary.tasks_completed}/{quickResult.summary.tasks_total} tasks completed
                </div>
              )}
              {(quickResult.tasks || []).map((t) => (
                <div key={t.task_name} style={S.taskRow}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>{t.task_name}</div>
                    <div style={{ fontSize: 11, color: "#8b949e" }}>{t.agent_id}</div>
                  </div>
                  <span style={S.statusBadge(t.status)}>{t.status}</span>
                </div>
              ))}
            </div>
          )}

          {selectedWorkflow && !quickResult && (
            <div style={S.card}>
              <div style={S.sectionTitle}>Workflow Details</div>
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>{selectedWorkflow.name}</div>
              <span style={S.statusBadge(selectedWorkflow.status)}>{selectedWorkflow.status}</span>
              {selectedWorkflow.result_summary && (
                <div style={{ marginTop: 12, fontSize: 12, color: "#8b949e" }}>
                  {JSON.stringify(selectedWorkflow.result_summary)}
                </div>
              )}
            </div>
          )}

          {!quickResult && !selectedWorkflow && (
            <div style={{ ...S.card, textAlign: "center", padding: 60 }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>⚙️</div>
              <div style={{ color: "#8b949e" }}>Select a workflow or run a quick execution to see results</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
