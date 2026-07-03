import { useState, useEffect } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 18, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 18, marginBottom: 14 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#58a6ff", marginBottom: 12 },
  row2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 },
  input: { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, padding: "6px 10px", color: "#f0f6fc", fontSize: 12, width: "100%", boxSizing: "border-box", marginBottom: 6 },
  btn: (c = "#58a6ff") => ({ background: c + "22", border: `1px solid ${c}55`, borderRadius: 6, padding: "6px 14px", color: c, fontSize: 12, cursor: "pointer", fontFamily: "monospace", marginRight: 6, marginTop: 4 }),
  kv: { display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: "1px solid #21262d33", fontSize: 12 },
  badge: (c) => ({ display: "inline-block", fontSize: 10, padding: "1px 6px", borderRadius: 4, background: c + "22", color: c, fontWeight: 700 }),
  bar: (pct, color) => ({ display: "inline-block", width: `${Math.min(Math.abs(pct) * 40, 120)}px`, height: 10, background: color, borderRadius: 2, verticalAlign: "middle" }),
};

const TENORS = ["1M", "3M", "6M", "1Y", "2Y", "5Y", "10Y", "30Y"];
const DEFAULT_RATES = { "1M": "5.30", "3M": "5.35", "6M": "5.25", "1Y": "5.10", "2Y": "4.80", "5Y": "4.60", "10Y": "4.50", "30Y": "4.65" };

