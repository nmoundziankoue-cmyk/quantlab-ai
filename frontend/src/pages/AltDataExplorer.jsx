import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { altIntelligenceApi } from "../api/altIntelligenceApi";

const S = {
  page: { padding: 28, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" },
  card: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20, marginBottom: 16 },
  title: { fontSize: 13, fontWeight: 700, color: "#8b949e", letterSpacing: "0.06em", marginBottom: 14, textTransform: "uppercase" },
  label: { fontSize: 12, color: "#8b949e", marginBottom: 4, display: "block" },
  input: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "9px 12px", fontSize: 13, width: "100%", boxSizing: "border-box" },
  select: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "9px 12px", fontSize: 13, width: "100%", boxSizing: "border-box" },
  btn: { background: "#1f6feb", border: "none", borderRadius: 6, color: "#fff", padding: "10px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer" },
  btnGreen: { background: "#238636", border: "none", borderRadius: 6, color: "#fff", padding: "10px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer" },
  tab: { padding: "8px 18px", fontSize: 13, fontWeight: 600, cursor: "pointer", borderRadius: "6px 6px 0 0", border: "1px solid transparent", background: "transparent", color: "#8b949e", marginRight: 2 },
  tabActive: { background: "#161b22", border: "1px solid #30363d", borderBottom: "1px solid #161b22", color: "#e6edf3" },
  err: { background: "#2d1317", border: "1px solid #f85149", borderRadius: 6, color: "#f85149", padding: "10px 14px", fontSize: 13, marginBottom: 14 },
  ok: { background: "#1a3a25", border: "1px solid #3fb950", borderRadius: 6, color: "#3fb950", padding: "10px 14px", fontSize: 13, marginBottom: 14 },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 12 },
  th: { padding: "8px 10px", textAlign: "left", color: "#8b949e", borderBottom: "1px solid #21262d", fontWeight: 600 },
  td: { padding: "7px 10px", borderBottom: "1px solid #21262d", color: "#e6edf3" },
  pill: { display: "inline-block", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600 },
  metricBox: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 6, padding: "12px 14px", textAlign: "center" },
  metricValue: { fontSize: 20, fontWeight: 700, color: "#58a6ff", lineHeight: 1.2 },
  metricLabel: { fontSize: 11, color: "#8b949e", marginTop: 4, textTransform: "uppercase", letterSpacing: "0.06em" },
  textarea: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "9px 12px", fontSize: 12, width: "100%", boxSizing: "border-box", resize: "vertical", fontFamily: "monospace" },
};

const FILING_TYPES = ["10-K", "10-Q", "8-K", "Proxy", "13F", "13D", "Insider", "Transcript", "Other"];

function pct(n) { return n == null ? "—" : `${(Number(n) * 100).toFixed(1)}%`; }
function fmt(n, d = 2) { return n == null ? "—" : Number(n).toFixed(d); }

