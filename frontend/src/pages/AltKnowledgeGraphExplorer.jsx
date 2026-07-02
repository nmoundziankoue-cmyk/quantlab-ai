import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { altIntelligenceApi } from "../api/altIntelligenceApi";

const S = {
  page: { padding: 28, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" },
  card: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20, marginBottom: 16 },
  title: { fontSize: 13, fontWeight: 700, color: "#8b949e", letterSpacing: "0.06em", marginBottom: 14, textTransform: "uppercase" },
  label: { fontSize: 12, color: "#8b949e", marginBottom: 4, display: "block" },
  input: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "9px 12px", fontSize: 13, width: "100%", boxSizing: "border-box" },
  btn: { background: "#1f6feb", border: "none", borderRadius: 6, color: "#fff", padding: "10px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer" },
  btnGreen: { background: "#238636", border: "none", borderRadius: 6, color: "#fff", padding: "10px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer" },
  tab: { padding: "8px 18px", fontSize: 13, fontWeight: 600, cursor: "pointer", borderRadius: "6px 6px 0 0", border: "1px solid transparent", background: "transparent", color: "#8b949e", marginRight: 2 },
  tabActive: { background: "#161b22", border: "1px solid #30363d", borderBottom: "1px solid #161b22", color: "#e6edf3" },
  err: { background: "#2d1317", border: "1px solid #f85149", borderRadius: 6, color: "#f85149", padding: "10px 14px", fontSize: 13, marginBottom: 14 },
  ok: { background: "#1a3a25", border: "1px solid #3fb950", borderRadius: 6, color: "#3fb950", padding: "10px 14px", fontSize: 13, marginBottom: 14 },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 12 },
  th: { padding: "8px 10px", textAlign: "left", color: "#8b949e", borderBottom: "1px solid #21262d", fontWeight: 600 },
  td: { padding: "7px 10px", borderBottom: "1px solid #21262d", color: "#e6edf3" },
  metricBox: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 6, padding: "16px 14px", textAlign: "center" },
  metricValue: { fontSize: 24, fontWeight: 700, color: "#58a6ff", lineHeight: 1.2 },
  metricLabel: { fontSize: 11, color: "#8b949e", marginTop: 4, textTransform: "uppercase", letterSpacing: "0.06em" },
};

