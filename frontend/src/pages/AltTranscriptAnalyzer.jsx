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
  btnGreen: { background: "#238636", border: "none", borderRadius: 6, color: "#fff", padding: "10px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer" },
  tab: { padding: "8px 18px", fontSize: 13, fontWeight: 600, cursor: "pointer", borderRadius: "6px 6px 0 0", border: "1px solid transparent", background: "transparent", color: "#8b949e", marginRight: 2 },
  tabActive: { background: "#161b22", border: "1px solid #30363d", borderBottom: "1px solid #161b22", color: "#e6edf3" },
  err: { background: "#2d1317", border: "1px solid #f85149", borderRadius: 6, color: "#f85149", padding: "10px 14px", fontSize: 13, marginBottom: 14 },
  pill: { display: "inline-block", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600 },
  metricBox: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 6, padding: "14px 12px", textAlign: "center" },
  metricValue: { fontSize: 22, fontWeight: 700, color: "#58a6ff", lineHeight: 1.2 },
  metricLabel: { fontSize: 11, color: "#8b949e", marginTop: 4, textTransform: "uppercase", letterSpacing: "0.06em" },
  textarea: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "9px 12px", fontSize: 12, width: "100%", boxSizing: "border-box", resize: "vertical", fontFamily: "monospace" },
};

const SAMPLE_TRANSCRIPT = `Good morning everyone. Thank you for joining our Q3 earnings call.

We are very pleased to report exceptional results this quarter. Revenue grew 23% year over year, significantly exceeding our guidance range. Our gross margins expanded to 45.2%, reflecting strong pricing power and operational efficiency improvements.

Looking ahead, we remain confident in our ability to sustain double-digit growth. We are raising our full-year guidance to reflect the strong momentum we see across all segments.

However, we do face some uncertainty in the macroeconomic environment. Currency headwinds may impact our international revenue, and supply chain constraints remain a risk we continue to monitor closely.

Question from analyst: Can you provide more color on the margin expansion?

CEO: Absolutely. The margin improvement reflects our continued focus on higher-value products and cost optimization initiatives we implemented last year.`;

function ScoreGauge({ value, lo = -1, hi = 1, color }) {
  const pct = Math.max(0, Math.min(100, ((value - lo) / (hi - lo)) * 100));
  const c = color || (value > 0.1 ? "#3fb950" : value < -0.1 ? "#f85149" : "#d29922");
  return (
    <div>
      <div style={{ background: "#21262d", borderRadius: 4, height: 8, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, background: c, height: "100%", transition: "width 0.4s" }} />
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 3, fontSize: 10, color: "#8b949e" }}>
        <span>{lo}</span><span style={{ color: c, fontWeight: 600 }}>{Number(value).toFixed(3)}</span><span>{hi}</span>
      </div>
    </div>
  );
}

function AnalysisTab() {
  const [transcript, setTranscript] = useState(SAMPLE_TRANSCRIPT);
  const [result, setResult] = useState(null);

  const enrichMut = useMutation({
    mutationFn: () => altIntelligenceApi.enrichText({ text: transcript, summary_sentences: 4 }),
    onSuccess: r => setResult(r.data),
  });

  // Feature computation for transcript positivity/uncertainty
  const featureMut = useMutation({
    mutationFn: () => altIntelligenceApi.computeFeatures({ symbol: "TRANSCRIPT", transcript_texts: [transcript] }),
    onSuccess: r => setResult(prev => ({ ...prev, features: r.data.features })),
  });

  const handleAnalyze = () => {
    enrichMut.mutate(undefined, {
      onSuccess: () => featureMut.mutate(),
    });
  };

  return (
    <div>
      <div style={{ marginBottom: 14 }}>
        <label style={S.label}>Earnings Call Transcript</label>
        <textarea style={{ ...S.textarea, minHeight: 200 }} value={transcript} onChange={e => setTranscript(e.target.value)} />
      </div>
      <button style={{ ...S.btnGreen, opacity: !transcript || enrichMut.isPending ? 0.6 : 1 }}
        onClick={handleAnalyze} disabled={!transcript || enrichMut.isPending}>
        {enrichMut.isPending ? "Analyzing…" : "Analyze Transcript"}
      </button>
      {enrichMut.error && <div style={{ ...S.err, marginTop: 12 }}>{enrichMut.error.message}</div>}
      {result && (
        <div style={{ marginTop: 16 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 16 }}>
            {[
              ["Sentiment", result.sentiment, -1, 1, null],
              ["Risk Score", result.risk, 0, 1, "#f85149"],
              ["Uncertainty", result.uncertainty, 0, 1, "#d29922"],
              ["Readability", result.readability, 0, 100, "#58a6ff"],
            ].map(([label, val, lo, hi, color]) => (
              <div key={label} style={S.metricBox}>
                <div style={{ ...S.metricValue, color: color || (val > 0.1 ? "#3fb950" : val < -0.1 ? "#f85149" : "#d29922") }}>
                  {Number(val).toFixed(3)}
                </div>
                <div style={S.metricLabel}>{label}</div>
                <div style={{ marginTop: 8 }}><ScoreGauge value={val} lo={lo} hi={hi} color={color} /></div>
              </div>
            ))}
          </div>
          {result.features && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12, marginBottom: 16 }}>
              <div style={S.metricBox}>
                <div style={{ ...S.metricValue, color: "#3fb950" }}>{Number(result.features.alt_transcript_positivity ?? 0).toFixed(3)}</div>
                <div style={S.metricLabel}>Transcript Positivity</div>
              </div>
              <div style={S.metricBox}>
                <div style={{ ...S.metricValue, color: "#d29922" }}>{Number(result.features.alt_transcript_uncertainty ?? 0).toFixed(3)}</div>
                <div style={S.metricLabel}>Transcript Uncertainty</div>
              </div>
            </div>
          )}
          <div style={S.card}>
            <div style={S.title}>AI-Generated Summary</div>
            <p style={{ fontSize: 13, lineHeight: 1.8, color: "#c9d1d9", margin: 0 }}>{result.summary || "—"}</p>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div style={S.card}>
              <div style={S.title}>Topics Detected</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {(result.topics || []).map(t => <span key={t} style={{ ...S.pill, background: "#1f3245", color: "#58a6ff", border: "1px solid #1f6feb" }}>{t}</span>)}
                {!(result.topics?.length) && <span style={{ fontSize: 12, color: "#8b949e" }}>None</span>}
              </div>
            </div>
            <div style={S.card}>
              <div style={S.title}>Named Entities</div>
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
        </div>
      )}
    </div>
  );
}

