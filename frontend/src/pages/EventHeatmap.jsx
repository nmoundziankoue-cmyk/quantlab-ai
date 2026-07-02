import { useState, useEffect } from "react";
import { eventsApi } from "../api/eventsApi";

const CARD = { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" };
const BTN = (a) => ({ padding: "7px 16px", borderRadius: 6, border: "none", cursor: "pointer", fontSize: 12, background: a ? "#1f6feb" : "#21262d", color: "#f0f6fc", fontFamily: "monospace" });

function interpolateColor(t) {
  // Dark blue → bright blue → white
  const r = Math.round(13 + t * 242);
  const g = Math.round(17 + t * 239);
  const b = Math.round(23 + t * 232);
  return `rgb(${r},${g},${b})`;
}

function HeatCell({ item, max }) {
  const t = max > 0 ? item.count / max : 0;
  const bg = t === 0 ? "#0d1117" : `rgba(31,111,235,${0.08 + t * 0.85})`;
  const textColor = t > 0.6 ? "#f0f6fc" : t > 0.2 ? "#c9d1d9" : "#8b949e";
  return (
    <div title={`${item.label}\nTotal: ${item.count}\nCorporate: ${item.corporate || 0}\nMacro: ${item.macro || 0}`}
      style={{ background: bg, border: "1px solid #21262d", borderRadius: 4, padding: "8px 6px", textAlign: "center", minWidth: 56, cursor: "default" }}>
      <div style={{ fontSize: 9, color: textColor === "#f0f6fc" ? "#c9d1d9" : "#8b949e", marginBottom: 2 }}>{item.label}</div>
      <div style={{ fontSize: 16, fontWeight: 700, color: textColor, lineHeight: 1 }}>{item.count}</div>
      {item.corporate > 0 && <div style={{ fontSize: 9, color: "#3fb950", marginTop: 2 }}>c:{item.corporate}</div>}
      {item.macro > 0 && <div style={{ fontSize: 9, color: "#e3b341" }}>m:{item.macro}</div>}
    </div>
  );
}

function LegendBar() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
      <span style={{ fontSize: 11, color: "#8b949e" }}>0</span>
      <div style={{ height: 10, flex: 1, maxWidth: 200, background: "linear-gradient(to right, #0d1117, rgba(31,111,235,0.93))", borderRadius: 5 }} />
      <span style={{ fontSize: 11, color: "#8b949e" }}>max</span>
      <span style={{ fontSize: 11, color: "#8b949e", marginLeft: 16 }}>
        <span style={{ color: "#3fb950" }}>■</span> corporate &nbsp;
        <span style={{ color: "#e3b341" }}>■</span> macro
      </span>
    </div>
  );
}

export default function EventHeatmap() {
  const [grouping, setGrouping] = useState("day");
  const [data, setData] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [hr, sr] = await Promise.all([
        eventsApi.heatmap({ grouping }),
        eventsApi.statistics(),
      ]);
      setData(hr.data || []);
      setStats(sr.data);
    } catch {
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [grouping]);

  const max = data.reduce((m, d) => Math.max(m, d.count), 0);
  const totalEvents = data.reduce((s, d) => s + d.count, 0);
  const periodsWithEvents = data.filter((d) => d.count > 0).length;

  return (
    <div style={{ padding: 24, color: "#f0f6fc", fontFamily: "monospace" }}>
      <div style={{ fontSize: 11, color: "#58a6ff", letterSpacing: "0.1em", marginBottom: 4 }}>M15</div>
      <h1 style={{ margin: "0 0 4px", fontSize: 22 }}>Event Heatmap</h1>
      <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 20 }}>Event density over time — darker cells indicate more activity</div>

      <div style={{ display: "flex", gap: 8, marginBottom: 20, alignItems: "center" }}>
        <span style={{ fontSize: 12, color: "#8b949e" }}>Group by:</span>
        {["day","week","month","quarter","year"].map((g) => (
          <button key={g} style={BTN(grouping === g)} onClick={() => setGrouping(g)}>{g}</button>
        ))}
      </div>

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 20 }}>
        {[
          ["Periods", data.length, "#58a6ff"],
          ["Active Periods", periodsWithEvents, "#3fb950"],
          ["Total Events", totalEvents, "#e3b341"],
          ["Peak", max, "#f85149"],
        ].map(([l, v, c]) => (
          <div key={l} style={{ ...CARD, minWidth: 100, flex: 1 }}>
            <div style={{ fontSize: 11, color: "#8b949e" }}>{l}</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: c }}>{v}</div>
          </div>
        ))}
      </div>

      <div style={CARD}>
        <LegendBar />
        {loading ? (
          <div style={{ color: "#8b949e" }}>Loading heatmap…</div>
        ) : data.length === 0 ? (
          <div style={{ color: "#8b949e" }}>No data. Add corporate or macro events first.</div>
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
            {data.map((item, i) => <HeatCell key={i} item={item} max={max} />)}
          </div>
        )}
      </div>

      {stats && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 16 }}>
          <div style={CARD}>
            <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 10 }}>CORPORATE EVENT TYPES</div>
            {Object.entries(stats.corporate?.by_type || {})
              .sort((a, b) => b[1] - a[1])
              .slice(0, 10)
              .map(([k, v]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "3px 0", borderBottom: "1px solid #161b22", fontSize: 11 }}>
                  <span style={{ color: "#c9d1d9" }}>{k.replace(/_/g," ")}</span>
                  <span style={{ color: "#3fb950" }}>{v}</span>
                </div>
              ))}
          </div>
          <div style={CARD}>
            <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 10 }}>MACRO EVENT TYPES</div>
            {Object.entries(stats.macro?.by_type || {})
              .sort((a, b) => b[1] - a[1])
              .slice(0, 10)
              .map(([k, v]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "3px 0", borderBottom: "1px solid #161b22", fontSize: 11 }}>
                  <span style={{ color: "#c9d1d9" }}>{k.replace(/_/g," ")}</span>
                  <span style={{ color: "#e3b341" }}>{v}</span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
