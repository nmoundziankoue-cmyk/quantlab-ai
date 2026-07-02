import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { altIntelligenceApi } from "../api/altIntelligenceApi";

const S = {
  page: { padding: 28, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" },
  card: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20, marginBottom: 16 },
  title: { fontSize: 13, fontWeight: 700, color: "#8b949e", letterSpacing: "0.06em", marginBottom: 14, textTransform: "uppercase" },
  label: { fontSize: 12, color: "#8b949e", marginBottom: 4, display: "block" },
  input: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "9px 12px", fontSize: 13, width: "100%", boxSizing: "border-box" },
  btn: { background: "#1f6feb", border: "none", borderRadius: 6, color: "#fff", padding: "10px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer" },
  err: { background: "#2d1317", border: "1px solid #f85149", borderRadius: 6, color: "#f85149", padding: "10px 14px", fontSize: 13, marginBottom: 14 },
  pill: { display: "inline-block", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600 },
  textarea: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "9px 12px", fontSize: 12, width: "100%", boxSizing: "border-box", resize: "vertical", fontFamily: "monospace" },
};

const SEVERITY_COLORS = {
  CRITICAL: { bg: "#2d1317", border: "#f85149", dot: "#f85149", text: "#f85149" },
  HIGH:     { bg: "#2d1f0a", border: "#d29922", dot: "#d29922", text: "#d29922" },
  MEDIUM:   { bg: "#1f3245", border: "#1f6feb", dot: "#58a6ff", text: "#58a6ff" },
  LOW:      { bg: "#1a2a1a", border: "#3fb950", dot: "#3fb950", text: "#3fb950" },
};

const SAMPLE_TEXT = `The Board announced that John Smith will step down as Chief Executive Officer effective December 31st. Mary Johnson, current COO, has been appointed as new CEO.

The company reported Q3 earnings of $2.45 per share, significantly beating consensus estimates of $2.10.

A new share buyback program of $2 billion was authorized by the board.

Company X has entered into a merger agreement to acquire Target Corp for $5.2 billion in cash. The transaction is expected to close in Q1 2025.

The FDA has approved the company's new drug NDA-approved filing for Phase 3 treatment. Patent approval confirmed for key technology process.`;

