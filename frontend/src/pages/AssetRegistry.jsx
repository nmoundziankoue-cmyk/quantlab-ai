import { useState } from "react";
import { multiAssetApi } from "../api/multiAssetApi";

const CARD = { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" };
const LABEL = { fontSize: 11, color: "#8b949e", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 4 };
const INPUT = { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", fontFamily: "monospace", fontSize: 12, padding: "6px 10px", width: "100%" };

const TYPE_COLORS = { equity: "#58a6ff", bond: "#3fb950", etf: "#e3b341", crypto: "#a371f7", commodity: "#ffa657", currency: "#f85149", option: "#79c0ff", future: "#f9e2af", index: "#8b949e" };

export default function AssetRegistry() {
  const [assets, setAssets] = useState([]);
  const [stats, setStats] = useState(null);
  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState(null);
  const [form, setForm] = useState({ ticker: "", name: "", asset_type: "equity", country: "US", currency: "USD", sector: "", description: "" });
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState(null);
  const [tab, setTab] = useState("list");

  const load = async () => {
    setLoading(true);
    try {
      const [a, s] = await Promise.all([multiAssetApi.listAssets(), multiAssetApi.assetStatistics()]);
      setAssets(a.data || []);
      setStats(s.data);
    } catch (e) { setMsg({ type: "error", text: e.message }); }
    finally { setLoading(false); }
  };

  const register = async () => {
    if (!form.ticker || !form.name) return setMsg({ type: "error", text: "Ticker and name required" });
    setLoading(true); setMsg(null);
    try {
      await multiAssetApi.registerAsset(form);
      setMsg({ type: "success", text: `Registered ${form.ticker}` });
      setForm({ ticker: "", name: "", asset_type: "equity", country: "US", currency: "USD", sector: "", description: "" });
      await load();
    } catch (e) { setMsg({ type: "error", text: e.message }); }
    finally { setLoading(false); }
  };

  const doSearch = async () => {
    if (!search.trim()) return;
    try {
      const res = await multiAssetApi.searchAssets(search.trim());
      setSearchResults(res.data);
    } catch (e) { setMsg({ type: "error", text: e.message }); }
  };

  return (
    <div style={{ padding: 24, color: "#f0f6fc", fontFamily: "monospace", maxWidth: 1100 }}>
      <div style={{ fontSize: 11, color: "#ffa657", letterSpacing: "0.1em", marginBottom: 4 }}>M16 — ASSET REGISTRY</div>
      <h1 style={{ margin: "0 0 24px", fontSize: 22, fontWeight: 700 }}>Asset Registry</h1>

      <div style={{ display: "flex", gap: 8, marginBottom: 20, alignItems: "center" }}>
        {["list", "register", "search"].map(t => (
          <button key={t} onClick={() => setTab(t)} style={{ padding: "6px 14px", borderRadius: 6, border: "1px solid", borderColor: tab === t ? "#ffa657" : "#21262d", background: tab === t ? "#ffa65722" : "transparent", color: tab === t ? "#ffa657" : "#8b949e", fontSize: 12, cursor: "pointer", fontFamily: "monospace" }}>{t.toUpperCase()}</button>
        ))}
        <button onClick={load} disabled={loading} style={{ marginLeft: "auto", padding: "6px 16px", background: "#ffa65733", border: "1px solid #ffa657", borderRadius: 6, color: "#ffa657", fontSize: 12, cursor: "pointer", fontFamily: "monospace" }}>
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>

      {msg && <div style={{ padding: "8px 12px", borderRadius: 6, marginBottom: 16, background: msg.type === "error" ? "#f8514922" : "#3fb95022", color: msg.type === "error" ? "#f85149" : "#3fb950", fontSize: 12 }}>{msg.text}</div>}

      {stats && (
        <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
          {[["Total Assets", stats.total_assets], ["Active", stats.active_assets], ["Asset Types", Object.keys(stats.by_type || {}).length], ["Countries", Object.keys(stats.by_country || {}).length]].map(([k, v]) => (
            <div key={k} style={{ ...CARD, flex: 1, textAlign: "center" }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: "#ffa657" }}>{v ?? "—"}</div>
              <div style={{ fontSize: 11, color: "#8b949e", marginTop: 2 }}>{k}</div>
            </div>
          ))}
        </div>
      )}

      {tab === "list" && (
        <div style={CARD}>
          <div style={LABEL}>Registered Assets ({assets.length})</div>
          {assets.length === 0 ? (
            <div style={{ fontSize: 12, color: "#8b949e", marginTop: 8 }}>No assets registered yet. Click Refresh or register assets via the Register tab.</div>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 8 }}>
              <thead><tr>{["Ticker", "Name", "Type", "Country", "Currency", "Sector"].map(h => <th key={h} style={{ textAlign: "left", padding: "6px 8px", fontSize: 11, color: "#8b949e", borderBottom: "1px solid #21262d" }}>{h}</th>)}</tr></thead>
              <tbody>
                {assets.map(a => (
                  <tr key={a.asset_id}>
                    <td style={{ padding: "7px 8px", fontWeight: 700, color: "#58a6ff", fontSize: 12 }}>{a.ticker}</td>
                    <td style={{ padding: "7px 8px", fontSize: 12, color: "#c9d1d9" }}>{a.name}</td>
                    <td style={{ padding: "7px 8px" }}><span style={{ fontSize: 11, color: TYPE_COLORS[a.asset_type] || "#8b949e", background: `${TYPE_COLORS[a.asset_type] || "#8b949e"}22`, padding: "2px 6px", borderRadius: 4 }}>{a.asset_type}</span></td>
                    <td style={{ padding: "7px 8px", fontSize: 11, color: "#8b949e" }}>{a.country || "—"}</td>
                    <td style={{ padding: "7px 8px", fontSize: 11, color: "#8b949e" }}>{a.currency}</td>
                    <td style={{ padding: "7px 8px", fontSize: 11, color: "#8b949e" }}>{a.sector || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === "register" && (
        <div style={{ ...CARD, maxWidth: 560 }}>
          <div style={LABEL}>Register New Asset</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 12 }}>
            {[["Ticker *", "ticker"], ["Name *", "name"], ["Country", "country"], ["Currency", "currency"], ["Sector", "sector"]].map(([label, key]) => (
              <div key={key}>
                <div style={LABEL}>{label}</div>
                <input value={form[key]} onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))} style={INPUT} />
              </div>
            ))}
            <div>
              <div style={LABEL}>Asset Type</div>
              <select value={form.asset_type} onChange={e => setForm(f => ({ ...f, asset_type: e.target.value }))} style={{ ...INPUT, appearance: "none" }}>
                {["equity","bond","etf","crypto","commodity","currency","option","future","index"].map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
          </div>
          <div style={{ marginTop: 10 }}>
            <div style={LABEL}>Description</div>
            <input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} style={INPUT} />
          </div>
          <button onClick={register} disabled={loading} style={{ marginTop: 16, padding: "8px 24px", background: "#ffa65733", border: "1px solid #ffa657", borderRadius: 6, color: "#ffa657", fontSize: 12, cursor: "pointer", fontFamily: "monospace" }}>
            {loading ? "Registering…" : "Register Asset"}
          </button>
        </div>
      )}

      {tab === "search" && (
        <div>
          <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
            <input value={search} onChange={e => setSearch(e.target.value)} onKeyDown={e => e.key === "Enter" && doSearch()} placeholder="Search ticker, name, ISIN…" style={{ ...INPUT, flex: 1, maxWidth: 400 }} />
            <button onClick={doSearch} style={{ padding: "6px 16px", background: "#ffa65733", border: "1px solid #ffa657", borderRadius: 6, color: "#ffa657", fontSize: 12, cursor: "pointer", fontFamily: "monospace" }}>Search</button>
          </div>
          {searchResults && (
            <div style={CARD}>
              <div style={LABEL}>{searchResults.length} result{searchResults.length !== 1 ? "s" : ""}</div>
              {searchResults.length === 0 ? <div style={{ fontSize: 12, color: "#8b949e" }}>No assets found</div> : (
                searchResults.map(a => (
                  <div key={a.asset_id} style={{ padding: "8px 0", borderBottom: "1px solid #21262d" }}>
                    <span style={{ fontWeight: 700, color: "#58a6ff", fontSize: 13 }}>{a.ticker}</span>
                    <span style={{ color: "#c9d1d9", fontSize: 12, marginLeft: 8 }}>{a.name}</span>
                    <span style={{ color: TYPE_COLORS[a.asset_type], fontSize: 11, marginLeft: 8, background: `${TYPE_COLORS[a.asset_type]}22`, padding: "1px 6px", borderRadius: 4 }}>{a.asset_type}</span>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
