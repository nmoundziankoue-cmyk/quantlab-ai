import { useState, useEffect } from "react";
import { eventsApi } from "../api/eventsApi";

const CARD = { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" };
const BTN = (a) => ({ padding: "7px 16px", borderRadius: 6, border: "none", cursor: "pointer", fontSize: 12, background: a ? "#1f6feb" : "#21262d", color: "#f0f6fc", fontFamily: "monospace" });

const DIR_COLOR = { bullish: "#3fb950", bearish: "#f85149", neutral: "#8b949e" };
const THEME_COLORS = {
  macro: "#58a6ff", sector: "#e3b341", regulatory: "#f78166", technology: "#79c0ff",
  ai: "#d2a8ff", healthcare: "#56d364", energy: "#e3b341", financial: "#ffa657",
  geopolitical: "#f85149", supply_chain: "#8b949e", earnings: "#3fb950", corporate_action: "#58a6ff",
};

function ScoreBar({ value, color }) {
  return (
    <div style={{ background: "#161b22", borderRadius: 3, height: 5, overflow: "hidden", flex: 1, marginLeft: 8 }}>
      <div style={{ width: `${Math.min(100, value * 100)}%`, height: "100%", background: color, borderRadius: 3 }} />
    </div>
  );
}

function CatalystCard({ c }) {
  const dir = c.direction;
  const color = DIR_COLOR[dir] || "#8b949e";
  const themeColor = THEME_COLORS[c.theme] || "#8b949e";
  return (
    <div style={{ ...CARD, marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
        <div>
          <span style={{ fontWeight: 700, fontSize: 15, color: "#f0f6fc" }}>{c.ticker}</span>
          <span style={{ fontSize: 11, color: themeColor, padding: "2px 8px", border: `1px solid ${themeColor}`, borderRadius: 4, marginLeft: 10 }}>{c.theme}</span>
        </div>
        <span style={{ fontSize: 13, fontWeight: 700, color, padding: "3px 12px", border: `1px solid ${color}`, borderRadius: 4 }}>
          {dir.toUpperCase()}
        </span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 8 }}>
        {[
          ["Composite", c.composite_score, "#58a6ff"],
          ["Importance", c.importance_score, "#e3b341"],
          ["Severity", c.severity_score, "#f85149"],
          ["Confidence", c.confidence_score, "#3fb950"],
        ].map(([l, v, col]) => (
          <div key={l} style={{ display: "flex", alignItems: "center" }}>
            <span style={{ fontSize: 11, color: "#8b949e", width: 80, flexShrink: 0 }}>{l}</span>
            <ScoreBar value={v} color={col} />
            <span style={{ fontSize: 11, fontWeight: 700, color: col, marginLeft: 8, width: 40, textAlign: "right" }}>{v.toFixed(3)}</span>
          </div>
        ))}
      </div>
      {c.tags?.length > 0 && (
        <div style={{ marginTop: 8, display: "flex", gap: 5, flexWrap: "wrap" }}>
          {c.tags.slice(0, 6).map((t) => (
            <span key={t} style={{ fontSize: 10, color: "#8b949e", padding: "1px 6px", background: "#161b22", borderRadius: 3 }}>{t}</span>
          ))}
        </div>
      )}
    </div>
  );
}

export default function CatalystDashboard() {
  const [catalysts, setCatalysts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [direction, setDirection] = useState("");
  const [limit, setLimit] = useState(20);
  const [clusters, setClusters] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const params = { limit };
      if (direction) params.direction = direction;
      const [cr, cl] = await Promise.all([
        eventsApi.listCatalysts(params),
        eventsApi.clusters({ limit: 100 }),
      ]);
      setCatalysts(cr.data || []);
      setClusters(cl.data);
    } catch {
      setCatalysts([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [direction, limit]);

  const bullCount = catalysts.filter((c) => c.direction === "bullish").length;
  const bearCount = catalysts.filter((c) => c.direction === "bearish").length;
  const neutralCount = catalysts.filter((c) => c.direction === "neutral").length;

  return (
    <div style={{ padding: 24, color: "#f0f6fc", fontFamily: "monospace" }}>
      <div style={{ fontSize: 11, color: "#58a6ff", letterSpacing: "0.1em", marginBottom: 4 }}>M15</div>
      <h1 style={{ margin: "0 0 20px", fontSize: 22 }}>Catalyst Dashboard</h1>

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 20 }}>
        {[
          ["Bullish", bullCount, "#3fb950"],
          ["Bearish", bearCount, "#f85149"],
          ["Neutral", neutralCount, "#8b949e"],
        ].map(([l, v, c]) => (
          <div key={l} style={{ ...CARD, flex: 1, minWidth: 120 }}>
            <div style={{ fontSize: 11, color: "#8b949e" }}>{l} Catalysts</div>
            <div style={{ fontSize: 24, fontWeight: 700, color: c }}>{v}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 20, alignItems: "center" }}>
        <div style={{ fontSize: 12, color: "#8b949e" }}>Direction:</div>
        {["","bullish","bearish","neutral"].map((d) => (
          <button key={d || "all"} style={BTN(direction === d)} onClick={() => setDirection(d)}>
            {d || "All"}
          </button>
        ))}
        <select style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", padding: "6px 10px", fontSize: 12, fontFamily: "monospace" }}
          value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
          {[10, 20, 50].map((n) => <option key={n} value={n}>{n} results</option>)}
        </select>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: 16 }}>
        <div>
          {loading ? (
            <div style={{ color: "#8b949e" }}>Loading catalysts…</div>
          ) : catalysts.length === 0 ? (
            <div style={{ ...CARD, color: "#8b949e" }}>No catalysts found. Add corporate events first.</div>
          ) : (
            catalysts.map((c, i) => <CatalystCard key={c.event_id || i} c={c} />)
          )}
        </div>

        <div>
          {clusters && (
            <div style={CARD}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "#58a6ff", marginBottom: 12 }}>Event Clusters</div>
              {Object.entries(clusters.distribution || {}).map(([k, v]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: "1px solid #161b22", fontSize: 11 }}>
                  <span style={{ color: THEME_COLORS[k] || "#8b949e" }}>{k.replace(/_/g," ")}</span>
                  <span style={{ color: "#f0f6fc", fontWeight: 700 }}>{v}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
