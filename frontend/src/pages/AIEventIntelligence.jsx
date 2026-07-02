import { useState, useEffect } from "react";
import { eventsApi } from "../api/eventsApi";

const CARD = { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" };
const INPUT = { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", padding: "6px 10px", fontSize: 12, fontFamily: "monospace" };
const BTN = (a) => ({ padding: "7px 16px", borderRadius: 6, border: "none", cursor: "pointer", fontSize: 12, background: a ? "#1f6feb" : "#21262d", color: "#f0f6fc", fontFamily: "monospace" });

function Section({ title, content, color = "#c9d1d9" }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 11, letterSpacing: "0.08em", color: "#8b949e", marginBottom: 6, textTransform: "uppercase" }}>{title}</div>
      <div style={{ fontSize: 12, color, lineHeight: 1.7 }}>{content}</div>
    </div>
  );
}

function BulletList({ title, items, color = "#c9d1d9" }) {
  if (!items || items.length === 0) return null;
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 11, letterSpacing: "0.08em", color: "#8b949e", marginBottom: 6, textTransform: "uppercase" }}>{title}</div>
      <ul style={{ margin: 0, paddingLeft: 18, color, fontSize: 12, lineHeight: 1.7 }}>
        {items.map((item, i) => <li key={i}>{item}</li>)}
      </ul>
    </div>
  );
}

function ScoreGauge({ value, label, color }) {
  return (
    <div style={{ textAlign: "center" }}>
      <svg width="80" height="80" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="32" fill="none" stroke="#21262d" strokeWidth="6" />
        <circle cx="40" cy="40" r="32" fill="none" stroke={color} strokeWidth="6"
          strokeDasharray={`${value * 201} 201`} strokeLinecap="round"
          transform="rotate(-90 40 40)" />
        <text x="40" y="46" textAnchor="middle" fill={color} fontSize="14" fontWeight="700" fontFamily="monospace">
          {(value * 100).toFixed(0)}
        </text>
      </svg>
      <div style={{ fontSize: 10, color: "#8b949e", marginTop: 2 }}>{label}</div>
    </div>
  );
}

