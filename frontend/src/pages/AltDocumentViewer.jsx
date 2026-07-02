import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { altIntelligenceApi } from "../api/altIntelligenceApi";

const S = {
  page: { padding: 28, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" },
  card: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20, marginBottom: 16 },
  title: { fontSize: 13, fontWeight: 700, color: "#8b949e", letterSpacing: "0.06em", marginBottom: 14, textTransform: "uppercase" },
  label: { fontSize: 12, color: "#8b949e", marginBottom: 4, display: "block" },
  input: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "9px 12px", fontSize: 13, width: "100%", boxSizing: "border-box" },
  select: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "9px 12px", fontSize: 13, width: "100%", boxSizing: "border-box" },
  btn: { background: "#1f6feb", border: "none", borderRadius: 6, color: "#fff", padding: "10px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer" },
  btnGreen: { background: "#238636", border: "none", borderRadius: 6, color: "#fff", padding: "10px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer" },
  tab: { padding: "8px 18px", fontSize: 13, fontWeight: 600, cursor: "pointer", borderRadius: "6px 6px 0 0", border: "1px solid transparent", background: "transparent", color: "#8b949e", marginRight: 2 },
  tabActive: { background: "#161b22", border: "1px solid #30363d", borderBottom: "1px solid #161b22", color: "#e6edf3" },
  err: { background: "#2d1317", border: "1px solid #f85149", borderRadius: 6, color: "#f85149", padding: "10px 14px", fontSize: 13, marginBottom: 14 },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 12 },
  th: { padding: "8px 10px", textAlign: "left", color: "#8b949e", borderBottom: "1px solid #21262d", fontWeight: 600 },
  td: { padding: "7px 10px", borderBottom: "1px solid #21262d", color: "#e6edf3" },
  pill: { display: "inline-block", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600 },
  metricBox: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 6, padding: "12px 14px", textAlign: "center" },
  metricValue: { fontSize: 20, fontWeight: 700, color: "#58a6ff", lineHeight: 1.2 },
  metricLabel: { fontSize: 11, color: "#8b949e", marginTop: 4, textTransform: "uppercase", letterSpacing: "0.06em" },
  textarea: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "9px 12px", fontSize: 12, width: "100%", boxSizing: "border-box", resize: "vertical", fontFamily: "monospace" },
  kvRow: { display: "flex", gap: 8, padding: "4px 0", borderBottom: "1px solid #21262d", fontSize: 12 },
  kvKey: { color: "#8b949e", minWidth: 160, flexShrink: 0 },
  kvVal: { color: "#e6edf3", wordBreak: "break-word" },
};

const FILING_TYPES = ["10-K", "10-Q", "8-K", "Proxy", "13F", "13D", "Insider", "Transcript", "Other"];

function sentimentColor(v) {
  if (v > 0.1) return "#3fb950";
  if (v < -0.1) return "#f85149";
  return "#8b949e";
}

