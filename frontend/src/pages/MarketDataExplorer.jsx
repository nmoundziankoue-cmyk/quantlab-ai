import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { marketDataApi } from "../api/marketDataApi";

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
  table: { width: "100%", borderCollapse: "collapse", fontSize: 12 },
  th: { padding: "8px 10px", textAlign: "left", color: "#8b949e", borderBottom: "1px solid #21262d", fontWeight: 600 },
  td: { padding: "7px 10px", borderBottom: "1px solid #21262d", color: "#e6edf3" },
  pill: { display: "inline-block", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600 },
  metricBox: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 6, padding: "12px 14px", textAlign: "center" },
  metricValue: { fontSize: 20, fontWeight: 700, color: "#58a6ff", lineHeight: 1.2 },
  metricLabel: { fontSize: 11, color: "#8b949e", marginTop: 4, textTransform: "uppercase", letterSpacing: "0.06em" },
};

function fmt(n, d = 2) { return n == null ? "—" : Number(n).toFixed(d); }
function pct(n) { return n == null ? "—" : `${(Number(n) * 100).toFixed(1)}%`; }

// ---------------------------------------------------------------------------
function ProvidersTab() {
  const { data, isLoading } = useQuery({
    queryKey: ["md-providers"],
    queryFn: () => marketDataApi.listProviders().then(r => r.data),
  });
  const { data: names } = useQuery({
    queryKey: ["md-provider-names"],
    queryFn: () => marketDataApi.allProviderNames().then(r => r.data.providers),
  });

  return (
    <div>
      <div style={{ marginBottom: 16, fontSize: 13, color: "#8b949e" }}>
        {names ? `${names.length} providers supported` : "Loading…"}
      </div>

      {isLoading && <div style={{ color: "#8b949e", fontSize: 13 }}>Loading providers…</div>}

      {data && (
        <div style={{ overflowX: "auto" }}>
          <table style={S.table}>
            <thead>
              <tr>
                <th style={S.th}>Provider</th>
                <th style={S.th}>Status</th>
                <th style={S.th}>P50 Latency</th>
                <th style={S.th}>Error Rate</th>
                <th style={S.th}>Capabilities</th>
              </tr>
            </thead>
            <tbody>
              {data.map(p => (
                <tr key={p.name}>
                  <td style={{ ...S.td, fontWeight: 700 }}>{p.name}</td>
                  <td style={S.td}>
                    <span style={{ ...S.pill, background: p.is_healthy ? "#1a3a25" : "#2d1317", color: p.is_healthy ? "#3fb950" : "#f85149" }}>
                      {p.is_healthy ? "HEALTHY" : "DOWN"}
                    </span>
                  </td>
                  <td style={S.td}>{fmt(p.p50_latency_ms)} ms</td>
                  <td style={{ ...S.td, color: p.error_rate > 0.1 ? "#f85149" : "#3fb950" }}>{pct(p.error_rate)}</td>
                  <td style={{ ...S.td, color: "#8b949e", maxWidth: 300, whiteSpace: "normal" }}>
                    {p.capabilities.slice(0, 5).join(", ")}{p.capabilities.length > 5 ? ` +${p.capabilities.length - 5}` : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {names && (
        <div style={{ ...S.card, marginTop: 16 }}>
          <div style={S.title}>All Supported Providers</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {names.map(n => (
              <span key={n} style={{ ...S.pill, background: "#21262d", color: "#e6edf3", border: "1px solid #30363d" }}>{n}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
function ValidationTab() {
  const [symbol, setSymbol] = useState("AAPL");
  const [result, setResult] = useState(null);

  const severityColor = (s) => s === "critical" ? "#f85149" : s === "error" ? "#f85149" : s === "warning" ? "#d29922" : "#58a6ff";

  const mut = useMutation({
    mutationFn: async () => {
      // Generate synthetic bars for demonstration
      const bars = Array.from({ length: 100 }, (_, i) => {
        const close = 100 + i * 0.1 + (Math.random() - 0.5) * 2;
        const high = close * 1.005;
        const low = close * 0.995;
        const d = new Date("2023-01-02");
        d.setDate(d.getDate() + i);
        return {
          timestamp: d.toISOString(),
          open: close * 0.999,
          high, low, close,
          volume: 1000000 + Math.random() * 4000000,
        };
      });
      return marketDataApi.validateBars({ symbol: symbol.toUpperCase(), bars }).then(r => r.data);
    },
    onSuccess: setResult,
  });

  return (
    <div>
      <div style={{ display: "flex", gap: 10, marginBottom: 20, alignItems: "flex-end" }}>
        <div>
          <label style={S.label}>Symbol</label>
          <input style={{ ...S.input, width: 120 }} value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} placeholder="AAPL" />
        </div>
        <button style={{ ...S.btnGreen, ...(mut.isPending ? { opacity: 0.5 } : {}) }}
          onClick={() => mut.mutate()} disabled={mut.isPending}>
          {mut.isPending ? "Validating…" : "Run Validation (synthetic bars)"}
        </button>
      </div>

      {mut.error && <div style={S.err}>{mut.error.message}</div>}

      {result && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 16 }}>
            <div style={S.metricBox}><div style={{ ...S.metricValue, color: result.quality_score > 0.8 ? "#3fb950" : "#f85149" }}>{(result.quality_score * 100).toFixed(1)}%</div><div style={S.metricLabel}>Quality Score</div></div>
            <div style={S.metricBox}><div style={{ ...S.metricValue, color: result.passed ? "#3fb950" : "#f85149" }}>{result.passed ? "PASS" : "FAIL"}</div><div style={S.metricLabel}>Status</div></div>
            <div style={S.metricBox}><div style={{ ...S.metricValue, color: result.error_count > 0 ? "#f85149" : "#3fb950" }}>{result.error_count}</div><div style={S.metricLabel}>Errors</div></div>
            <div style={S.metricBox}><div style={{ ...S.metricValue, color: result.warning_count > 0 ? "#d29922" : "#3fb950" }}>{result.warning_count}</div><div style={S.metricLabel}>Warnings</div></div>
          </div>
          {result.issues?.length > 0 && (
            <div style={S.card}>
              <div style={S.title}>Issues Detected</div>
              {result.issues.map((iss, i) => (
                <div key={i} style={{ padding: "10px 14px", borderLeft: `3px solid ${severityColor(iss.severity)}`, marginBottom: 8, background: "#0d1117", borderRadius: "0 4px 4px 0" }}>
                  <div style={{ fontWeight: 700, color: severityColor(iss.severity), fontSize: 12 }}>{iss.type.toUpperCase()} · {iss.severity}</div>
                  <div style={{ fontSize: 12, color: "#e6edf3", marginTop: 2 }}>{iss.description}</div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
function FeaturesTab() {
  const { data: catalog } = useQuery({
    queryKey: ["feature-catalog"],
    queryFn: () => marketDataApi.featureCatalog().then(r => r.data),
  });

  const groups = catalog ? catalog.features.reduce((acc, f) => {
    acc[f.group] = acc[f.group] || [];
    acc[f.group].push(f);
    return acc;
  }, {}) : {};

  return (
    <div>
      <div style={{ marginBottom: 16, fontSize: 13, color: "#8b949e" }}>
        {catalog ? `${catalog.total} features available across ${Object.keys(groups).length} groups` : "Loading…"}
      </div>
      {Object.entries(groups).map(([group, features]) => (
        <div key={group} style={S.card}>
          <div style={S.title}>{group.replace(/_/g, " ")} ({features.length})</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {features.map(f => (
              <span key={f.name} title={f.description} style={{ ...S.pill, background: "#21262d", color: "#e6edf3", border: "1px solid #30363d", cursor: "default" }}>
                {f.name}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
function WarehouseTab() {
  const { data: stats, refetch } = useQuery({
    queryKey: ["warehouse-stats"],
    queryFn: () => marketDataApi.warehouseStats().then(r => r.data),
  });
  const { data: partitions } = useQuery({
    queryKey: ["warehouse-partitions"],
    queryFn: () => marketDataApi.listPartitions().then(r => r.data),
  });
  const { data: cacheStats } = useQuery({
    queryKey: ["cache-stats"],
    queryFn: () => marketDataApi.cacheStats().then(r => r.data),
  });

  const cleanup = useMutation({
    mutationFn: () => marketDataApi.cleanupWarehouse().then(r => r.data),
    onSuccess: () => refetch(),
  });

  return (
    <div>
      {stats && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 16 }}>
          <div style={S.metricBox}><div style={S.metricValue}>{stats.symbol_count}</div><div style={S.metricLabel}>Symbols</div></div>
          <div style={S.metricBox}><div style={S.metricValue}>{stats.partition_count}</div><div style={S.metricLabel}>Partitions</div></div>
          <div style={S.metricBox}><div style={S.metricValue}>{stats.total_mb.toFixed(1)} MB</div><div style={S.metricLabel}>Total Size</div></div>
          <div style={S.metricBox}><div style={{ ...S.metricValue, color: "#3fb950" }}>{(stats.cache_hit_rate * 100).toFixed(1)}%</div><div style={S.metricLabel}>Cache Hit Rate</div></div>
        </div>
      )}

      {cacheStats && (
        <div style={{ ...S.card, marginBottom: 16 }}>
          <div style={S.title}>LRU Cache</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
            <div style={S.metricBox}><div style={S.metricValue}>{cacheStats.size} / {cacheStats.maxsize}</div><div style={S.metricLabel}>Cache Entries</div></div>
            <div style={S.metricBox}><div style={S.metricValue}>{cacheStats.ttl_seconds}s</div><div style={S.metricLabel}>TTL</div></div>
            <div style={S.metricBox}><div style={{ ...S.metricValue, color: "#3fb950" }}>{(cacheStats.hit_rate * 100).toFixed(1)}%</div><div style={S.metricLabel}>Hit Rate</div></div>
          </div>
        </div>
      )}

      <div style={{ marginBottom: 16 }}>
        <button
          style={{ ...S.btn, background: "#da3633", ...(cleanup.isPending ? { opacity: 0.5 } : {}) }}
          onClick={() => cleanup.mutate()} disabled={cleanup.isPending}
        >
          {cleanup.isPending ? "Cleaning…" : "Cleanup Expired Partitions"}
        </button>
        {cleanup.data && <span style={{ marginLeft: 12, color: "#3fb950", fontSize: 13 }}>Removed {cleanup.data.removed_partitions} partitions</span>}
      </div>

      {partitions && partitions.length > 0 && (
        <div style={{ overflowX: "auto" }}>
          <table style={S.table}>
            <thead>
              <tr>
                <th style={S.th}>Symbol</th>
                <th style={S.th}>Data Type</th>
                <th style={S.th}>Timeframe</th>
                <th style={S.th}>Version</th>
                <th style={S.th}>Rows</th>
                <th style={S.th}>Quality</th>
                <th style={S.th}>Provider</th>
              </tr>
            </thead>
            <tbody>
              {partitions.map((p, i) => (
                <tr key={i}>
                  <td style={{ ...S.td, fontWeight: 700 }}>{p.symbol}</td>
                  <td style={S.td}>{p.data_type}</td>
                  <td style={S.td}>{p.timeframe}</td>
                  <td style={S.td}>v{p.version}</td>
                  <td style={S.td}>{p.row_count.toLocaleString()}</td>
                  <td style={{ ...S.td, color: p.quality_score > 0.8 ? "#3fb950" : "#d29922" }}>{(p.quality_score * 100).toFixed(0)}%</td>
                  <td style={{ ...S.td, color: "#8b949e" }}>{p.provider}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {partitions && partitions.length === 0 && (
        <div style={{ ...S.card, textAlign: "center", padding: 40, color: "#8b949e" }}>
          Warehouse is empty. Data will appear here after fetching OHLCV bars.
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
const TABS = [
  { key: "providers", label: "Providers" },
  { key: "validate", label: "Data Validation" },
  { key: "features", label: "Feature Catalog" },
  { key: "warehouse", label: "Warehouse" },
];

export default function MarketDataExplorer() {
  const [activeTab, setActiveTab] = useState("providers");

  return (
    <div style={S.page}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Market Data Explorer</h1>
        <p style={{ color: "#8b949e", margin: "4px 0 0", fontSize: 13 }}>
          Institutional data platform — 11 providers · Quality validation · Feature store · Data warehouse
        </p>
      </div>

      <div style={{ display: "flex", borderBottom: "1px solid #30363d" }}>
        {TABS.map(t => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            style={{ ...S.tab, ...(activeTab === t.key ? S.tabActive : {}) }}>
            {t.label}
          </button>
        ))}
      </div>

      <div style={{ ...S.card, borderTopLeftRadius: 0, marginTop: 0, borderTop: "none" }}>
        {activeTab === "providers" && <ProvidersTab />}
        {activeTab === "validate" && <ValidationTab />}
        {activeTab === "features" && <FeaturesTab />}
        {activeTab === "warehouse" && <WarehouseTab />}
      </div>
    </div>
  );
}
