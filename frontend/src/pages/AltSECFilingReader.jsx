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
  btnGreen: { background: "#238636", border: "none", borderRadius: 6, color: "#fff", padding: "10px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer" },
  err: { background: "#2d1317", border: "1px solid #f85149", borderRadius: 6, color: "#f85149", padding: "10px 14px", fontSize: 13, marginBottom: 14 },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 12 },
  th: { padding: "8px 10px", textAlign: "left", color: "#8b949e", borderBottom: "1px solid #21262d", fontWeight: 600 },
  td: { padding: "7px 10px", borderBottom: "1px solid #21262d", color: "#e6edf3", verticalAlign: "top" },
  pill: { display: "inline-block", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600 },
  textarea: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "9px 12px", fontSize: 12, width: "100%", boxSizing: "border-box", resize: "vertical", fontFamily: "monospace" },
  sectionCard: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 6, padding: 14, marginBottom: 10 },
  sectionName: { fontSize: 12, fontWeight: 700, color: "#58a6ff", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" },
  preview: { fontSize: 12, color: "#8b949e", lineHeight: 1.6, marginBottom: 8, whiteSpace: "pre-wrap" },
  lineItem: { display: "flex", justifyContent: "space-between", padding: "3px 0", borderBottom: "1px dotted #21262d", fontSize: 12 },
  liKey: { color: "#8b949e" },
  liVal: { color: "#e6edf3", fontWeight: 600 },
};

const FILING_TYPES = ["10-K", "10-Q", "8-K", "Proxy", "13F", "13D", "Insider", "Transcript", "Other"];

const SECTION_COLORS = {
  income_statement: "#1f3245",
  balance_sheet: "#1a2a1a",
  cash_flow: "#2a2a1a",
  risk_factors: "#2d1317",
  mda: "#1a1a2d",
  business_description: "#21262d",
  executive_compensation: "#2a1a2a",
  share_buybacks: "#1a2a2a",
  guidance: "#2a2a1a",
};

