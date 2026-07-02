import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { altIntelligenceApi } from "../api/altIntelligenceApi";

const S = {
  page: { padding: 28, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" },
  card: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20, marginBottom: 16 },
  title: { fontSize: 13, fontWeight: 700, color: "#8b949e", letterSpacing: "0.06em", marginBottom: 14, textTransform: "uppercase" },
  label: { fontSize: 12, color: "#8b949e", marginBottom: 4, display: "block" },
  input: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "9px 12px", fontSize: 13, width: "100%", boxSizing: "border-box" },
  select: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "9px 12px", fontSize: 13, width: "100%", boxSizing: "border-box" },
  btn: { background: "#1f6feb", border: "none", borderRadius: 6, color: "#fff", padding: "10px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer" },
  err: { background: "#2d1317", border: "1px solid #f85149", borderRadius: 6, color: "#f85149", padding: "10px 14px", fontSize: 13, marginBottom: 14 },
  pill: { display: "inline-block", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600 },
  hitCard: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 6, padding: 14, marginBottom: 8 },
  toggle: { display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontSize: 13 },
};

const FILING_TYPES = ["", "10-K", "10-Q", "8-K", "Proxy", "13F", "13D", "Insider", "Transcript", "Other"];

function ScoreBar({ score }) {
  const pct = Math.min(100, score * 100);
  const color = score >= 0.5 ? "#3fb950" : score >= 0.2 ? "#d29922" : "#58a6ff";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, flex: "0 0 120px" }}>
      <div style={{ flex: 1, background: "#21262d", borderRadius: 3, height: 4 }}>
        <div style={{ width: `${pct}%`, background: color, height: "100%", borderRadius: 3 }} />
      </div>
      <span style={{ fontSize: 11, color, fontFamily: "monospace", minWidth: 40 }}>{Number(score).toFixed(3)}</span>
    </div>
  );
}

