import { useState, useRef, useEffect } from "react";
import { useEntities, useFullGraph, useCreateEntity, useDeleteEntity, useCreateEdge, useExtractEntities } from "../hooks/useKnowledgeGraph";

const S = {
  page: { padding: 24, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" },
  title: { fontSize: 22, fontWeight: 700, marginBottom: 20 },
  grid2: { display: "grid", gridTemplateColumns: "320px 1fr", gap: 16 },
  card: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20, marginBottom: 16 },
  sectionTitle: { fontSize: 12, color: "#8b949e", fontWeight: 600, marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.05em" },
  input: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "8px 12px", color: "#e6edf3", fontSize: 13, width: "100%", outline: "none", marginBottom: 8, boxSizing: "border-box" },
  select: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "8px 12px", color: "#e6edf3", fontSize: 13, width: "100%", outline: "none", marginBottom: 8, boxSizing: "border-box" },
  btn: (c = "#238636") => ({ background: c, border: "none", borderRadius: 6, padding: "7px 14px", color: "#fff", cursor: "pointer", fontSize: 12, fontWeight: 600, marginRight: 6, marginBottom: 6 }),
  textarea: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "8px 12px", color: "#e6edf3", fontSize: 12, width: "100%", outline: "none", marginBottom: 8, boxSizing: "border-box", height: 80, resize: "vertical" },
  entityRow: { display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #21262d", alignItems: "center" },
};

const ENTITY_TYPE_COLORS = {
  TICKER: "#58a6ff", SECTOR: "#3fb950", PERSON: "#f0883e",
  CONCEPT: "#d2a8ff", EVENT: "#ffa657", COUNTRY: "#79c0ff",
  INDUSTRY: "#56d364", PRODUCT: "#ff7b72",
};

function SimpleGraphViz({ graph }) {
  const ref = useRef(null);
  const { nodes, edges } = graph || {};

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas || !nodes?.length) return;
    const ctx = canvas.getContext("2d");
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    // Place nodes in a circle
    const positions = {};
    nodes.forEach((n, i) => {
      const angle = (i / nodes.length) * 2 * Math.PI - Math.PI / 2;
      const r = Math.min(W, H) * 0.38;
      positions[n.id] = { x: W / 2 + r * Math.cos(angle), y: H / 2 + r * Math.sin(angle) };
    });

    // Draw edges
    ctx.strokeStyle = "#30363d";
    ctx.lineWidth = 1;
    (edges || []).forEach((e) => {
      const s = positions[e.source_id], t = positions[e.target_id];
      if (!s || !t) return;
      ctx.beginPath();
      ctx.moveTo(s.x, s.y);
      ctx.lineTo(t.x, t.y);
      ctx.stroke();
    });

    // Draw nodes
    nodes.forEach((n) => {
      const pos = positions[n.id];
      if (!pos) return;
      const color = ENTITY_TYPE_COLORS[n.entity_type] || "#8b949e";
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 8, 0, 2 * Math.PI);
      ctx.fillStyle = color + "44";
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.fillStyle = "#e6edf3";
      ctx.font = "10px monospace";
      ctx.textAlign = "center";
      ctx.fillText(n.name.substring(0, 8), pos.x, pos.y + 20);
    });
  }, [graph]);

  if (!nodes?.length) return (
    <div style={{ textAlign: "center", padding: 40, color: "#8b949e" }}>
      <div style={{ fontSize: 36, marginBottom: 8 }}>🕸</div>
      <div>No entities in graph yet. Create entities to visualize the knowledge graph.</div>
    </div>
  );

  return <canvas ref={ref} width={600} height={400} style={{ width: "100%", height: 400, borderRadius: 6 }} />;
}

