import { useState, useEffect } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 18, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 18, marginBottom: 14 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#d2a8ff", marginBottom: 12 },
  row2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 },
  input: { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, padding: "6px 10px", color: "#f0f6fc", fontSize: 12, width: "100%", boxSizing: "border-box", marginBottom: 6 },
  btn: (c="#d2a8ff") => ({ background: c + "22", border: `1px solid ${c}55`, borderRadius: 6, padding: "6px 14px", color: c, fontSize: 12, cursor: "pointer", fontFamily: "monospace", marginRight: 6, marginTop: 4 }),
  badge: (c="#3fb950") => ({ display: "inline-block", fontSize: 10, padding: "1px 6px", borderRadius: 4, background: c + "22", color: c, fontWeight: 700 }),
  kv: { display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: "1px solid #21262d33", fontSize: 12 },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 11 },
  th: { color: "#8b949e", textAlign: "left", padding: "4px 8px", borderBottom: "1px solid #21262d" },
  td: { padding: "5px 8px", color: "#c9d1d9", borderBottom: "1px solid #161b22" },
};

const beatColor = { LARGE_BEAT: "#3fb950", BEAT: "#56d364", IN_LINE: "#8b949e", MISS: "#f0883e", LARGE_MISS: "#ff7b72" };

export default function M18EarningsIntel() {
  const [ticker, setTicker] = useState("AAPL");
  const [releases, setReleases] = useState([]);
  const [calendar, setCalendar] = useState([]);
  const [analysis, setAnalysis] = useState(null);
  const [signal, setSignal] = useState(null);
  const [releaseForm, setReleaseForm] = useState({ ticker: "AAPL", fiscal_quarter: "Q1 2026", reported_eps: "2.18", consensus_eps: "2.02", reported_revenue: "119600", consensus_revenue: "111200", gross_margin: "0.46", operating_margin: "0.31", guidance_direction: "RAISED" });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  const refresh = () => {
    setLoading(true);
    Promise.all([
      fetch(`/m18/earnings/releases/${ticker.toUpperCase()}`).then(r => r.json()).then(d => setReleases(Array.isArray(d) ? d : [])).catch(() => {}),
      fetch("/m18/earnings/calendar/upcoming?limit=15").then(r => r.json()).then(d => setCalendar(Array.isArray(d) ? d : [])).catch(() => {}),
    ]).then(() => { setLoading(false); setError(null); }).catch(() => { setError("Unable to connect to the backend"); setLoading(false); });
  };
  useEffect(() => { refresh(); }, [ticker]);

  const recordRelease = async () => {
    const r = await post("/m18/earnings/releases", {
      ...releaseForm, ticker: releaseForm.ticker.toUpperCase(),
      reported_eps: parseFloat(releaseForm.reported_eps), consensus_eps: parseFloat(releaseForm.consensus_eps),
      reported_revenue: parseFloat(releaseForm.reported_revenue), consensus_revenue: parseFloat(releaseForm.consensus_revenue),
      gross_margin: parseFloat(releaseForm.gross_margin), operating_margin: parseFloat(releaseForm.operating_margin),
    });
    if (r.ok) { setTicker(releaseForm.ticker.toUpperCase()); }
  };

  const runAnalysis = async () => {
    const r = await fetch(`/m18/earnings/surprise-analysis/${ticker.toUpperCase()}`);
    if (r.ok) setAnalysis(await r.json());
  };

  const genSignal = async () => {
    const r = await post("/m18/earnings/signal", { ticker: ticker.toUpperCase(), eps_surprise_pct: 0.08, revenue_surprise_pct: 0.075, guidance_direction: "RAISED" });
    if (r.ok) setSignal(await r.json());
  };

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 300, color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 11 }}>
      Loading…
    </div>
  );

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Earnings Intelligence</div>

      <div style={S.row2}>
        <div style={S.section}>
          <div style={S.sHdr}>Record Earnings Release</div>
          {Object.keys(releaseForm).map(f => (
            <div key={f}>
              <div style={{ fontSize: 10, color: "#8b949e", marginBottom: 2 }}>{f}</div>
              <input style={S.input} value={releaseForm[f]} onChange={e => setReleaseForm(p => ({ ...p, [f]: e.target.value }))} />
            </div>
          ))}
          <button style={S.btn()} onClick={recordRelease}>Record Release</button>
        </div>

        <div>
          <div style={S.section}>
            <div style={S.sHdr}>Ticker Analysis</div>
            <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
              <input style={{ ...S.input, width: 120, marginBottom: 0 }} value={ticker} onChange={e => setTicker(e.target.value.toUpperCase())} placeholder="Ticker" />
              <button style={S.btn()} onClick={refresh}>Load</button>
              <button style={S.btn("#56d364")} onClick={runAnalysis}>Surprise Analysis</button>
              <button style={S.btn("#58a6ff")} onClick={genSignal}>Gen Signal</button>
            </div>
            {analysis && (
              <div>
                {[["Beat Rate", `${(analysis.beat_rate * 100).toFixed(0)}%`], ["Avg EPS Surprise", `${(analysis.avg_eps_surprise_pct * 100).toFixed(2)}%`], ["Avg Rev Surprise", `${(analysis.avg_revenue_surprise_pct * 100).toFixed(2)}%`], ["Consistency Score", analysis.consistency_score?.toFixed(1)], ["Avg Post Drift", `${(analysis.post_earnings_drift_avg * 100).toFixed(2)}%`]].map(([k, v]) => (
                  <div key={k} style={S.kv}><span style={{ color: "#8b949e" }}>{k}</span><span style={{ color: "#f0f6fc" }}>{v}</span></div>
                ))}
              </div>
            )}
            {signal && (
              <div style={{ marginTop: 12, background: "#161b22", borderRadius: 6, padding: 10 }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: signal.signal === "STRONG_BUY" || signal.signal === "BUY" ? "#3fb950" : signal.signal === "SELL" || signal.signal === "STRONG_SELL" ? "#ff7b72" : "#8b949e" }}>{signal.signal}</div>
                <div style={{ fontSize: 11, color: "#8b949e", marginTop: 4 }}>Confidence: {(signal.confidence * 100).toFixed(1)}%</div>
                <div style={{ fontSize: 11, color: "#8b949e", marginTop: 2 }}>{signal.rationale}</div>
              </div>
            )}
          </div>
        </div>
      </div>

      <div style={S.section}>
        <div style={S.sHdr}>Historical Releases — {ticker}</div>
        {releases.length === 0 ? <div style={{ color: "#8b949e", fontSize: 12 }}>No releases recorded for {ticker}.</div> : (
          <table style={S.table}>
            <thead><tr>{["Quarter","EPS Reported","EPS Consensus","EPS Beat/Miss","Rev Surprise","Guidance","Drift 1d"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr></thead>
            <tbody>
              {releases.map(r => (
                <tr key={r.release_id}>
                  <td style={{ ...S.td, color: "#d2a8ff" }}>{r.fiscal_quarter}</td>
                  <td style={S.td}>${r.reported_eps?.toFixed(2)}</td>
                  <td style={S.td}>${r.consensus_eps?.toFixed(2)}</td>
                  <td style={S.td}><span style={{ ...S.badge(beatColor[r.eps_beat_miss] || "#8b949e") }}>{r.eps_beat_miss}</span></td>
                  <td style={{ ...S.td, color: r.revenue_surprise_pct >= 0 ? "#3fb950" : "#ff7b72" }}>{(r.revenue_surprise_pct * 100)?.toFixed(2)}%</td>
                  <td style={S.td}>{r.guidance_direction}</td>
                  <td style={{ ...S.td, color: r.post_earnings_drift_1d >= 0 ? "#3fb950" : "#ff7b72" }}>{(r.post_earnings_drift_1d * 100)?.toFixed(2)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div style={S.section}>
        <div style={S.sHdr}>Upcoming Earnings</div>
        {calendar.length === 0 ? <div style={{ color: "#8b949e", fontSize: 12 }}>No events scheduled.</div> : (
          <table style={S.table}>
            <thead><tr>{["Ticker","Quarter","Expected Date","Time","Consensus EPS"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr></thead>
            <tbody>
              {calendar.map(e => (
                <tr key={e.entry_id}>
                  <td style={{ ...S.td, color: "#58a6ff" }}>{e.ticker}</td>
                  <td style={S.td}>{e.fiscal_quarter}</td>
                  <td style={S.td}>{e.expected_date?.slice(0, 10)}</td>
                  <td style={S.td}>{e.time_of_day}</td>
                  <td style={S.td}>${e.consensus_eps?.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
