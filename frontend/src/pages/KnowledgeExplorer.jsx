import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import axios from "axios";

const API = "";
const card = { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20, marginBottom: 16 };
const ENTITY_COLORS = { company: "#58a6ff", sector: "#3fb950", concept: "#d29922", event: "#f85149", person: "#a371f7" };

export default function KnowledgeExplorer() {
  const [searchQ, setSearchQ] = useState("");
  const [similarTicker, setSimilarTicker] = useState("AAPL");
  const [searchResults, setSearchResults] = useState(null);
  const [similarResults, setSimilarResults] = useState(null);

  const { data: stats } = useQuery({
    queryKey: ["kg2-stats"],
    queryFn: () => axios.get(`${API}/knowledge/v2/stats`).then(r => r.data),
  });

  const { data: entities } = useQuery({
    queryKey: ["kg2-entities"],
    queryFn: () => axios.get(`${API}/knowledge/v2/entities?limit=50`).then(r => r.data),
  });

  const { data: clusters } = useQuery({
    queryKey: ["kg2-clusters"],
    queryFn: () => axios.get(`${API}/knowledge/v2/clusters?entity_type=company&n=4`).then(r => r.data),
  });

  const search = useMutation({
    mutationFn: () => axios.get(`${API}/knowledge/v2/search?q=${encodeURIComponent(searchQ)}&top_k=8`).then(r => r.data),
    onSuccess: (d) => setSearchResults(d.results),
  });

  const findSimilar = useMutation({
    mutationFn: () => axios.get(`${API}/knowledge/v2/similar/${similarTicker}?top_k=5`).then(r => r.data),
    onSuccess: (d) => setSimilarResults(d.similar),
  });

  return (
    <div style={{ padding: 28, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Knowledge Explorer</h1>
        <p style={{ color: "#8b949e", margin: "4px 0 0", fontSize: 13 }}>Semantic entity search, similarity, and concept clustering</p>
      </div>

      {/* Stats */}
      {stats && (
        <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
          {[["Entities", stats.entity_count], ["Relationships", stats.relationship_count],
            ["Companies", stats.entity_types?.company ?? 0], ["Sectors", stats.entity_types?.sector ?? 0]].map(([k, v]) => (
            <div key={k} style={{ ...card, margin: 0, flex: 1 }}>
              <div style={{ fontSize: 11, color: "#8b949e" }}>{k}</div>
              <div style={{ fontSize: 24, fontWeight: 700 }}>{v}</div>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {/* Semantic search */}
        <div style={card}>
          <div style={{ fontWeight: 600, marginBottom: 12 }}>Semantic Search</div>
          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            <input value={searchQ} onChange={e => setSearchQ(e.target.value)} placeholder="Search entities…"
              style={{ flex: 1, background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "8px 10px", fontSize: 13 }} />
            <button onClick={() => search.mutate()} style={{ background: "#1f6feb", border: "none", borderRadius: 6, color: "#fff", padding: "8px 14px", cursor: "pointer", fontSize: 13 }}>
              Search
            </button>
          </div>
          {(searchResults ?? []).map(r => (
            <div key={r.id} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #21262d", fontSize: 13 }}>
              <div>
                <span style={{ fontWeight: 600, color: ENTITY_COLORS[r.type] ?? "#e6edf3" }}>{r.id}</span>
                <span style={{ color: "#8b949e", marginLeft: 8 }}>{r.name}</span>
              </div>
              <span style={{ color: "#d29922" }}>{(r.similarity * 100).toFixed(1)}%</span>
            </div>
          ))}
        </div>

        {/* Similar companies */}
        <div style={card}>
          <div style={{ fontWeight: 600, marginBottom: 12 }}>Similar Companies</div>
          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            <input value={similarTicker} onChange={e => setSimilarTicker(e.target.value.toUpperCase())} placeholder="Ticker…"
              style={{ width: 100, background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "8px 10px", fontSize: 13 }} />
            <button onClick={() => findSimilar.mutate()} style={{ background: "#238636", border: "none", borderRadius: 6, color: "#fff", padding: "8px 14px", cursor: "pointer", fontSize: 13 }}>
              Find Similar
            </button>
          </div>
          {(similarResults ?? []).map(r => (
            <div key={r.id} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #21262d", fontSize: 13 }}>
              <span style={{ fontWeight: 600, color: "#58a6ff" }}>{r.id}</span>
              <span style={{ color: "#8b949e" }}>{r.name}</span>
              <span style={{ color: "#3fb950" }}>{(r.similarity * 100).toFixed(1)}% similar</span>
            </div>
          ))}
        </div>
      </div>

      {/* Entity table */}
      <div style={card}>
        <div style={{ fontWeight: 600, marginBottom: 12 }}>All Entities</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {(entities?.entities ?? []).map(e => (
            <div key={e.id} style={{ background: "#0d1117", border: `1px solid ${ENTITY_COLORS[e.type] ?? "#30363d"}`, borderRadius: 6, padding: "6px 12px", fontSize: 12 }}>
              <span style={{ color: ENTITY_COLORS[e.type] ?? "#e6edf3", fontWeight: 600 }}>{e.id}</span>
              <span style={{ color: "#8b949e", marginLeft: 6 }}>{e.name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Clusters */}
      {clusters?.clusters?.length > 0 && (
        <div style={card}>
          <div style={{ fontWeight: 600, marginBottom: 12 }}>Company Clusters</div>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {clusters.clusters.map((c, i) => (
              <div key={i} style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "10px 14px", flex: "1 1 150px" }}>
                <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 6 }}>Cluster {c.cluster + 1}</div>
                {c.members.map(m => <div key={m} style={{ fontSize: 13, color: "#58a6ff" }}>{m}</div>)}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