export default function AltSearchDashboard() {
  const [query, setQuery] = useState("");
  const [symbol, setSymbol] = useState("");
  const [filingType, setFilingType] = useState("");
  const [executive, setExecutive] = useState("");
  const [company, setCompany] = useState("");
  const [since, setSince] = useState("");
  const [until, setUntil] = useState("");
  const [semantic, setSemantic] = useState(false);
  const [limit, setLimit] = useState("20");
  const [result, setResult] = useState(null);

  const mut = useMutation({
    mutationFn: () => {
      const payload = { semantic, limit: parseInt(limit) };
      if (query) payload.query = query;
      if (symbol) payload.symbol = symbol.toUpperCase();
      if (filingType) payload.filing_type = filingType;
      if (executive) payload.executive = executive;
      if (company) payload.company = company;
      if (since) payload.since = since;
      if (until) payload.until = until;
      return altIntelligenceApi.search(payload);
    },
    onSuccess: r => setResult(r.data),
  });

  const hasAnyCriteria = query || symbol || filingType || executive || company;

  return (
    <div style={S.page}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Search Dashboard</h1>
        <p style={{ color: "#8b949e", margin: "4px 0 0", fontSize: 13 }}>
          Full-text, semantic, and metadata search across the M14 alternative data document index
        </p>
      </div>

      <div style={S.card}>
        <div style={S.title}>Search Parameters</div>

        {/* Primary search */}
        <div style={{ marginBottom: 14 }}>
          <label style={S.label}>Search Query</label>
          <div style={{ display: "flex", gap: 10 }}>
            <input style={{ ...S.input, flex: 1 }} value={query} onChange={e => setQuery(e.target.value)}
              placeholder="revenue growth, CEO change, merger, patent approval…"
              onKeyDown={e => e.key === "Enter" && hasAnyCriteria && mut.mutate()} />
            <label style={{ ...S.toggle, flexShrink: 0 }}>
              <div style={{ width: 36, height: 20, borderRadius: 10, background: semantic ? "#1f6feb" : "#30363d", position: "relative", transition: "background 0.2s", cursor: "pointer" }}
                onClick={() => setSemantic(s => !s)}>
                <div style={{ width: 16, height: 16, borderRadius: "50%", background: "#fff", position: "absolute", top: 2, left: semantic ? 18 : 2, transition: "left 0.2s" }} />
              </div>
              <span style={{ fontSize: 12, color: semantic ? "#58a6ff" : "#8b949e" }}>Semantic</span>
            </label>
          </div>
        </div>

        {/* Metadata filters */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 10, marginBottom: 14 }}>
          <div><label style={S.label}>Symbol</label><input style={S.input} value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} placeholder="AAPL" /></div>
          <div><label style={S.label}>Filing Type</label>
            <select style={S.select} value={filingType} onChange={e => setFilingType(e.target.value)}>
              {FILING_TYPES.map(t => <option key={t} value={t}>{t || "All"}</option>)}
            </select>
          </div>
          <div><label style={S.label}>Executive</label><input style={S.input} value={executive} onChange={e => setExecutive(e.target.value)} placeholder="Tim Cook" /></div>
          <div><label style={S.label}>Company</label><input style={S.input} value={company} onChange={e => setCompany(e.target.value)} placeholder="Apple Inc" /></div>
          <div><label style={S.label}>Max Results</label>
            <select style={S.select} value={limit} onChange={e => setLimit(e.target.value)}>
              {[10, 20, 50, 100].map(n => <option key={n}>{n}</option>)}
            </select>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 16 }}>
          <div><label style={S.label}>From Date (YYYY-MM-DD)</label><input style={S.input} value={since} onChange={e => setSince(e.target.value)} placeholder="2024-01-01" /></div>
          <div><label style={S.label}>To Date (YYYY-MM-DD)</label><input style={S.input} value={until} onChange={e => setUntil(e.target.value)} placeholder="2024-12-31" /></div>
        </div>

        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <button style={{ ...S.btn, opacity: !hasAnyCriteria || mut.isPending ? 0.5 : 1 }}
            onClick={() => mut.mutate()} disabled={!hasAnyCriteria || mut.isPending}>
            {mut.isPending ? "Searching…" : "Search"}
          </button>
          <button style={{ background: "transparent", border: "1px solid #30363d", borderRadius: 6, color: "#8b949e", padding: "10px 16px", fontSize: 13, cursor: "pointer" }}
            onClick={() => { setQuery(""); setSymbol(""); setFilingType(""); setExecutive(""); setCompany(""); setSince(""); setUntil(""); setResult(null); }}>
            Clear
          </button>
          {!hasAnyCriteria && <span style={{ fontSize: 12, color: "#8b949e" }}>Provide at least one search criterion</span>}
        </div>
      </div>

      {mut.error && <div style={S.err}>{mut.error.message}</div>}

      {result && (
        <div style={S.card}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <div style={S.title}>Results — {result.hit_count} document{result.hit_count !== 1 ? "s" : ""} {semantic ? "(semantic)" : "(full-text)"}</div>
            {result.hit_count > 0 && <span style={{ fontSize: 12, color: "#8b949e" }}>Ranked by relevance</span>}
          </div>

          {result.hit_count === 0 ? (
            <div style={{ textAlign: "center", padding: 40, color: "#8b949e" }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>○</div>
              <div>No documents match your search criteria.</div>
              <div style={{ fontSize: 12, marginTop: 8 }}>Ingest documents via the Alternative Data Explorer first.</div>
            </div>
          ) : (
            result.hits.map((hit, i) => (
              <div key={hit.doc_id} style={S.hitCard}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                  <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                    <span style={{ fontSize: 13, fontWeight: 700, color: "#58a6ff" }}>{hit.symbol}</span>
                    <span style={{ ...S.pill, background: "#21262d", color: "#e6edf3" }}>{hit.filing_type}</span>
                    <span style={{ fontSize: 11, color: "#8b949e", fontFamily: "monospace" }}>{hit.doc_id}</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 11, color: "#8b949e" }}>#{i + 1}</span>
                    <ScoreBar score={hit.score} />
                  </div>
                </div>
                <p style={{ fontSize: 12, color: "#8b949e", margin: 0, lineHeight: 1.6, fontStyle: "italic", overflow: "hidden", textOverflow: "ellipsis", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>
                  {hit.snippet}
                </p>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
