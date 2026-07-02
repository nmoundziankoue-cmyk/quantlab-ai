import { useState, useEffect } from "react";
import { eventsApi } from "../api/eventsApi";

const CARD = { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" };
const INPUT = { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", padding: "6px 10px", fontSize: 12, fontFamily: "monospace" };
const BTN = (a) => ({ padding: "7px 16px", borderRadius: 6, border: "none", cursor: "pointer", fontSize: 12, background: a ? "#1f6feb" : "#21262d", color: "#f0f6fc", fontFamily: "monospace" });

const IMP_COLOR = { critical: "#f85149", high: "#e3b341", medium: "#58a6ff", low: "#8b949e" };
const KIND_COLOR = { corporate: "#3fb950", macro: "#e3b341" };

function HitCard({ hit }) {
  const ev = hit.event_data || {};
  const kind = hit.kind;
  const kc = KIND_COLOR[kind] || "#8b949e";
  const ic = IMP_COLOR[ev.importance] || "#8b949e";
  const date = ev.timestamp ? new Date(ev.timestamp * 1000).toLocaleDateString() : "—";

  return (
    <div style={{ ...CARD, marginBottom: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span style={{ fontSize: 10, color: kc, padding: "1px 6px", border: `1px solid ${kc}`, borderRadius: 3 }}>{kind}</span>
          <span style={{ fontWeight: 700, fontSize: 14, color: "#f0f6fc" }}>
            {ev.ticker ? `${ev.ticker} — ` : ""}{(ev.event_type || "").replace(/_/g," ").toUpperCase()}
          </span>
          <span style={{ fontSize: 11, color: ic }}>{ev.importance}</span>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <span style={{ fontSize: 10, color: "#8b949e" }}>{date}</span>
          <span style={{ fontSize: 12, fontWeight: 700, color: "#58a6ff" }}>score: {hit.score.toFixed(3)}</span>
        </div>
      </div>
      <div style={{ fontSize: 12, color: "#c9d1d9" }}>{ev.description?.slice(0, 150)}</div>
      {ev.country && <div style={{ fontSize: 11, color: "#8b949e", marginTop: 4 }}>{ev.sector || ""} · {ev.country}</div>}
    </div>
  );
}

export default function EventSearch() {
  const [query, setQuery] = useState("");
  const [ticker, setTicker] = useState("");
  const [sector, setSector] = useState("");
  const [country, setCountry] = useState("");
  const [importance, setImportance] = useState("");
  const [kind, setKind] = useState("");
  const [hits, setHits] = useState([]);
  const [facets, setFacets] = useState(null);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [suggestions, setSuggestions] = useState([]);

  useEffect(() => {
    eventsApi.searchFacets().then((r) => setFacets(r.data)).catch(() => {});
  }, []);

  const search = async () => {
    setLoading(true);
    setSearched(true);
    try {
      const payload = { query: query || undefined, limit: 50 };
      if (ticker) payload.tickers = [ticker.toUpperCase()];
      if (sector) payload.sectors = [sector];
      if (country) payload.countries = [country.toUpperCase()];
      if (importance) payload.importance = [importance];
      if (kind) payload.kind = kind;
      const r = await eventsApi.search(payload);
      setHits(r.data?.hits || []);
    } catch {
      setHits([]);
    } finally {
      setLoading(false);
    }
  };

  const autocomplete = async (q) => {
    if (q.length < 2) { setSuggestions([]); return; }
    try {
      const r = await eventsApi.autocomplete(q);
      setSuggestions(r.data || []);
    } catch { setSuggestions([]); }
  };

  const onKeyDown = (e) => { if (e.key === "Enter") search(); };

  return (
    <div style={{ padding: 24, color: "#f0f6fc", fontFamily: "monospace" }}>
      <div style={{ fontSize: 11, color: "#58a6ff", letterSpacing: "0.1em", marginBottom: 4 }}>M15</div>
      <h1 style={{ margin: "0 0 20px", fontSize: 22 }}>Event Search</h1>

      <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: 16 }}>
        <div style={CARD}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#58a6ff", marginBottom: 14 }}>Filters</div>
          <div style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>Kind</div>
            <select style={{ ...INPUT, width: "100%" }} value={kind} onChange={(e) => setKind(e.target.value)}>
              <option value="">All</option>
              <option value="corporate">Corporate</option>
              <option value="macro">Macro</option>
            </select>
          </div>
          <div style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>Ticker</div>
            <div style={{ position: "relative" }}>
              <input style={{ ...INPUT, width: "100%" }} value={ticker}
                onChange={(e) => { setTicker(e.target.value); autocomplete(e.target.value); }} />
              {suggestions.length > 0 && (
                <div style={{ position: "absolute", top: "100%", left: 0, right: 0, background: "#161b22", border: "1px solid #30363d", borderRadius: 6, zIndex: 10 }}>
                  {suggestions.map((s) => (
                    <div key={s} style={{ padding: "6px 10px", fontSize: 12, cursor: "pointer", color: "#c9d1d9" }}
                      onClick={() => { setTicker(s); setSuggestions([]); }}
                      onMouseEnter={(e) => e.target.style.background = "#21262d"}
                      onMouseLeave={(e) => e.target.style.background = ""}>{s}</div>
                  ))}
                </div>
              )}
            </div>
          </div>
          {[["Sector","sector",setSector],["Country","country",setCountry]].map(([l,k,set]) => (
            <div key={k} style={{ marginBottom: 10 }}>
              <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>{l}</div>
              <input style={{ ...INPUT, width: "100%" }} value={k === "sector" ? sector : country} onChange={(e) => set(e.target.value)} />
            </div>
          ))}
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>Importance</div>
            <select style={{ ...INPUT, width: "100%" }} value={importance} onChange={(e) => setImportance(e.target.value)}>
              <option value="">All</option>
              {["critical","high","medium","low"].map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>

          {facets && (
            <div>
              <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 6 }}>TOP SECTORS</div>
              {Object.entries(facets.sectors || {}).slice(0, 5).map(([k, v]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", fontSize: 11, padding: "2px 0" }}>
                  <span style={{ color: "#c9d1d9", cursor: "pointer" }} onClick={() => setSector(k)}>{k}</span>
                  <span style={{ color: "#58a6ff" }}>{v}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div>
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            <input style={{ ...INPUT, flex: 1 }} placeholder="Search events… (press Enter or click Search)"
              value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={onKeyDown} />
            <button style={BTN(true)} onClick={search} disabled={loading}>{loading ? "Searching…" : "Search"}</button>
          </div>

          {!searched && (
            <div style={{ ...CARD, color: "#8b949e" }}>Enter a query or apply filters and click Search.</div>
          )}
          {searched && hits.length === 0 && !loading && (
            <div style={{ ...CARD, color: "#8b949e" }}>No results found. Try different filters or add more events.</div>
          )}
          {hits.length > 0 && (
            <>
              <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 10 }}>{hits.length} result{hits.length !== 1 ? "s" : ""}</div>
              {hits.map((h, i) => <HitCard key={h.event_id || i} hit={h} />)}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