export default function AltSECFilingReader() {
  const [docId, setDocId] = useState("");
  const [symbol, setSymbol] = useState("AAPL");
  const [filingType, setFilingType] = useState("10-K");
  const [activeSection, setActiveSection] = useState(null);
  const [parsed, setParsed] = useState(null);

  // Ingest + immediately parse
  const [text, setText] = useState("");
  const ingestMut = useMutation({
    mutationFn: async () => {
      const id = docId || `sec_${symbol}_${filingType}_${Date.now()}`;
      await altIntelligenceApi.ingestDocument({ doc_id: id, symbol: symbol.toUpperCase(), filing_type: filingType, text, source: "sec.gov" });
      return altIntelligenceApi.parseDocument(id, { symbol: symbol.toUpperCase(), filing_type: filingType }).then(r => ({ ...r.data, _docId: id }));
    },
    onSuccess: data => { setParsed(data); setActiveSection(Object.keys(data.sections || {})[0] || null); },
  });

  const sections = parsed ? Object.entries(parsed.sections || {}) : [];

  return (
    <div style={S.page}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>SEC Filing Reader</h1>
        <p style={{ color: "#8b949e", margin: "4px 0 0", fontSize: 13 }}>
          Parse SEC filings — income statements, balance sheets, risk factors, MD&A, executive compensation, guidance
        </p>
      </div>

      <div style={S.card}>
        <div style={S.title}>Load Filing</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 12, marginBottom: 14 }}>
          <div><label style={S.label}>Doc ID</label><input style={S.input} value={docId} onChange={e => setDocId(e.target.value)} placeholder="auto" /></div>
          <div><label style={S.label}>Symbol</label><input style={S.input} value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} /></div>
          <div><label style={S.label}>Filing Type</label><select style={S.select} value={filingType} onChange={e => setFilingType(e.target.value)}>{FILING_TYPES.map(t => <option key={t}>{t}</option>)}</select></div>
        </div>
        <div style={{ marginBottom: 14 }}>
          <label style={S.label}>Filing Text</label>
          <textarea style={{ ...S.textarea, minHeight: 160 }} value={text} onChange={e => setText(e.target.value)}
            placeholder="Paste full 10-K, 10-Q, 8-K, or other SEC filing text here…" />
        </div>
        <button style={{ ...S.btnGreen, opacity: !text || ingestMut.isPending ? 0.6 : 1 }} onClick={() => ingestMut.mutate()} disabled={!text || ingestMut.isPending}>
          {ingestMut.isPending ? "Parsing…" : "Parse Filing"}
        </button>
        {ingestMut.error && <div style={{ ...S.err, marginTop: 12 }}>{ingestMut.error.message}</div>}
      </div>

      {parsed && (
        <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: 16 }}>
          {/* Section navigation */}
          <div style={S.card}>
            <div style={S.title}>Sections ({sections.length})</div>
            {sections.map(([name]) => (
              <button key={name} onClick={() => setActiveSection(name)} style={{
                display: "block", width: "100%", padding: "8px 10px", marginBottom: 4, textAlign: "left",
                background: activeSection === name ? (SECTION_COLORS[name] || "#21262d") : "transparent",
                border: activeSection === name ? "1px solid #30363d" : "1px solid transparent",
                borderRadius: 6, color: activeSection === name ? "#e6edf3" : "#8b949e", fontSize: 12, cursor: "pointer",
                textTransform: "capitalize",
              }}>
                {name.replace(/_/g, " ")}
              </button>
            ))}
            {parsed.entities && Object.values(parsed.entities).some(v => v.length > 0) && (
              <button onClick={() => setActiveSection("__entities__")} style={{
                display: "block", width: "100%", padding: "8px 10px", marginBottom: 4, textAlign: "left",
                background: activeSection === "__entities__" ? "#21262d" : "transparent",
                border: activeSection === "__entities__" ? "1px solid #30363d" : "1px solid transparent",
                borderRadius: 6, color: activeSection === "__entities__" ? "#58a6ff" : "#8b949e", fontSize: 12, cursor: "pointer",
              }}>
                Extracted Entities
              </button>
            )}
          </div>

          {/* Section content */}
          <div style={S.card}>
            {activeSection === "__entities__" ? (
              <>
                <div style={S.title}>Extracted Entities</div>
                {Object.entries(parsed.entities || {}).filter(([, v]) => v.length > 0).map(([type, vals]) => (
                  <div key={type} style={{ marginBottom: 14 }}>
                    <div style={{ fontSize: 11, color: "#8b949e", textTransform: "uppercase", marginBottom: 6 }}>{type}</div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                      {vals.map(v => <span key={v} style={{ display: "inline-block", padding: "2px 8px", borderRadius: 4, fontSize: 11, background: "#21262d", color: "#e6edf3", border: "1px solid #30363d" }}>{v}</span>)}
                    </div>
                  </div>
                ))}
              </>
            ) : activeSection && parsed.sections[activeSection] ? (
              <>
                <div style={S.title}>{activeSection.replace(/_/g, " ")}</div>
                <div style={{ ...S.sectionCard, background: SECTION_COLORS[activeSection] || "#0d1117" }}>
                  <div style={S.preview}>{parsed.sections[activeSection].text_preview || "No preview available."}</div>
                </div>
                {parsed.sections[activeSection].line_items && Object.keys(parsed.sections[activeSection].line_items).length > 0 && (
                  <>
                    <div style={{ fontSize: 11, color: "#8b949e", textTransform: "uppercase", marginBottom: 8, marginTop: 12 }}>Extracted Line Items</div>
                    {Object.entries(parsed.sections[activeSection].line_items).map(([k, v]) => (
                      <div key={k} style={S.lineItem}>
                        <span style={S.liKey}>{k}</span>
                        <span style={S.liVal}>{typeof v === "number" ? v.toLocaleString() : String(v)}</span>
                      </div>
                    ))}
                  </>
                )}
              </>
            ) : (
              <div style={{ color: "#8b949e", fontSize: 13 }}>Select a section to view details.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