export default function AltEventTimeline() {
  const [text, setText] = useState(SAMPLE_TEXT);
  const [symbol, setSymbol] = useState("AAPL");
  const [result, setResult] = useState(null);
  const [filterSeverity, setFilterSeverity] = useState("ALL");

  const mut = useMutation({
    mutationFn: () => altIntelligenceApi.detectEvents({ text, symbol }),
    onSuccess: r => setResult(r.data),
  });

  const events = (result?.events || []).filter(e => filterSeverity === "ALL" || e.severity === filterSeverity);

  const severityCounts = (result?.events || []).reduce((acc, e) => { acc[e.severity] = (acc[e.severity] || 0) + 1; return acc; }, {});

  return (
    <div style={S.page}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Event Timeline</h1>
        <p style={{ color: "#8b949e", margin: "4px 0 0", fontSize: 13 }}>
          Real-time event detection — earnings, M&A, CEO changes, buybacks, FDA approvals, credit events, supply chain disruptions
        </p>
      </div>

      <div style={S.card}>
        <div style={S.title}>Detect Events</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 160px auto", gap: 12, marginBottom: 14, alignItems: "flex-end" }}>
          <div><label style={S.label}>Symbol</label><input style={S.input} value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} placeholder="AAPL" /></div>
          <div style={{ gridColumn: "span 2" }} />
        </div>
        <div style={{ marginBottom: 14 }}>
          <label style={S.label}>Document / News Text</label>
          <textarea style={{ ...S.textarea, minHeight: 160 }} value={text} onChange={e => setText(e.target.value)} />
        </div>
        <button style={{ ...S.btn, opacity: !text || mut.isPending ? 0.6 : 1 }} onClick={() => mut.mutate()} disabled={!text || mut.isPending}>
          {mut.isPending ? "Detecting…" : "Detect Events"}
        </button>
      </div>

      {mut.error && <div style={S.err}>{mut.error.message}</div>}

      {result && (
        <>
          {/* Summary metrics */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 10, marginBottom: 16 }}>
            {[["TOTAL", result.event_count, "#58a6ff"], ["CRITICAL", severityCounts.CRITICAL || 0, "#f85149"], ["HIGH", severityCounts.HIGH || 0, "#d29922"], ["MEDIUM", severityCounts.MEDIUM || 0, "#58a6ff"], ["LOW", severityCounts.LOW || 0, "#3fb950"]].map(([label, count, color]) => (
              <div key={label} style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: "14px 12px", textAlign: "center" }}>
                <div style={{ fontSize: 22, fontWeight: 700, color, lineHeight: 1.2 }}>{count}</div>
                <div style={{ fontSize: 11, color: "#8b949e", marginTop: 4, letterSpacing: "0.06em" }}>{label}</div>
              </div>
            ))}
          </div>

          {/* Severity filter */}
          <div style={{ display: "flex", gap: 6, marginBottom: 14 }}>
            {["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map(s => (
              <button key={s} onClick={() => setFilterSeverity(s)} style={{
                padding: "5px 14px", fontSize: 12, fontWeight: 600, borderRadius: 6, cursor: "pointer",
                background: filterSeverity === s ? (SEVERITY_COLORS[s]?.bg || "#21262d") : "#0d1117",
                border: `1px solid ${filterSeverity === s ? (SEVERITY_COLORS[s]?.border || "#58a6ff") : "#30363d"}`,
                color: filterSeverity === s ? (SEVERITY_COLORS[s]?.text || "#e6edf3") : "#8b949e",
              }}>{s}</button>
            ))}
          </div>

          {/* Timeline */}
          {events.length === 0 ? (
            <div style={{ ...S.card, textAlign: "center", padding: 40, color: "#8b949e" }}>
              No {filterSeverity !== "ALL" ? filterSeverity.toLowerCase() : ""} events detected in the provided text.
            </div>
          ) : (
            <div style={{ position: "relative" }}>
              <div style={{ position: "absolute", left: 20, top: 0, bottom: 0, width: 2, background: "#21262d", zIndex: 0 }} />
              {events.map((ev, i) => {
                const sc = SEVERITY_COLORS[ev.severity] || SEVERITY_COLORS.LOW;
                return (
                  <div key={i} style={{ display: "flex", gap: 20, marginBottom: 14, position: "relative", zIndex: 1 }}>
                    <div style={{ width: 42, height: 42, borderRadius: "50%", background: sc.bg, border: `2px solid ${sc.border}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                      <div style={{ width: 10, height: 10, borderRadius: "50%", background: sc.dot }} />
                    </div>
                    <div style={{ ...S.card, flex: 1, marginBottom: 0, borderLeft: `3px solid ${sc.border}` }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                        <div>
                          <span style={{ fontSize: 14, fontWeight: 700, color: "#e6edf3" }}>{ev.event_type.replace(/_/g, " ")}</span>
                          <span style={{ marginLeft: 10, ...S.pill, background: sc.bg, color: sc.text, border: `1px solid ${sc.border}` }}>{ev.severity}</span>
                        </div>
                        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                          <span style={{ fontSize: 12, color: "#8b949e" }}>Confidence:</span>
                          <span style={{ fontSize: 13, fontWeight: 700, color: ev.confidence >= 0.8 ? "#3fb950" : ev.confidence >= 0.6 ? "#d29922" : "#f85149" }}>
                            {(ev.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                      <p style={{ fontSize: 12, color: "#8b949e", margin: "0 0 8px", lineHeight: 1.6, fontStyle: "italic" }}>"{ev.snippet}"</p>
                      {ev.matched_patterns?.length > 0 && (
                        <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                          {ev.matched_patterns.map(p => <span key={p} style={{ ...S.pill, background: "#21262d", color: "#8b949e", fontSize: 10 }}>{p}</span>)}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}
