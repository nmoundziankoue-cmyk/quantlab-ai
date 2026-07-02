import { useState } from "react";
import { useAltDataEvents, useIngestEvent, useBatchIngest, useTickerTimeline, useTickerSentiment, useImportanceFeed, useAltDataClusters, useBuildClusters } from "../hooks/useAlternativeData";
import useAlternativeDataStore from "../store/useAlternativeDataStore";

const S = {
  page: { padding: 24, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" },
  title: { fontSize: 22, fontWeight: 700, marginBottom: 20 },
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: 16, marginBottom: 24 },
  card: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20 },
  cardTitle: { fontSize: 13, color: "#8b949e", fontWeight: 600, marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.05em" },
  input: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "8px 12px", color: "#e6edf3", fontSize: 13, width: "100%", outline: "none", marginBottom: 8, boxSizing: "border-box" },
  select: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "8px 12px", color: "#e6edf3", fontSize: 13, width: "100%", outline: "none", marginBottom: 8, boxSizing: "border-box" },
  btn: (color = "#238636") => ({ background: color, border: "none", borderRadius: 6, padding: "8px 14px", color: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 600 }),
  row: { padding: "10px 0", borderBottom: "1px solid #21262d" },
  badge: (color) => ({ background: color + "22", color, borderRadius: 4, padding: "2px 8px", fontSize: 11, fontWeight: 600, marginRight: 6 }),
};

const EVENT_TYPES = ["NEWS", "SEC_FILING", "EARNINGS_TRANSCRIPT", "INSIDER_TRANSACTION", "OPTIONS_FLOW", "CENTRAL_BANK", "MACRO_EVENT", "ANALYST_UPGRADE", "ANALYST_DOWNGRADE", "SHORT_INTEREST", "SOCIAL_SENTIMENT", "PATENT_FILING"];

function IngestPanel() {
  const ingest = useIngestEvent();
  const [form, setForm] = useState({ event_type: "NEWS", source: "", headline: "", content: "", tickers: "" });

  const handleSubmit = () => {
    if (!form.source || !form.headline) return;
    ingest.mutate({
      ...form,
      tickers: form.tickers ? form.tickers.split(",").map((t) => t.trim().toUpperCase()).filter(Boolean) : [],
    }, { onSuccess: () => setForm({ event_type: "NEWS", source: "", headline: "", content: "", tickers: "" }) });
  };

  return (
    <div style={S.card}>
      <div style={S.cardTitle}>Ingest Event</div>
      <select style={S.select} value={form.event_type} onChange={(e) => setForm((f) => ({ ...f, event_type: e.target.value }))}>
        {EVENT_TYPES.map((t) => <option key={t}>{t}</option>)}
      </select>
      <input style={S.input} placeholder="Source (e.g. Reuters, SEC EDGAR)" value={form.source} onChange={(e) => setForm((f) => ({ ...f, source: e.target.value }))} />
      <input style={S.input} placeholder="Headline" value={form.headline} onChange={(e) => setForm((f) => ({ ...f, headline: e.target.value }))} />
      <input style={S.input} placeholder="Tickers (comma-separated, e.g. AAPL, MSFT)" value={form.tickers} onChange={(e) => setForm((f) => ({ ...f, tickers: e.target.value }))} />
      <button style={S.btn()} onClick={handleSubmit} disabled={ingest.isPending}>{ingest.isPending ? "Ingesting..." : "Ingest Event"}</button>
      {ingest.isSuccess && <span style={{ marginLeft: 10, color: "#3fb950", fontSize: 13 }}>Ingested</span>}
    </div>
  );
}