function DocumentListTab() {
  const [symbol, setSymbol] = useState("");
  const [filingType, setFilingType] = useState("");
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["alt-docs", symbol, filingType],
    queryFn: () => altIntelligenceApi.listDocuments({ symbol: symbol || undefined, filing_type: filingType || undefined }).then(r => r.data),
  });
  const { data: stats } = useQuery({ queryKey: ["alt-doc-stats"], queryFn: () => altIntelligenceApi.documentStats().then(r => r.data) });

  return (
    <div>
      {stats && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 16 }}>
          <div style={S.metricBox}><div style={S.metricValue}>{stats.total_documents ?? 0}</div><div style={S.metricLabel}>Total Documents</div></div>
          <div style={S.metricBox}><div style={S.metricValue}>{stats.total_symbols ?? 0}</div><div style={S.metricLabel}>Symbols</div></div>
          <div style={S.metricBox}><div style={S.metricValue}>{stats.total_size_bytes ? (stats.total_size_bytes / 1024).toFixed(1) + " KB" : "0 KB"}</div><div style={S.metricLabel}>Total Size</div></div>
        </div>
      )}
      <div style={{ display: "flex", gap: 10, marginBottom: 14, alignItems: "flex-end" }}>
        <div><label style={S.label}>Symbol filter</label><input style={{ ...S.input, width: 120 }} value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} placeholder="All" /></div>
        <div><label style={S.label}>Filing type</label>
          <select style={{ ...S.select, width: 140 }} value={filingType} onChange={e => setFilingType(e.target.value)}>
            <option value="">All</option>
            {FILING_TYPES.map(t => <option key={t}>{t}</option>)}
          </select>
        </div>
        <button style={S.btn} onClick={() => refetch()}>Filter</button>
      </div>
      {isLoading && <div style={{ color: "#8b949e", fontSize: 13 }}>Loading…</div>}
      {data && data.length === 0 && <div style={{ color: "#8b949e", fontSize: 13 }}>No documents found. Use the Alt Data Explorer to ingest documents.</div>}
      {data && data.length > 0 && (
        <div style={{ overflowX: "auto" }}>
          <table style={S.table}>
            <thead><tr><th style={S.th}>Doc ID</th><th style={S.th}>Symbol</th><th style={S.th}>Type</th><th style={S.th}>Source</th><th style={S.th}>Version</th><th style={S.th}>Size</th><th style={S.th}>Checksum</th></tr></thead>
            <tbody>
              {data.map(d => (
                <tr key={d.doc_id}>
                  <td style={{ ...S.td, fontFamily: "monospace", fontSize: 11 }}>{d.doc_id}</td>
                  <td style={{ ...S.td, fontWeight: 700 }}>{d.symbol}</td>
                  <td style={S.td}><span style={{ ...S.pill, background: "#21262d", color: "#58a6ff" }}>{d.filing_type}</span></td>
                  <td style={{ ...S.td, color: "#8b949e" }}>{d.source}</td>
                  <td style={S.td}>v{d.version}</td>
                  <td style={S.td}>{(d.size_bytes / 1024).toFixed(1)} KB</td>
                  <td style={{ ...S.td, fontFamily: "monospace", fontSize: 10, color: "#8b949e" }}>{d.checksum}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function EnrichTab() {
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);

  const mut = useMutation({
    mutationFn: () => altIntelligenceApi.enrichText({ text, summary_sentences: 3 }),
    onSuccess: r => setResult(r.data),
  });

  const scoreBar = (v, lo = -1, hi = 1) => {
    const pct = Math.max(0, Math.min(1, (v - lo) / (hi - lo)));
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{ flex: 1, background: "#21262d", borderRadius: 3, height: 6 }}>
          <div style={{ width: `${pct * 100}%`, background: "#58a6ff", borderRadius: 3, height: 6 }} />
        </div>
        <span style={{ fontSize: 12, minWidth: 40, textAlign: "right" }}>{Number(v).toFixed(3)}</span>
      </div>
    );
  };

  return (
    <div>
      <div style={{ marginBottom: 14 }}>
        <label style={S.label}>Document Text</label>
        <textarea style={{ ...S.textarea, minHeight: 140 }} value={text} onChange={e => setText(e.target.value)}
          placeholder="Paste any institutional document, filing, transcript, or news article…" />
      </div>
      <button style={{ ...S.btn, opacity: !text || mut.isPending ? 0.6 : 1 }} onClick={() => mut.mutate()} disabled={!text || mut.isPending}>
        {mut.isPending ? "Enriching…" : "Enrich Document"}
      </button>
      {mut.error && <div style={{ ...S.err, marginTop: 12 }}>{mut.error.message}</div>}
      {result && (
        <div style={{ marginTop: 16 }}>
          <div style={S.card}>
            <div style={S.title}>AI Scores</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              {[["Sentiment", result.sentiment, -1, 1], ["Risk", result.risk, 0, 1], ["Uncertainty", result.uncertainty, 0, 1], ["Readability", result.readability, 0, 100], ["Novelty", result.novelty, 0, 1]].map(([name, val, lo, hi]) => (
                <div key={name}>
                  <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>{name}</div>
                  {scoreBar(val, lo, hi)}
                </div>
              ))}
            </div>
          </div>
          <div style={S.card}>
            <div style={S.title}>Summary</div>
            <p style={{ fontSize: 13, lineHeight: 1.7, margin: 0, color: "#c9d1d9" }}>{result.summary || "—"}</p>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div style={S.card}>
              <div style={S.title}>Topics ({result.topics?.length || 0})</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {(result.topics || []).map(t => <span key={t} style={{ ...S.pill, background: "#1f3245", color: "#58a6ff", border: "1px solid #1f6feb" }}>{t}</span>)}
                {!result.topics?.length && <span style={{ color: "#8b949e", fontSize: 12 }}>None detected</span>}
              </div>
            </div>
            <div style={S.card}>
              <div style={S.title}>Entities</div>
              {Object.entries(result.entities || {}).filter(([, v]) => v.length).map(([type, vals]) => (
                <div key={type} style={{ marginBottom: 8 }}>
                  <span style={{ fontSize: 11, color: "#8b949e", textTransform: "uppercase" }}>{type}</span>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 4 }}>
                    {vals.map(v => <span key={v} style={{ ...S.pill, background: "#21262d", color: "#e6edf3" }}>{v}</span>)}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div style={S.card}>
            <div style={S.title}>Top Keywords</div>
            <div style={{ overflowX: "auto" }}>
              <table style={S.table}>
                <thead><tr><th style={S.th}>Term</th><th style={S.th}>TF-IDF Score</th></tr></thead>
                <tbody>
                  {(result.keywords || []).slice(0, 15).map(kw => (
                    <tr key={kw.term}>
                      <td style={S.td}>{kw.term}</td>
                      <td style={S.td}>{Number(kw.score).toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const TABS = [{ key: "list", label: "Document Library" }, { key: "enrich", label: "AI Enrichment" }];

export default function AltDocumentViewer() {
  const [active, setActive] = useState("list");
  return (
    <div style={S.page}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Document Viewer</h1>
        <p style={{ color: "#8b949e", margin: "4px 0 0", fontSize: 13 }}>Browse and AI-enrich ingested institutional documents — SEC filings, transcripts, news</p>
      </div>
      <div style={{ display: "flex", borderBottom: "1px solid #30363d" }}>
        {TABS.map(t => <button key={t.key} onClick={() => setActive(t.key)} style={{ ...S.tab, ...(active === t.key ? S.tabActive : {}) }}>{t.label}</button>)}
      </div>
      <div style={{ ...S.card, borderTopLeftRadius: 0, marginTop: 0, borderTop: "none" }}>
        {active === "list" && <DocumentListTab />}
        {active === "enrich" && <EnrichTab />}
      </div>
    </div>
  );
}