export default function KnowledgeGraph() {
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState("TICKER");
  const [newDesc, setNewDesc] = useState("");
  const [extractText, setExtractText] = useState("");
  const [extractResult, setExtractResult] = useState(null);
  const [tab, setTab] = useState("entities");
  const [typeFilter, setTypeFilter] = useState("");

  const { data: entities = [] } = useEntities({ entity_type: typeFilter || undefined, limit: 100 });
  const { data: graph } = useFullGraph({ limit: 200 });
  const createEntity = useCreateEntity();
  const deleteEntity = useDeleteEntity();
  const extractEntities = useExtractEntities();

  const handleCreate = () => {
    if (!newName.trim()) return;
    createEntity.mutate({ name: newName.trim(), entity_type: newType, description: newDesc || undefined }, {
      onSuccess: () => { setNewName(""); setNewDesc(""); },
    });
  };

  const handleExtract = () => {
    extractEntities.mutate({ text: extractText, persist: true }, { onSuccess: setExtractResult });
  };

  const tabs = [{ k: "entities", l: "Entities" }, { k: "graph", l: "Graph View" }, { k: "extract", l: "Entity Extraction" }];

  return (
    <div style={S.page}>
      <div style={S.title}>Knowledge Graph</div>
      <div style={S.grid2}>
        <div>
          <div style={S.card}>
            <div style={S.sectionTitle}>Add Entity</div>
            <input style={S.input} placeholder="Entity name (e.g. AAPL)" value={newName} onChange={(e) => setNewName(e.target.value)} />
            <select style={S.select} value={newType} onChange={(e) => setNewType(e.target.value)}>
              {Object.keys(ENTITY_TYPE_COLORS).map((t) => <option key={t}>{t}</option>)}
            </select>
            <input style={S.input} placeholder="Description (optional)" value={newDesc} onChange={(e) => setNewDesc(e.target.value)} />
            <button style={S.btn()} onClick={handleCreate} disabled={createEntity.isPending}>
              {createEntity.isPending ? "Creating..." : "Add Entity"}
            </button>
          </div>

          <div style={S.card}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <div style={S.sectionTitle}>Entity Types</div>
            </div>
            {Object.entries(ENTITY_TYPE_COLORS).map(([type, color]) => {
              const count = entities.filter((e) => e.entity_type === type).length;
              return (
                <div key={type} style={{ ...S.entityRow, cursor: "pointer" }} onClick={() => setTypeFilter(typeFilter === type ? "" : type)}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <div style={{ width: 10, height: 10, borderRadius: "50%", background: color }} />
                    <span style={{ fontSize: 13, color: typeFilter === type ? color : "#e6edf3" }}>{type}</span>
                  </div>
                  <span style={{ fontSize: 12, color: "#8b949e" }}>{count}</span>
                </div>
              );
            })}
            {typeFilter && <div style={{ marginTop: 8 }}><button style={S.btn("#21262d")} onClick={() => setTypeFilter("")}>Clear Filter</button></div>}
          </div>
        </div>

        <div>
          <div style={{ display: "flex", gap: 4, marginBottom: 16, borderBottom: "1px solid #30363d" }}>
            {tabs.map(({ k, l }) => (
              <div key={k} style={{ padding: "8px 16px", cursor: "pointer", fontSize: 13, fontWeight: 600, borderBottom: `2px solid ${tab === k ? "#58a6ff" : "transparent"}`, color: tab === k ? "#58a6ff" : "#8b949e", marginBottom: -1 }} onClick={() => setTab(k)}>{l}</div>
            ))}
          </div>

          {tab === "entities" && (
            <div style={S.card}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
                <div style={S.sectionTitle}>{typeFilter ? `${typeFilter} entities` : "All Entities"} ({entities.length})</div>
              </div>
              {entities.length === 0 ? (
                <div style={{ textAlign: "center", padding: 30, color: "#8b949e" }}>No entities yet. Add one or use Entity Extraction.</div>
              ) : entities.slice(0, 30).map((e) => {
                const color = ENTITY_TYPE_COLORS[e.entity_type] || "#8b949e";
                return (
                  <div key={e.id} style={S.entityRow}>
                    <div>
                      <span style={{ color, fontWeight: 700, marginRight: 8 }}>{e.name}</span>
                      <span style={{ fontSize: 11, color: "#8b949e" }}>{e.entity_type}</span>
                      {e.description && <div style={{ fontSize: 11, color: "#6e7681", marginTop: 2 }}>{e.description.substring(0, 60)}</div>}
                    </div>
                    <button style={{ background: "#b91c1c", border: "none", borderRadius: 4, padding: "3px 8px", color: "#fff", cursor: "pointer", fontSize: 11 }} onClick={() => deleteEntity.mutate(e.id)}>Del</button>
                  </div>
                );
              })}
            </div>
          )}

          {tab === "graph" && (
            <div style={S.card}>
              <div style={S.sectionTitle}>Knowledge Graph Visualization ({graph?.node_count || 0} nodes, {graph?.edge_count || 0} edges)</div>
              <SimpleGraphViz graph={graph} />
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
                {Object.entries(ENTITY_TYPE_COLORS).map(([t, c]) => (
                  <div key={t} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, color: "#8b949e" }}>
                    <div style={{ width: 8, height: 8, borderRadius: "50%", background: c }} />{t}
                  </div>
                ))}
              </div>
            </div>
          )}

          {tab === "extract" && (
            <div style={S.card}>
              <div style={S.sectionTitle}>Extract Entities from Text</div>
              <textarea style={S.textarea} placeholder="Paste any financial text to automatically extract and store entities..." value={extractText} onChange={(e) => setExtractText(e.target.value)} />
              <button style={S.btn("#1f6feb")} onClick={handleExtract} disabled={extractEntities.isPending || !extractText.trim()}>
                {extractEntities.isPending ? "Extracting..." : "Extract & Store Entities"}
              </button>
              {extractResult && (
                <div style={{ marginTop: 16, padding: 12, background: "#0d1117", borderRadius: 6, border: "1px solid #30363d" }}>
                  <div style={{ fontSize: 12, color: "#3fb950", marginBottom: 8 }}>
                    Extracted {extractResult.extracted_count} entities ({extractResult.created} new, {extractResult.existing} existing)
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