function TickerTimeline() {
  const store = useAlternativeDataStore();
  const [ticker, setTicker] = useState("AAPL");
  const { data: timeline = [], refetch } = useTickerTimeline(store.activeTicker);
  const { data: sentiment } = useTickerSentiment(store.activeTicker);

  return (
    <div style={S.card}>
      <div style={S.cardTitle}>Ticker Intelligence</div>
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <input style={{ ...S.input, marginBottom: 0, flex: 1 }} placeholder="Ticker" value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} />
        <button style={S.btn("#1f6feb")} onClick={() => store.setActiveTicker(ticker)}>Analyze</button>
      </div>
      {sentiment && store.activeTicker && (
        <div style={{ display: "flex", gap: 16, marginBottom: 12, paddingBottom: 12, borderBottom: "1px solid #21262d" }}>
          <div style={{ textAlign: "center" }}><div style={{ fontSize: 22, fontWeight: 700, color: "#3fb950" }}>{sentiment.bullish_count}</div><div style={{ fontSize: 11, color: "#8b949e" }}>Bullish</div></div>
          <div style={{ textAlign: "center" }}><div style={{ fontSize: 22, fontWeight: 700, color: "#f85149" }}>{sentiment.bearish_count}</div><div style={{ fontSize: 11, color: "#8b949e" }}>Bearish</div></div>
          <div style={{ textAlign: "center" }}><div style={{ fontSize: 22, fontWeight: 700, color: "#8b949e" }}>{sentiment.neutral_count}</div><div style={{ fontSize: 11, color: "#8b949e" }}>Neutral</div></div>
        </div>
      )}
      {timeline.slice(0, 8).map((e, i) => (
        <div key={i} style={S.row}>
          <div style={{ fontSize: 13, fontWeight: 600 }}>{e.headline}</div>
          <div style={{ fontSize: 11, color: "#8b949e" }}>{e.event_type} · {e.source}</div>
        </div>
      ))}
      {timeline.length === 0 && store.activeTicker && <div style={{ color: "#8b949e", fontSize: 13 }}>No events for {store.activeTicker}</div>}
    </div>
  );
}

export default function AlternativeData() {
  const { data: events = [] } = useAltDataEvents({ limit: 20 });
  const { data: importanceFeed = [] } = useImportanceFeed({ limit: 10, min_importance: 0.7 });
  const { data: clusters = [] } = useAltDataClusters();
  const buildClusters = useBuildClusters();

  return (
    <div style={S.page}>
      <div style={S.title}>Alternative Data Intelligence</div>
      <div style={S.grid}>
        <IngestPanel />
        <TickerTimeline />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
        <div style={S.card}>
          <div style={S.cardTitle}>High-Impact Feed ({importanceFeed.length})</div>
          {importanceFeed.length === 0 && <div style={{ color: "#8b949e", fontSize: 13 }}>No high-impact events yet</div>}
          {importanceFeed.map((e, i) => (
            <div key={i} style={S.row}>
              <div style={{ fontSize: 13, fontWeight: 600 }}>{e.headline}</div>
              <div style={{ fontSize: 11, color: "#8b949e" }}>{e.event_type} · imp: {parseFloat(e.importance_score || 0).toFixed(2)}</div>
            </div>
          ))}
        </div>

        <div style={S.card}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <div style={S.cardTitle}>Event Clusters ({clusters.length})</div>
            <button style={{ ...S.btn("#21262d"), border: "1px solid #30363d", padding: "4px 10px", fontSize: 12 }} onClick={() => buildClusters.mutate()}>Rebuild</button>
          </div>
          {clusters.length === 0 && <div style={{ color: "#8b949e", fontSize: 13 }}>No clusters. Ingest events and click Rebuild.</div>}
          {clusters.map((c, i) => (
            <div key={i} style={S.row}>
              <div style={{ fontSize: 13, fontWeight: 600 }}>{c.cluster_label}</div>
              <div style={{ fontSize: 11, color: "#8b949e" }}>{c.event_count} events</div>
            </div>
          ))}
        </div>
      </div>

      <div style={S.card}>
        <div style={S.cardTitle}>Recent Events ({events.length})</div>
        {events.length === 0 && <div style={{ color: "#8b949e", fontSize: 13 }}>No events yet. Use the Ingest panel above.</div>}
        {events.map((e, i) => (
          <div key={i} style={S.row}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{e.headline}</div>
              <div style={{ fontSize: 12, color: "#8b949e" }}>{e.event_type} · {e.source} · Tickers: {(e.tickers || []).join(", ") || "N/A"}</div>
            </div>
            <div>
              <span style={S.badge(parseFloat(e.sentiment_score || 0) > 0.1 ? "#3fb950" : parseFloat(e.sentiment_score || 0) < -0.1 ? "#f85149" : "#8b949e")}>
                {parseFloat(e.sentiment_score || 0).toFixed(2)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
