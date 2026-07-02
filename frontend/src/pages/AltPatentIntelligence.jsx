import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { altIntelligenceApi } from "../api/altIntelligenceApi";

const S = {
  page: { padding: 28, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" },
  card: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20, marginBottom: 16 },
  title: { fontSize: 13, fontWeight: 700, color: "#8b949e", letterSpacing: "0.06em", marginBottom: 14, textTransform: "uppercase" },
  label: { fontSize: 12, color: "#8b949e", marginBottom: 4, display: "block" },
  input: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "9px 12px", fontSize: 13, width: "100%", boxSizing: "border-box" },
  btn: { background: "#1f6feb", border: "none", borderRadius: 6, color: "#fff", padding: "10px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer" },
  err: { background: "#2d1317", border: "1px solid #f85149", borderRadius: 6, color: "#f85149", padding: "10px 14px", fontSize: 13, marginBottom: 14 },
  pill: { display: "inline-block", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600 },
  metricBox: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 6, padding: "14px 12px", textAlign: "center" },
  metricValue: { fontSize: 22, fontWeight: 700, color: "#58a6ff", lineHeight: 1.2 },
  metricLabel: { fontSize: 11, color: "#8b949e", marginTop: 4, textTransform: "uppercase", letterSpacing: "0.06em" },
};

function fmt(n, d = 4) { return Number(n).toFixed(d); }
function pctFmt(n) { return `${(Number(n) * 100).toFixed(1)}%`; }

function SparkBar({ values, color = "#58a6ff" }) {
  if (!values.length) return <div style={{ color: "#8b949e", fontSize: 12 }}>No data</div>;
  const max = Math.max(...values, 1);
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 4, height: 60 }}>
      {values.map((v, i) => (
        <div key={i} style={{ flex: 1, background: color, borderRadius: "2px 2px 0 0", opacity: 0.7 + (i / values.length) * 0.3, height: `${(v / max) * 100}%`, minHeight: 2, transition: "height 0.3s" }} title={v} />
      ))}
    </div>
  );
}