export default function AIEventIntelligence() {
  const [events, setEvents] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [intel, setIntel] = useState(null);
  const [score, setScore] = useState(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState("corporate");

  useEffect(() => {
    eventsApi.listCorporate({ limit: 50 }).then((r) => {
      const evs = r.data || [];
      setEvents(evs);
      if (evs.length > 0) setSelectedId(evs[0].id);
    }).catch(() => setEvents([]));
  }, []);

  const analyse = async () => {
    if (!selectedId) return;
    setLoading(true);
    setIntel(null);
    setScore(null);
    try {
      const [ir, sr] = await Promise.all([
        eventsApi.getIntelligence({ event_id: selectedId }),
        eventsApi.intelligenceScore(selectedId),
      ]);
      setIntel(ir.data);
      setScore(sr.data);
    } catch (e) {
      alert(e?.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 24, color: "#f0f6fc", fontFamily: "monospace" }}>
      <div style={{ fontSize: 11, color: "#d2a8ff", letterSpacing: "0.1em", marginBottom: 4 }}>M15 — AI INTELLIGENCE</div>
      <h1 style={{ margin: "0 0 4px", fontSize: 22 }}>AI Event Intelligence</h1>
      <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 20 }}>Deterministic qualitative analysis: bull/bear case, risks, historical analogues, portfolio implications</div>

      <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        {["corporate","macro"].map((t) => <button key={t} style={BTN(tab === t)} onClick={() => setTab(t)}>{t} events</button>)}
      </div>

      {tab === "corporate" && (
        <div style={{ display: "flex", gap: 10, marginBottom: 20, alignItems: "flex-end" }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>Select Event</div>
            <select style={{ ...INPUT, width: "100%", maxWidth: 500 }} value={selectedId} onChange={(e) => setSelectedId(e.target.value)}>
              {events.length === 0 && <option value="">No events available — add corporate events first</option>}
              {events.map((ev) => (
                <option key={ev.id} value={ev.id}>
                  {ev.ticker} — {ev.event_type?.replace(/_/g," ")} ({new Date(ev.timestamp * 1000).toLocaleDateString()})
                </option>
              ))}
            </select>
          </div>
          <button style={BTN(true)} disabled={!selectedId || loading} onClick={analyse}>
            {loading ? "Analysing…" : "Generate Intelligence"}
          </button>
        </div>
      )}

      {intel && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 16 }}>
          <div>
            <div style={{ ...CARD, marginBottom: 12, borderLeft: "3px solid #d2a8ff" }}>
              <Section title="Executive Summary" content={intel.executive_summary} color="#f0f6fc" />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
              <div style={{ ...CARD, borderLeft: "3px solid #3fb950" }}>
                <Section title="Bull Case" content={intel.bull_case} color="#c9d1d9" />
              </div>
              <div style={{ ...CARD, borderLeft: "3px solid #f85149" }}>
                <Section title="Bear Case" content={intel.bear_case} color="#c9d1d9" />
              </div>
            </div>
            <div style={{ ...CARD, marginBottom: 12 }}>
              <Section title="Neutral View" content={intel.neutral_view} />
            </div>
            <div style={{ ...CARD, marginBottom: 12 }}>
              <BulletList title="Key Risks" items={intel.key_risks} color="#f8a093" />
              <BulletList title="Key Opportunities" items={intel.key_opportunities} color="#79c0ff" />
            </div>
            <div style={{ ...CARD, marginBottom: 12 }}>
              <Section title="Portfolio Implications" content={intel.portfolio_implications} />
              <Section title="Sector Implications" content={intel.sector_implications} />
              <Section title="Macro Implications" content={intel.macro_implications} />
            </div>
            <div style={{ ...CARD }}>
              <BulletList title="Historical Analogues" items={intel.historical_analogues} color="#e3b341" />
            </div>
          </div>

          <div>
            {score && (
              <div style={CARD}>
                <div style={{ fontSize: 12, fontWeight: 700, color: "#d2a8ff", marginBottom: 14 }}>Intelligence Score</div>
                <div style={{ display: "flex", justifyContent: "space-around", marginBottom: 16 }}>
                  <ScoreGauge value={score.overall_score} label="Overall" color="#d2a8ff" />
                  <ScoreGauge value={score.positive_score} label="Positive" color="#3fb950" />
                  <ScoreGauge value={score.negative_score} label="Negative" color="#f85149" />
                </div>
                {[
                  ["Importance", score.importance_score, "#e3b341"],
                  ["Novelty", score.novelty_score, "#58a6ff"],
                  ["Exp. Volatility", score.expected_volatility, "#f85149"],
                  ["Exp. Liquidity", score.expected_liquidity, "#3fb950"],
                  ["Inst. Interest", score.institutional_interest, "#d2a8ff"],
                  ["Portfolio Rel.", score.portfolio_relevance, "#79c0ff"],
                  ["Confidence", score.confidence_score, "#8b949e"],
                ].map(([l, v, c]) => (
                  <div key={l} style={{ display: "flex", alignItems: "center", marginBottom: 8, gap: 8 }}>
                    <span style={{ fontSize: 11, color: "#8b949e", width: 100, flexShrink: 0 }}>{l}</span>
                    <div style={{ flex: 1, background: "#161b22", borderRadius: 3, height: 5 }}>
                      <div style={{ width: `${Math.min(100, v * 100)}%`, height: "100%", background: c, borderRadius: 3 }} />
                    </div>
                    <span style={{ fontSize: 11, color: c, width: 36, textAlign: "right" }}>{(v * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {!intel && !loading && (
        <div style={{ ...CARD, color: "#8b949e" }}>
          {events.length === 0
            ? "Add corporate events first, then select one here to generate AI intelligence."
            : "Select an event above and click Generate Intelligence."}
        </div>
      )}
    </div>
  );
}