function MetricsTab() {
  const { data, isLoading, refetch } = useQuery({ queryKey: ["kg-metrics"], queryFn: () => altIntelligenceApi.graphMetrics().then(r => r.data) });

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 14 }}>
        <button style={S.btn} onClick={() => refetch()}>Refresh</button>
      </div>
      {isLoading && <div style={{ color: "#8b949e", fontSize: 13 }}>Loading metrics…</div>}
      {data && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 20 }}>
            <div style={S.metricBox}><div style={S.metricValue}>{data.node_count}</div><div style={S.metricLabel}>Total Nodes</div></div>
            <div style={S.metricBox}><div style={S.metricValue}>{data.component_count}</div><div style={S.metricLabel}>Components</div></div>
            <div style={S.metricBox}><div style={{ ...S.metricValue, color: "#3fb950" }}>{data.largest_component_size}</div><div style={S.metricLabel}>Largest Component</div></div>
            <div style={S.metricBox}><div style={{ ...S.metricValue, color: "#d2a679" }}>{data.community_count}</div><div style={S.metricLabel}>Communities</div></div>
          </div>
          {data.top_central_nodes?.length > 0 && (
            <div style={S.card}>
              <div style={S.title}>Top Central Nodes (Degree Centrality)</div>
              <div style={{ overflowX: "auto" }}>
                <table style={S.table}>
                  <thead><tr><th style={S.th}>Rank</th><th style={S.th}>Node ID</th><th style={S.th}>Centrality Score</th></tr></thead>
                  <tbody>
                    {data.top_central_nodes.map((n, i) => (
                      <tr key={n.node_id}>
                        <td style={{ ...S.td, color: "#8b949e" }}>#{i + 1}</td>
                        <td style={{ ...S.td, fontWeight: 700 }}>{n.node_id}</td>
                        <td style={{ ...S.td, color: "#58a6ff" }}>{Number(n.centrality).toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function DependencyChainTab() {
  const [src, setSrc] = useState("");
  const [tgt, setTgt] = useState("");
  const [maxDepth, setMaxDepth] = useState(6);
  const [result, setResult] = useState(null);

  const mut = useMutation({
    mutationFn: () => altIntelligenceApi.dependencyChain({ source_id: src, target_id: tgt, max_depth: parseInt(maxDepth) }),
    onSuccess: r => setResult(r.data),
  });

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 120px auto", gap: 12, alignItems: "flex-end", marginBottom: 16 }}>
        <div><label style={S.label}>Source Node ID</label><input style={S.input} value={src} onChange={e => setSrc(e.target.value)} placeholder="e.g. AAPL" /></div>
        <div><label style={S.label}>Target Node ID</label><input style={S.input} value={tgt} onChange={e => setTgt(e.target.value)} placeholder="e.g. MSFT" /></div>
        <div><label style={S.label}>Max Depth</label><input style={{ ...S.input, textAlign: "center" }} type="number" value={maxDepth} onChange={e => setMaxDepth(e.target.value)} min={1} max={20} /></div>
        <button style={{ ...S.btn, opacity: !src || !tgt || mut.isPending ? 0.6 : 1 }} onClick={() => mut.mutate()} disabled={!src || !tgt || mut.isPending}>
          {mut.isPending ? "Searching…" : "Find Path"}
        </button>
      </div>
      {mut.error && <div style={S.err}>{mut.error.message}</div>}
      {result && (
        <div style={S.card}>
          <div style={S.title}>Dependency Chain Result</div>
          {result.found ? (
            <div>
              <div style={{ fontSize: 13, color: "#3fb950", marginBottom: 12 }}>Path found ({result.path.length} nodes)</div>
              <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 6 }}>
                {result.path.map((node, i) => (
                  <span key={`${node}-${i}`} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ background: "#1f3245", border: "1px solid #1f6feb", borderRadius: 6, padding: "4px 12px", fontSize: 13, color: "#58a6ff", fontWeight: 600 }}>{node}</span>
                    {i < result.path.length - 1 && <span style={{ color: "#8b949e", fontSize: 18 }}>→</span>}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <div style={{ color: "#f85149", fontSize: 13 }}>No path found between "{src}" and "{tgt}" within depth {maxDepth}.</div>
          )}
        </div>
      )}
    </div>
  );
}

function LinkTab() {
  const [mode, setMode] = useState("executive");
  const [entityId, setEntityId] = useState("");
  const [entityName, setEntityName] = useState("");
  const [companyId, setCompanyId] = useState("");
  const [relLabel, setRelLabel] = useState("");
  const [score, setScore] = useState("1.0");
  const [ok, setOk] = useState(null);

  const mut = useMutation({
    mutationFn: () => {
      const payload = { entity_id: entityId, entity_name: entityName, related_company_id: companyId, relation_label: relLabel, score: parseFloat(score) };
      return mode === "executive" ? altIntelligenceApi.linkExecutive(payload) : altIntelligenceApi.linkSupplier(payload);
    },
    onSuccess: r => setOk(r.data),
  });

  return (
    <div>
      <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
        {["executive", "supplier"].map(m => (
          <button key={m} onClick={() => setMode(m)} style={{ ...S.tab, ...(mode === m ? S.tabActive : {}) }}>{m === "executive" ? "Link Executive" : "Link Supplier"}</button>
        ))}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 14 }}>
        <div><label style={S.label}>{mode === "executive" ? "Executive ID" : "Supplier ID"}</label><input style={S.input} value={entityId} onChange={e => setEntityId(e.target.value)} placeholder={mode === "executive" ? "exec_john_doe" : "supplier_tsmc"} /></div>
        <div><label style={S.label}>{mode === "executive" ? "Executive Name" : "Supplier Name"}</label><input style={S.input} value={entityName} onChange={e => setEntityName(e.target.value)} placeholder={mode === "executive" ? "John Doe" : "TSMC"} /></div>
        <div><label style={S.label}>Company ID</label><input style={S.input} value={companyId} onChange={e => setCompanyId(e.target.value)} placeholder="AAPL" /></div>
        <div><label style={S.label}>{mode === "executive" ? "Role / Relation Label" : "Revenue Share (0–1)"}</label>
          <input style={S.input} value={mode === "executive" ? relLabel : score}
            onChange={e => mode === "executive" ? setRelLabel(e.target.value) : setScore(e.target.value)}
            placeholder={mode === "executive" ? "CEO" : "0.35"} />
        </div>
      </div>
      <button style={{ ...S.btnGreen, opacity: !entityId || !entityName || !companyId || mut.isPending ? 0.6 : 1 }}
        onClick={() => mut.mutate()} disabled={!entityId || !entityName || !companyId || mut.isPending}>
        {mut.isPending ? "Linking…" : `Link ${mode === "executive" ? "Executive" : "Supplier"}`}
      </button>
      {mut.error && <div style={{ ...S.err, marginTop: 12 }}>{mut.error.message}</div>}
      {ok && <div style={{ ...S.ok, marginTop: 12 }}>Linked: {entityName} → {companyId} (status: {ok.status})</div>}
    </div>
  );
}

const TABS = [{ key: "metrics", label: "Graph Metrics" }, { key: "chain", label: "Dependency Chain" }, { key: "link", label: "Link Entities" }];

export default function AltKnowledgeGraphExplorer() {
  const [active, setActive] = useState("metrics");
  return (
    <div style={S.page}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Knowledge Graph Explorer</h1>
        <p style={{ color: "#8b949e", margin: "4px 0 0", fontSize: 13 }}>Graph metrics, dependency chains, executive & supplier relationships across the institutional knowledge graph</p>
      </div>
      <div style={{ display: "flex", borderBottom: "1px solid #30363d" }}>
        {TABS.map(t => <button key={t.key} onClick={() => setActive(t.key)} style={{ ...S.tab, ...(active === t.key ? S.tabActive : {}) }}>{t.label}</button>)}
      </div>
      <div style={{ ...S.card, borderTopLeftRadius: 0, marginTop: 0, borderTop: "none" }}>
        {active === "metrics" && <MetricsTab />}
        {active === "chain" && <DependencyChainTab />}
        {active === "link" && <LinkTab />}
      </div>
    </div>
  );
}
