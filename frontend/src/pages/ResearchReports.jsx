import { useState } from "react";
import { useReportSections, useGenerateReport, useExportReportHtml } from "../hooks/useReports";

const S = {
  page: { padding: 24, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" },
  title: { fontSize: 22, fontWeight: 700, marginBottom: 20 },
  grid: { display: "grid", gridTemplateColumns: "300px 1fr", gap: 16 },
  card: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20 },
  cardTitle: { fontSize: 13, color: "#8b949e", fontWeight: 600, marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.05em" },
  input: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "8px 12px", color: "#e6edf3", fontSize: 13, width: "100%", outline: "none", marginBottom: 10, boxSizing: "border-box" },
  btn: (color = "#238636") => ({ background: color, border: "none", borderRadius: 6, padding: "8px 16px", color: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 600, marginRight: 8, marginBottom: 8 }),
  sectionBtn: (active) => ({ padding: "6px 10px", borderRadius: 4, cursor: "pointer", fontSize: 12, marginBottom: 4, background: active ? "#1f6feb" : "#21262d", color: active ? "#fff" : "#8b949e", display: "block", width: "100%", textAlign: "left", border: "none" }),
  section: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: 16, marginBottom: 12, whiteSpace: "pre-wrap", fontSize: 13, lineHeight: 1.7, color: "#e6edf3" },
  sectionTitle: { fontSize: 14, fontWeight: 700, color: "#58a6ff", marginBottom: 8 },
};

export default function ResearchReports() {
  const { data: sections = [] } = useReportSections();
  const generateReport = useGenerateReport();
  const exportHtml = useExportReportHtml();

  const [ticker, setTicker] = useState("AAPL");
  const [recommendation, setRecommendation] = useState("BUY");
  const [targetPrice, setTargetPrice] = useState("");
  const [selectedSections, setSelectedSections] = useState([]);
  const [report, setReport] = useState(null);
  const [activeSection, setActiveSection] = useState(null);

  const toggleSection = (s) => {
    setSelectedSections((prev) => prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]);
  };

  const handleGenerate = () => {
    const params = { ticker, recommendation, ...(targetPrice && { target_price: targetPrice }) };
    if (selectedSections.length > 0) params.sections = selectedSections.join(",");
    generateReport.mutate(params, { onSuccess: (r) => { setReport(r); setActiveSection(Object.keys(r.sections || {})[0] || null); } });
  };

  const handleExportHtml = () => {
    if (!report) return;
    const md = Object.values(report.sections || {}).join("\n\n");
    exportHtml.mutate({ content: md }, {
      onSuccess: (r) => {
        const blob = new Blob([r.html || r], { type: "text/html" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a"); a.href = url; a.download = `${ticker}-report.html`; a.click();
      }
    });
  };

  return (
    <div style={S.page}>
      <div style={S.title}>Institutional Research Reports</div>
      <div style={S.grid}>
        <div>
          <div style={S.card}>
            <div style={S.cardTitle}>Report Configuration</div>
            <input style={S.input} placeholder="Ticker (e.g. AAPL)" value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} />
            <select style={S.input} value={recommendation} onChange={(e) => setRecommendation(e.target.value)}>
              {["BUY", "OUTPERFORM", "NEUTRAL", "UNDERPERFORM", "SELL"].map((r) => <option key={r}>{r}</option>)}
            </select>
            <input style={S.input} placeholder="Target Price (optional)" value={targetPrice} onChange={(e) => setTargetPrice(e.target.value)} />
            <button style={S.btn()} onClick={handleGenerate} disabled={generateReport.isPending}>
              {generateReport.isPending ? "Generating..." : "Generate Report"}
            </button>
            {report && (
              <button style={S.btn("#1f6feb")} onClick={handleExportHtml}>Export HTML</button>
            )}
          </div>

          {sections.length > 0 && (
            <div style={{ ...S.card, marginTop: 12 }}>
              <div style={S.cardTitle}>Sections ({sections.length})</div>
              <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 8 }}>Click to include/exclude</div>
              {sections.map((s) => (
                <button key={s} style={S.sectionBtn(selectedSections.includes(s))} onClick={() => toggleSection(s)}>
                  {s.replace(/_/g, " ")}
                </button>
              ))}
              {selectedSections.length > 0 && (
                <button style={{ ...S.btn("#21262d"), border: "1px solid #30363d", marginTop: 4 }} onClick={() => setSelectedSections([])}>Clear All</button>
              )}
            </div>
          )}
        </div>

        <div>
          {!report && !generateReport.isPending && (
            <div style={{ ...S.card, textAlign: "center", padding: 60 }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>📊</div>
              <div style={{ color: "#8b949e", fontSize: 14 }}>Configure and generate a 14-section institutional research report</div>
            </div>
          )}
          {generateReport.isPending && (
            <div style={{ ...S.card, textAlign: "center", padding: 60 }}>
              <div style={{ color: "#58a6ff", fontSize: 14 }}>Generating report for {ticker}...</div>
            </div>
          )}
          {report && (
            <div>
              <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
                {Object.keys(report.sections || {}).map((s) => (
                  <button key={s} style={{ ...S.btn(activeSection === s ? "#1f6feb" : "#21262d"), border: "1px solid #30363d", padding: "5px 10px", fontSize: 11, marginBottom: 0, marginRight: 4 }} onClick={() => setActiveSection(s)}>
                    {s.replace(/_/g, " ")}
                  </button>
                ))}
              </div>
              {activeSection && report.sections[activeSection] && (
                <div style={S.card}>
                  <div style={S.sectionTitle}>{activeSection.replace(/_/g, " ").toUpperCase()}</div>
                  <div style={S.section}>{report.sections[activeSection]}</div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
