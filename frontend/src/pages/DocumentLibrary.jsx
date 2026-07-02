import { useState } from "react";
import { useDocuments, useIngestDocument, useDeleteDocument, useSearchDocuments, useAskDocument } from "../hooks/useDocuments";
import useDocumentStore from "../store/useDocumentStore";

const S = {
  page: { padding: 24, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" },
  title: { fontSize: 22, fontWeight: 700, marginBottom: 20 },
  grid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24 },
  card: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20 },
  cardTitle: { fontSize: 13, color: "#8b949e", fontWeight: 600, marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.05em" },
  input: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "8px 12px", color: "#e6edf3", fontSize: 13, width: "100%", outline: "none", marginBottom: 8, boxSizing: "border-box" },
  textarea: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "8px 12px", color: "#e6edf3", fontSize: 13, width: "100%", outline: "none", marginBottom: 8, resize: "vertical", boxSizing: "border-box" },
  btn: (color = "#238636") => ({ background: color, border: "none", borderRadius: 6, padding: "8px 16px", color: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 600, marginRight: 8 }),
  row: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid #21262d" },
  tag: (color) => ({ background: (color || "#1c2128"), border: "1px solid #30363d", borderRadius: 4, padding: "2px 8px", fontSize: 11, color: color ? "#fff" : "#8b949e" }),
  statusColor: { INDEXED: "#3fb950", PENDING: "#f0883e", PROCESSING: "#58a6ff", FAILED: "#f85149" },
  result: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: 12, marginTop: 8, fontSize: 13, color: "#e6edf3" },
};

export default function DocumentLibrary() {
  const { data: docs = [] } = useDocuments();
  const ingest = useIngestDocument();
  const deleteDoc = useDeleteDocument();
  const searchDocs = useSearchDocuments();
  const askDoc = useAskDocument();
  const store = useDocumentStore();

  const [ingestForm, setIngestForm] = useState({ title: "", doc_type: "RESEARCH_REPORT", content: "" });
  const [searchQuery, setSearchQuery] = useState("");
  const [searchType, setSearchType] = useState("HYBRID");
  const [question, setQuestion] = useState("");

  const handleIngest = () => {
    if (!ingestForm.title || !ingestForm.content) return;
    ingest.mutate(ingestForm, { onSuccess: () => setIngestForm({ title: "", doc_type: "RESEARCH_REPORT", content: "" }) });
  };

  const handleSearch = () => {
    if (!searchQuery) return;
    searchDocs.mutate({ query: searchQuery, search_type: searchType, top_k: 10 }, { onSuccess: (r) => store.setLastSearchResults(r) });
  };

  const handleAsk = () => {
    if (!question) return;
    askDoc.mutate({ question, top_k: 5 }, { onSuccess: (r) => store.setLastAnswer(r) });
  };

  return (
    <div style={S.page}>
      <div style={S.title}>Document Intelligence Library</div>

      <div style={S.grid}>
        <div style={S.card}>
          <div style={S.cardTitle}>Ingest Document</div>
          <input style={S.input} placeholder="Title" value={ingestForm.title} onChange={(e) => setIngestForm((f) => ({ ...f, title: e.target.value }))} />
          <select style={S.input} value={ingestForm.doc_type} onChange={(e) => setIngestForm((f) => ({ ...f, doc_type: e.target.value }))}>
            {["RESEARCH_REPORT", "SEC_FILING", "EARNINGS_TRANSCRIPT", "NEWS_ARTICLE", "MACRO_REPORT", "OTHER"].map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          <textarea style={{ ...S.textarea, height: 100 }} placeholder="Paste document content..." value={ingestForm.content} onChange={(e) => setIngestForm((f) => ({ ...f, content: e.target.value }))} />
          <button style={S.btn()} onClick={handleIngest} disabled={ingest.isPending}>{ingest.isPending ? "Ingesting..." : "Ingest"}</button>
          {ingest.isSuccess && <span style={{ color: "#3fb950", fontSize: 13 }}>Indexed successfully</span>}
        </div>

        <div style={S.card}>
          <div style={S.cardTitle}>Semantic Search</div>
          <input style={S.input} placeholder="Search query..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
          <select style={S.input} value={searchType} onChange={(e) => setSearchType(e.target.value)}>
            {["HYBRID", "SEMANTIC", "KEYWORD"].map((t) => <option key={t}>{t}</option>)}
          </select>
          <button style={S.btn("#1f6feb")} onClick={handleSearch} disabled={searchDocs.isPending}>Search</button>
          {store.lastSearchResults && (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 6 }}>{store.lastSearchResults.total_results} results</div>
              {store.lastSearchResults.results?.slice(0, 5).map((r, i) => (
                <div key={i} style={S.result}>
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>{r.document_title} <span style={{ color: "#8b949e", fontWeight: 400 }}>({(r.score * 100).toFixed(0)}%)</span></div>
                  <div style={{ fontSize: 12, color: "#8b949e" }}>{r.content?.slice(0, 120)}...</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div style={S.card}>
        <div style={S.cardTitle}>Ask Documents (RAG)</div>
        <div style={{ display: "flex", gap: 8 }}>
          <input style={{ ...S.input, marginBottom: 0 }} placeholder="Ask a question..." value={question} onChange={(e) => setQuestion(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleAsk()} />
          <button style={S.btn()} onClick={handleAsk} disabled={askDoc.isPending}>Ask</button>
        </div>
        {store.lastAnswer && (
          <div style={{ ...S.result, marginTop: 12 }}>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>{store.lastAnswer.question}</div>
            <div style={{ fontSize: 14, lineHeight: 1.6 }}>{store.lastAnswer.answer}</div>
            <div style={{ fontSize: 11, color: "#8b949e", marginTop: 8 }}>Confidence: {(store.lastAnswer.confidence * 100).toFixed(0)}% · {store.lastAnswer.model_used}</div>
          </div>
        )}
      </div>

      <div style={{ ...S.card, marginTop: 16 }}>
        <div style={S.cardTitle}>Documents ({docs.length})</div>
        {docs.length === 0 && <div style={{ color: "#8b949e", fontSize: 13 }}>No documents yet. Ingest your first document above.</div>}
        {docs.map((d) => (
          <div key={d.id} style={S.row}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{d.title}</div>
              <div style={{ fontSize: 12, color: "#8b949e" }}>{d.doc_type} · {d.chunk_count} chunks</div>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <span style={S.tag(S.statusColor[d.status])}>{d.status}</span>
              <button style={{ ...S.btn("#b91c1c"), padding: "4px 10px", fontSize: 12 }} onClick={() => deleteDoc.mutate(d.id)}>Delete</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