function QATab() {
  const [transcript, setTranscript] = useState(SAMPLE_TRANSCRIPT);
  const [question, setQuestion] = useState("What was the revenue growth?");
  const [result, setResult] = useState(null);

  const mut = useMutation({
    mutationFn: () => altIntelligenceApi.askQuestion({ question, text: transcript }),
    onSuccess: r => setResult(r.data),
  });

  return (
    <div>
      <div style={{ marginBottom: 14 }}>
        <label style={S.label}>Transcript Text</label>
        <textarea style={{ ...S.textarea, minHeight: 180 }} value={transcript} onChange={e => setTranscript(e.target.value)} />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 12, alignItems: "flex-end", marginBottom: 16 }}>
        <div>
          <label style={S.label}>Question</label>
          <input style={S.input} value={question} onChange={e => setQuestion(e.target.value)} placeholder="What did the CEO say about margins?" />
        </div>
        <button style={{ ...S.btn, opacity: !question || !transcript || mut.isPending ? 0.6 : 1 }}
          onClick={() => mut.mutate()} disabled={!question || !transcript || mut.isPending}>
          {mut.isPending ? "Searching…" : "Ask Question"}
        </button>
      </div>
      {mut.error && <div style={S.err}>{mut.error.message}</div>}
      {result && (
        <div style={S.card}>
          <div style={S.title}>Answer</div>
          {result.confidence > 0 ? (
            <>
              <p style={{ fontSize: 14, color: "#e6edf3", lineHeight: 1.7, margin: "0 0 12px" }}>{result.answer}</p>
              <div style={{ display: "flex", gap: 16, fontSize: 12, color: "#8b949e" }}>
                <span>Confidence: <strong style={{ color: result.confidence >= 0.6 ? "#3fb950" : "#d29922" }}>{(result.confidence * 100).toFixed(0)}%</strong></span>
                <span>Sentence: <strong style={{ color: "#58a6ff" }}>#{result.sentence_index}</strong></span>
              </div>
            </>
          ) : (
            <div style={{ color: "#8b949e", fontSize: 13 }}>
              No confident answer found. The transcript may not contain information relevant to this question.
              <div style={{ marginTop: 8, fontSize: 12 }}>Tip: Try rephrasing with keywords that appear in the text.</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const TABS = [{ key: "analysis", label: "Transcript Analysis" }, { key: "qa", label: "Q&A" }];

export default function AltTranscriptAnalyzer() {
  const [active, setActive] = useState("analysis");
  return (
    <div style={S.page}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Transcript Analyzer</h1>
        <p style={{ color: "#8b949e", margin: "4px 0 0", fontSize: 13 }}>
          Earnings call intelligence — sentiment, uncertainty, topic extraction, entity recognition, extractive Q&A
        </p>
      </div>
      <div style={{ display: "flex", borderBottom: "1px solid #30363d" }}>
        {TABS.map(t => <button key={t.key} onClick={() => setActive(t.key)} style={{ ...S.tab, ...(active === t.key ? S.tabActive : {}) }}>{t.label}</button>)}
      </div>
      <div style={{ ...S.card, borderTopLeftRadius: 0, marginTop: 0, borderTop: "none" }}>
        {active === "analysis" && <AnalysisTab />}
        {active === "qa" && <QATab />}
      </div>
    </div>
  );
}
