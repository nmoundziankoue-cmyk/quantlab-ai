import { useState } from "react";
import { eventsApi } from "../api/eventsApi";

const CARD = { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" };
const INPUT = { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, color: "#f0f6fc", padding: "6px 10px", fontSize: 12, fontFamily: "monospace" };
const BTN = (a) => ({ padding: "7px 16px", borderRadius: 6, border: "none", cursor: "pointer", fontSize: 12, background: a ? "#1f6feb" : "#21262d", color: "#f0f6fc", fontFamily: "monospace" });

const WINDOWS = ["[-1,+1]","[-3,+3]","[-5,+5]","[-10,+10]","[-20,+20]","[-60,+60]"];

const DEFAULT_RETURNS = {
  AAPL: [-0.01, 0.005, 0.02, 0.015, -0.003, 0.01, 0.008, 0.012, -0.005, 0.018, 0.003],
  MSFT: [-0.008, 0.003, 0.015, 0.012, -0.002, 0.007, 0.006, 0.010, -0.004, 0.014, 0.002],
};

const DEFAULT_EXPECTED = {
  AAPL: Array(11).fill(0.001),
  MSFT: Array(11).fill(0.001),
};

function ResultCard({ windowLabel, result }) {
  const sig = result.significant;
  const pColor = result.p_value < 0.05 ? "#3fb950" : "#8b949e";
  return (
    <div style={{ ...CARD, marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div style={{ fontWeight: 700, color: "#58a6ff", fontSize: 14 }}>Window {windowLabel}</div>
        <span style={{
          fontSize: 11, padding: "2px 10px", borderRadius: 4,
          background: sig ? "rgba(63,185,80,0.15)" : "rgba(139,148,158,0.15)",
          color: sig ? "#3fb950" : "#8b949e", border: `1px solid ${sig ? "#3fb950" : "#8b949e"}`,
        }}>{sig ? "✓ SIGNIFICANT" : "NOT SIGNIFICANT"}</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        {[
          ["CAAR", `${(result.caar * 100).toFixed(3)}%`, result.caar >= 0 ? "#3fb950" : "#f85149"],
          ["AAR", `${(result.aar * 100).toFixed(3)}%`, result.aar >= 0 ? "#3fb950" : "#f85149"],
          ["t-stat", result.t_stat?.toFixed(3), result.t_stat > 2 ? "#3fb950" : result.t_stat < -2 ? "#f85149" : "#8b949e"],
          ["p-value", result.p_value?.toFixed(4), pColor],
          ["n", result.n_securities, "#f0f6fc"],
          ["CI 95%", `[${(result.ci_95_low * 100).toFixed(2)}%, ${(result.ci_95_high * 100).toFixed(2)}%]`, "#8b949e"],
          ["Boot CI", `[${(result.bootstrap_ci_low * 100).toFixed(2)}%, ${(result.bootstrap_ci_high * 100).toFixed(2)}%]`, "#8b949e"],
        ].map(([l, v, c]) => (
          <div key={l}>
            <div style={{ fontSize: 11, color: "#8b949e" }}>{l}</div>
            <div style={{ fontSize: 14, fontWeight: 700, color: c || "#f0f6fc" }}>{v}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function EventStudyPage() {
  const [eventId, setEventId] = useState("study_001");
  const [tickersInput, setTickersInput] = useState("AAPL,MSFT");
  const [returnsJson, setReturnsJson] = useState(JSON.stringify(DEFAULT_RETURNS, null, 2));
  const [expectedJson, setExpectedJson] = useState(JSON.stringify(DEFAULT_EXPECTED, null, 2));
  const [selectedWindows, setSelectedWindows] = useState(["[-1,+1]","[-3,+3]","[-5,+5]"]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const toggleWindow = (w) => {
    setSelectedWindows((prev) => prev.includes(w) ? prev.filter((x) => x !== w) : [...prev, w]);
  };

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      const tickers = tickersInput.split(",").map((t) => t.trim()).filter(Boolean);
      const actual = JSON.parse(returnsJson);
      const expected = JSON.parse(expectedJson);
      const r = await eventsApi.runStudy({
        event_id: eventId,
        tickers,
        actual_returns: actual,
        expected_returns: expected,
        windows: selectedWindows,
      });
      setResults(r.data?.results || {});
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 24, color: "#f0f6fc", fontFamily: "monospace" }}>
      <div style={{ fontSize: 11, color: "#58a6ff", letterSpacing: "0.1em", marginBottom: 4 }}>M15</div>
      <h1 style={{ margin: "0 0 4px", fontSize: 22 }}>Event Study Engine</h1>
      <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 20 }}>Classical event study: AR, AAR, CAR, CAAR, t-statistics, bootstrap confidence intervals</div>

      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 16 }}>
        <div>
          <div style={CARD}>
            <div style={{ fontSize: 13, fontWeight: 700, color: "#58a6ff", marginBottom: 14 }}>Study Parameters</div>

            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>Event ID</div>
              <input style={{ ...INPUT, width: "100%" }} value={eventId} onChange={(e) => setEventId(e.target.value)} />
            </div>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>Tickers (comma separated)</div>
              <input style={{ ...INPUT, width: "100%" }} value={tickersInput} onChange={(e) => setTickersInput(e.target.value)} />
            </div>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>Event Windows</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {WINDOWS.map((w) => (
                  <button key={w} style={{ ...BTN(selectedWindows.includes(w)), padding: "4px 10px", fontSize: 11 }} onClick={() => toggleWindow(w)}>{w}</button>
                ))}
              </div>
            </div>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>Actual Returns (JSON)</div>
              <textarea style={{ ...INPUT, width: "100%", height: 120, resize: "vertical", fontSize: 10 }}
                value={returnsJson} onChange={(e) => setReturnsJson(e.target.value)} />
            </div>
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>Expected Returns (JSON)</div>
              <textarea style={{ ...INPUT, width: "100%", height: 80, resize: "vertical", fontSize: 10 }}
                value={expectedJson} onChange={(e) => setExpectedJson(e.target.value)} />
            </div>
            {error && <div style={{ color: "#f85149", fontSize: 12, marginBottom: 10 }}>{error}</div>}
            <button style={{ ...BTN(true), width: "100%" }} disabled={loading} onClick={run}>
              {loading ? "Running Study…" : "Run Event Study"}
            </button>
          </div>
        </div>

        <div>
          {!results && <div style={{ ...CARD, color: "#8b949e" }}>Run the event study to see results here.</div>}
          {results && (
            <>
              <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 12 }}>
                Results for event <strong style={{ color: "#f0f6fc" }}>{eventId}</strong> across {selectedWindows.length} window{selectedWindows.length !== 1 ? "s" : ""}
              </div>
              {Object.entries(results).map(([w, r]) => <ResultCard key={w} windowLabel={w} result={r} />)}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