export default function AltPatentIntelligence() {
  const [symbol, setSymbol] = useState("AAPL");
  const [patentInput, setPatentInput] = useState("45, 52, 61, 58, 74, 89, 102");
  const [supplierInput, setSupplierInput] = useState("0.35, 0.20, 0.15, 0.12, 0.10, 0.08");
  const [customerInput, setCustomerInput] = useState("0.40, 0.25, 0.20, 0.10, 0.05");
  const [result, setResult] = useState(null);

  const parseList = (s) => s.split(",").map(x => parseFloat(x.trim())).filter(n => !isNaN(n));

  const mut = useMutation({
    mutationFn: () => altIntelligenceApi.computeFeatures({
      symbol,
      patent_counts_by_period: parseList(patentInput),
      supplier_concentration_shares: parseList(supplierInput),
      customer_concentration_shares: parseList(customerInput),
    }),
    onSuccess: r => setResult(r.data),
  });

  const features = result?.features || {};

  const growthColor = (v) => v > 0.05 ? "#3fb950" : v < -0.05 ? "#f85149" : "#d29922";
  const hhiColor = (v) => v > 0.4 ? "#f85149" : v > 0.2 ? "#d29922" : "#3fb950";

  return (
    <div style={S.page}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Patent Intelligence</h1>
        <p style={{ color: "#8b949e", margin: "4px 0 0", fontSize: 13 }}>
          Patent growth, supplier/customer concentration (HHI), and innovation signals for alternative alpha generation
        </p>
      </div>

      <div style={S.card}>
        <div style={S.title}>Innovation & Supply Chain Inputs</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 12, marginBottom: 14 }}>
          <div><label style={S.label}>Symbol</label><input style={S.input} value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} /></div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginBottom: 14 }}>
          <div>
            <label style={S.label}>Patent Counts by Period (comma-separated)</label>
            <input style={S.input} value={patentInput} onChange={e => setPatentInput(e.target.value)} placeholder="45, 52, 61, 74, 89" />
            <div style={{ fontSize: 11, color: "#8b949e", marginTop: 4 }}>Most recent period last</div>
          </div>
          <div>
            <label style={S.label}>Supplier Revenue Shares</label>
            <input style={S.input} value={supplierInput} onChange={e => setSupplierInput(e.target.value)} placeholder="0.35, 0.20, 0.15" />
            <div style={{ fontSize: 11, color: "#8b949e", marginTop: 4 }}>HHI concentration index</div>
          </div>
          <div>
            <label style={S.label}>Customer Revenue Shares</label>
            <input style={S.input} value={customerInput} onChange={e => setCustomerInput(e.target.value)} placeholder="0.40, 0.25, 0.20" />
            <div style={{ fontSize: 11, color: "#8b949e", marginTop: 4 }}>HHI concentration index</div>
          </div>
        </div>
        <button style={{ ...S.btn, opacity: mut.isPending ? 0.6 : 1 }} onClick={() => mut.mutate()} disabled={mut.isPending}>
          {mut.isPending ? "Computing…" : "Analyze Patent & Supply Chain"}
        </button>
      </div>

      {mut.error && <div style={S.err}>{mut.error.message}</div>}

      {result && (
        <>
          {/* Patent trend chart */}
          <div style={S.card}>
            <div style={S.title}>Patent Filing Trend</div>
            <SparkBar values={parseList(patentInput)} color="#58a6ff" />
            <div style={{ fontSize: 11, color: "#8b949e", marginTop: 8 }}>Periods (oldest → newest)</div>
          </div>

          {/* Key metrics */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 16 }}>
            <div style={S.metricBox}>
              <div style={{ ...S.metricValue, color: growthColor(features.alt_patent_growth ?? 0) }}>
                {features.alt_patent_growth !== undefined ? `${(features.alt_patent_growth * 100).toFixed(1)}%` : "—"}
              </div>
              <div style={S.metricLabel}>Patent Growth (tanh-clipped)</div>
              <div style={{ fontSize: 11, color: "#8b949e", marginTop: 4 }}>Period-over-period growth rate</div>
            </div>
            <div style={S.metricBox}>
              <div style={{ ...S.metricValue, color: hhiColor(features.alt_supplier_concentration ?? 0) }}>
                {features.alt_supplier_concentration !== undefined ? fmt(features.alt_supplier_concentration) : "—"}
              </div>
              <div style={S.metricLabel}>Supplier HHI</div>
              <div style={{ fontSize: 11, color: "#8b949e", marginTop: 4 }}>0 = fragmented · 1 = monopoly</div>
            </div>
            <div style={S.metricBox}>
              <div style={{ ...S.metricValue, color: hhiColor(features.alt_customer_concentration ?? 0) }}>
                {features.alt_customer_concentration !== undefined ? fmt(features.alt_customer_concentration) : "—"}
              </div>
              <div style={S.metricLabel}>Customer HHI</div>
              <div style={{ fontSize: 11, color: "#8b949e", marginTop: 4 }}>Higher = more concentrated</div>
            </div>
          </div>

          {/* Concentration charts */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            {[["Supplier Concentration", parseList(supplierInput), "#d29922"], ["Customer Concentration", parseList(customerInput), "#58a6ff"]].map(([label, vals, color]) => (
              <div key={label} style={S.card}>
                <div style={S.title}>{label}</div>
                <SparkBar values={vals} color={color} />
                <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {vals.map((v, i) => (
                    <span key={i} style={{ ...S.pill, background: "#21262d", color: "#e6edf3" }}>Party {i + 1}: {pctFmt(v)}</span>
                  ))}
                </div>
                <div style={{ marginTop: 8, fontSize: 12, color: "#8b949e" }}>
                  HHI: <span style={{ color: hhiColor(vals.reduce((s, v) => { const t = vals.reduce((a, x) => a + x, 0); return s + (v / t) ** 2; }, 0)) }}>
                    {fmt(vals.reduce((s, v) => { const t = vals.reduce((a, x) => a + x, 0) || 1; return s + (v / t) ** 2; }, 0))}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* All features */}
          <div style={S.card}>
            <div style={S.title}>All Computed Alternative Features</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
              {Object.entries(features).map(([k, v]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "5px 8px", background: "#0d1117", borderRadius: 4, fontSize: 12 }}>
                  <span style={{ color: "#8b949e" }}>{k.replace("alt_", "").replace(/_/g, " ")}</span>
                  <span style={{ color: "#58a6ff", fontWeight: 600, fontFamily: "monospace" }}>{fmt(v)}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