export default function M18YieldCurve() {
  const [curve, setCurve] = useState(null);
  const [spreads, setSpreads] = useState(null);
  const [history, setHistory] = useState([]);
  const [country, setCountry] = useState("US");
  const [rates, setRates] = useState(DEFAULT_RATES);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  const refresh = () => {
    setLoading(true);
    Promise.all([
      fetch(`/m18/economic/yield-curve/${country}`).then(r => r.json()).then(setCurve).catch(() => {}),
      fetch(`/m18/economic/yield-curve/history?country=${country}&limit=20`).then(r => r.json()).then(d => setHistory(Array.isArray(d) ? d : [])).catch(() => {}),
    ]).then(() => { setLoading(false); setError(null); }).catch(() => { setError("Unable to connect to the backend"); setLoading(false); });
  };
  useEffect(() => { refresh(); }, [country]);

  const record = async () => {
    const tenors = {};
    Object.entries(rates).forEach(([t, v]) => { if (v) tenors[t] = parseFloat(v) / 100; });
    await post("/m18/economic/yield-curve", { country, tenors });
    refresh();
  };

  const calcSpreads = async () => {
    const r = await fetch(`/m18/economic/yield-curve/spreads/${country}`);
    if (r.ok) setSpreads(await r.json());
  };

  const maxRate = Math.max(...Object.values(rates).map(Number));

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 300, color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 11 }}>
      Loading…
    </div>
  );

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Yield Curve Analysis</div>

      <div style={{ display: "flex", gap: 8, marginBottom: 16, alignItems: "center" }}>
        <input style={{ ...S.input, width: 100, marginBottom: 0 }} value={country} onChange={e => setCountry(e.target.value.toUpperCase())} placeholder="Country" />
        <button style={S.btn()} onClick={refresh}>Load</button>
        <button style={S.btn("#56d364")} onClick={calcSpreads}>Calc Spreads</button>
      </div>

      <div style={S.row2}>
        <div style={S.section}>
          <div style={S.sHdr}>Record Yield Curve — {country}</div>
          {TENORS.map(t => (
            <div key={t} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
              <div style={{ width: 36, color: "#8b949e", fontSize: 11 }}>{t}</div>
              <input style={{ ...S.input, width: 90, marginBottom: 0 }} value={rates[t]} onChange={e => setRates(p => ({ ...p, [t]: e.target.value }))} placeholder="%" />
              <div style={{ flex: 1, height: 8, background: "#161b22", borderRadius: 4, overflow: "hidden" }}>
                <div style={{ width: `${(parseFloat(rates[t] || 0) / (maxRate || 1)) * 100}%`, height: "100%", background: "#58a6ff", borderRadius: 4 }} />
              </div>
              <span style={{ fontSize: 11, color: "#79c0ff", width: 40 }}>{rates[t]}%</span>
            </div>
          ))}
          <button style={S.btn()} onClick={record}>Record Snapshot</button>
        </div>

        <div>
          {curve && (
            <div style={{ ...S.section, marginBottom: 14 }}>
              <div style={S.sHdr}>Current Curve — {curve.country}</div>
              <div style={{ display: "flex", gap: 8, marginBottom: 10, flexWrap: "wrap" }}>
                <span style={S.badge(curve.is_inverted ? "#ff7b72" : "#3fb950")}>{curve.is_inverted ? "INVERTED" : "NORMAL"}</span>
                <span style={{ fontSize: 11, color: "#8b949e" }}>Slope: {curve.slope?.toFixed(2)}%</span>
              </div>
              {curve.tenors && Object.entries(curve.tenors).sort((a, b) => {
                const order = ["1M","3M","6M","1Y","2Y","5Y","10Y","30Y"];
                return order.indexOf(a[0]) - order.indexOf(b[0]);
              }).map(([t, r]) => (
                <div key={t} style={S.kv}>
                  <span style={{ color: "#8b949e" }}>{t}</span>
                  <span style={{ color: "#58a6ff" }}>{(r * 100).toFixed(3)}%</span>
                </div>
              ))}
            </div>
          )}

          {spreads && (
            <div style={S.section}>
              <div style={S.sHdr}>Key Spreads — {spreads.country}</div>
              {[
                ["2s10s", spreads.spread_2s10s, "Classic recession signal"],
                ["3M10Y", spreads.spread_3m10y, "Fed model spread"],
                ["5s30s", spreads.spread_5s30s, "Long end slope"],
              ].map(([label, val, desc]) => (
                <div key={label} style={{ marginBottom: 10 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 2 }}>
                    <span style={{ fontSize: 12, color: "#f0f6fc" }}>{label}</span>
                    <span style={{ fontSize: 12, fontWeight: 700, color: (val ?? 0) >= 0 ? "#3fb950" : "#ff7b72" }}>{val != null ? `${(val * 100).toFixed(3)}%` : "—"}</span>
                  </div>
                  <div style={{ fontSize: 10, color: "#8b949e" }}>{desc}</div>
                </div>
              ))}
              {spreads.is_inverted && <div style={{ fontSize: 11, color: "#ff7b72", marginTop: 8 }}>⚠ Yield curve inverted — historical recession leading indicator</div>}
            </div>
          )}
        </div>
      </div>

      <div style={S.section}>
        <div style={S.sHdr}>Snapshot History ({history.length})</div>
        {history.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px 20px", fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-3)" }}>
            No snapshots recorded — use the form above to record a yield curve snapshot.
          </div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
            <thead><tr>{["Timestamp","Country","Inverted","Slope","2Y","10Y","30Y"].map(h => <th key={h} style={{ color: "#8b949e", textAlign: "left", padding: "4px 8px", borderBottom: "1px solid #21262d" }}>{h}</th>)}</tr></thead>
            <tbody>
              {history.map(snap => (
                <tr key={snap.snapshot_id}>
                  <td style={{ padding: "5px 8px", color: "#8b949e", borderBottom: "1px solid #161b22" }}>{snap.timestamp?.slice(0, 16)}</td>
                  <td style={{ padding: "5px 8px", color: "#c9d1d9", borderBottom: "1px solid #161b22" }}>{snap.country}</td>
                  <td style={{ padding: "5px 8px", borderBottom: "1px solid #161b22" }}><span style={S.badge(snap.is_inverted ? "#ff7b72" : "#3fb950")}>{snap.is_inverted ? "YES" : "NO"}</span></td>
                  <td style={{ padding: "5px 8px", color: (snap.slope ?? 0) >= 0 ? "#3fb950" : "#ff7b72", borderBottom: "1px solid #161b22" }}>{snap.slope?.toFixed(3)}%</td>
                  <td style={{ padding: "5px 8px", color: "#58a6ff", borderBottom: "1px solid #161b22" }}>{snap.tenors?.["2Y"] != null ? `${(snap.tenors["2Y"] * 100).toFixed(3)}%` : "—"}</td>
                  <td style={{ padding: "5px 8px", color: "#58a6ff", borderBottom: "1px solid #161b22" }}>{snap.tenors?.["10Y"] != null ? `${(snap.tenors["10Y"] * 100).toFixed(3)}%` : "—"}</td>
                  <td style={{ padding: "5px 8px", color: "#58a6ff", borderBottom: "1px solid #161b22" }}>{snap.tenors?.["30Y"] != null ? `${(snap.tenors["30Y"] * 100).toFixed(3)}%` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