function ProvidersTab() {
  const { data, isLoading } = useQuery({ queryKey: ["alt-providers"], queryFn: () => altIntelligenceApi.listProviders().then(r => r.data) });
  const { data: caps } = useQuery({ queryKey: ["alt-caps"], queryFn: () => altIntelligenceApi.providerCapabilities().then(r => r.data) });

  return (
    <div>
      {caps && (
        <div style={{ ...S.card, marginBottom: 14 }}>
          <div style={S.title}>Provider Capabilities Matrix — {Object.keys(caps.providers || {}).length} Providers</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {Object.keys(caps.providers || {}).map(name => (
              <span key={name} style={{ ...S.pill, background: "#21262d", color: "#e6edf3", border: "1px solid #30363d" }}>{name}</span>
            ))}
          </div>
        </div>
      )}

      {isLoading && <div style={{ color: "#8b949e", fontSize: 13 }}>Loading providers…</div>}
      {data && (
        <div style={{ overflowX: "auto" }}>
          <table style={S.table}>
            <thead>
              <tr>
                <th style={S.th}>Provider</th>
                <th style={S.th}>Priority</th>
                <th style={S.th}>Status</th>
                <th style={S.th}>Quality</th>
                <th style={S.th}>P50 Latency</th>
                <th style={S.th}>Error Rate</th>
                <th style={S.th}>Capabilities</th>
              </tr>
            </thead>
            <tbody>
              {data.map(p => (
                <tr key={p.name}>
                  <td style={{ ...S.td, fontWeight: 700, whiteSpace: "nowrap" }}>{p.name}</td>
                  <td style={{ ...S.td, color: "#8b949e" }}>{p.priority}</td>
                  <td style={S.td}>
                    <span style={{ ...S.pill, background: p.is_healthy ? "#1a3a25" : "#2d1317", color: p.is_healthy ? "#3fb950" : "#f85149" }}>
                      {p.is_healthy ? "HEALTHY" : "DOWN"}
                    </span>
                  </td>
                  <td style={{ ...S.td, color: "#58a6ff" }}>{fmt(p.quality_score * 100, 0)}%</td>
                  <td style={S.td}>{fmt(p.p50_latency_ms)} ms</td>
                  <td style={{ ...S.td, color: p.error_rate > 0.1 ? "#f85149" : "#3fb950" }}>{pct(p.error_rate)}</td>
                  <td style={{ ...S.td, color: "#8b949e", maxWidth: 280, whiteSpace: "normal" }}>
                    {p.capabilities.slice(0, 4).join(", ")}{p.capabilities.length > 4 ? ` +${p.capabilities.length - 4}` : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function IngestTab() {
  const [docId, setDocId] = useState("");
  const [symbol, setSymbol] = useState("AAPL");
  const [filingType, setFilingType] = useState("10-K");
  const [text, setText] = useState("");
  const [source, setSource] = useState("sec.gov");
  const [result, setResult] = useState(null);

  const mut = useMutation({
    mutationFn: () => altIntelligenceApi.ingestDocument({ doc_id: docId || `doc_${Date.now()}`, symbol: symbol.toUpperCase(), filing_type: filingType, text, source }),
    onSuccess: setResult,
  });

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 12, marginBottom: 14 }}>
        <div><label style={S.label}>Doc ID (optional)</label><input style={S.input} value={docId} onChange={e => setDocId(e.target.value)} placeholder="auto-generated" /></div>
        <div><label style={S.label}>Symbol</label><input style={S.input} value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} placeholder="AAPL" /></div>
        <div><label style={S.label}>Filing Type</label>
          <select style={S.select} value={filingType} onChange={e => setFilingType(e.target.value)}>
            {FILING_TYPES.map(t => <option key={t}>{t}</option>)}
          </select>
        </div>
        <div><label style={S.label}>Source</label><input style={S.input} value={source} onChange={e => setSource(e.target.value)} /></div>
      </div>
      <div style={{ marginBottom: 14 }}>
        <label style={S.label}>Document Text</label>
        <textarea style={{ ...S.textarea, minHeight: 160 }} value={text} onChange={e => setText(e.target.value)}
          placeholder="Paste SEC filing, earnings transcript, or any institutional document text here…" />
      </div>
      <button style={{ ...S.btnGreen, opacity: mut.isPending || !text ? 0.6 : 1 }} onClick={() => mut.mutate()} disabled={mut.isPending || !text}>
        {mut.isPending ? "Ingesting…" : "Ingest Document"}
      </button>

      {mut.error && <div style={{ ...S.err, marginTop: 12 }}>{mut.error.message}</div>}
      {result && (
        <div style={{ ...S.ok, marginTop: 12 }}>
          <strong>Ingested:</strong> {result.doc_id} · v{result.version} · {result.size_bytes.toLocaleString()} bytes · quality {(result.quality_score * 100).toFixed(0)}%
          {result.quality_passed ? " ✓" : " ⚠ quality issues"}
        </div>
      )}
    </div>
  );
}

function HealthTab() {
  const { data, isLoading } = useQuery({ queryKey: ["alt-health"], queryFn: () => altIntelligenceApi.providerHealth().then(r => r.data) });

  if (isLoading) return <div style={{ color: "#8b949e", fontSize: 13 }}>Loading health…</div>;
  if (!data) return null;

  const healthy = (data.providers || []).filter(p => p.is_healthy).length;
  const total = (data.providers || []).length;

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 16 }}>
        <div style={S.metricBox}><div style={S.metricValue}>{total}</div><div style={S.metricLabel}>Total Providers</div></div>
        <div style={S.metricBox}><div style={{ ...S.metricValue, color: "#3fb950" }}>{healthy}</div><div style={S.metricLabel}>Healthy</div></div>
        <div style={S.metricBox}><div style={{ ...S.metricValue, color: "#f85149" }}>{total - healthy}</div><div style={S.metricLabel}>Degraded</div></div>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table style={S.table}>
          <thead><tr><th style={S.th}>Provider</th><th style={S.th}>Healthy</th><th style={S.th}>P50 ms</th><th style={S.th}>P95 ms</th><th style={S.th}>Error Rate</th></tr></thead>
          <tbody>
            {(data.providers || []).map(p => {
              const lat = (data.latency || []).find(l => l.provider === p.provider) || {};
              return (
                <tr key={p.provider}>
                  <td style={{ ...S.td, fontWeight: 700 }}>{p.provider}</td>
                  <td style={S.td}><span style={{ ...S.pill, background: p.is_healthy ? "#1a3a25" : "#2d1317", color: p.is_healthy ? "#3fb950" : "#f85149" }}>{p.is_healthy ? "OK" : "DOWN"}</span></td>
                  <td style={S.td}>{fmt(lat.p50_ms)}</td>
                  <td style={S.td}>{fmt(lat.p95_ms)}</td>
                  <td style={{ ...S.td, color: lat.error_rate > 0.1 ? "#f85149" : "#3fb950" }}>{pct(lat.error_rate)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const TABS = [
  { key: "providers", label: "Providers" },
  { key: "ingest", label: "Ingest Document" },
  { key: "health", label: "Health Monitor" },
];

export default function AltDataExplorer() {
  const [active, setActive] = useState("providers");
  return (
    <div style={S.page}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Alternative Data Explorer</h1>
        <p style={{ color: "#8b949e", margin: "4px 0 0", fontSize: 13 }}>
          Institutional alternative data intelligence — 21 providers · SEC · Satellite · Insider · ESG · Social · Search
        </p>
      </div>
      <div style={{ display: "flex", borderBottom: "1px solid #30363d" }}>
        {TABS.map(t => <button key={t.key} onClick={() => setActive(t.key)} style={{ ...S.tab, ...(active === t.key ? S.tabActive : {}) }}>{t.label}</button>)}
      </div>
      <div style={{ ...S.card, borderTopLeftRadius: 0, marginTop: 0, borderTop: "none" }}>
        {active === "providers" && <ProvidersTab />}
        {active === "ingest" && <IngestTab />}
        {active === "health" && <HealthTab />}
      </div>
    </div>
  );
}
