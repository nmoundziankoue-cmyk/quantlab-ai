import { useState } from "react";

const CARD = { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "16px 20px" };
const LABEL = { fontSize: 11, color: "#8b949e", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 4 };
const HDR = { margin: "0 0 24px", fontSize: 22, fontWeight: 700, color: "#f0f6fc" };

const ASSET_CLASSES = [
  { label: "Equities", color: "#58a6ff", description: "Stocks & ETFs — cross-asset correlation, factor exposure, portfolio analysis" },
  { label: "Fixed Income", color: "#3fb950", description: "Bonds — duration, convexity, yield curves, credit buckets" },
  { label: "Options", color: "#e3b341", description: "Derivatives — Greeks, IV rank, max pain, gamma exposure" },
  { label: "Futures", color: "#f0883e", description: "Commodities & indices — term structure, roll yield, carry" },
  { label: "Crypto", color: "#a371f7", description: "Digital assets — dominance, on-chain proxies, cycle indicators" },
  { label: "Multi-Asset", color: "#ffa657", description: "Portfolio exposure across sectors, countries, currencies & factors" },
];

function AssetClassCard({ label, color, description }) {
  return (
    <div style={{ ...CARD, borderLeft: `3px solid ${color}` }}>
      <div style={{ fontSize: 14, fontWeight: 700, color, marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 12, color: "#8b949e", lineHeight: 1.5 }}>{description}</div>
    </div>
  );
}

function NavSection({ title, items, color }) {
  return (
    <div style={CARD}>
      <div style={{ fontSize: 12, fontWeight: 700, color, marginBottom: 12, letterSpacing: "0.06em" }}>{title}</div>
      {items.map(({ path, label }) => (
        <div key={path} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid #21262d" }}>
          <span style={{ fontSize: 12, color: "#c9d1d9" }}>{label}</span>
          <span style={{ fontSize: 11, color: "#8b949e" }}>{path}</span>
        </div>
      ))}
    </div>
  );
}

export default function MultiAssetDashboard() {
  const [activeTab, setActiveTab] = useState("overview");

  const NAV_ITEMS = [
    { path: "/correlation-matrix", label: "Correlation Matrix" },
    { path: "/factor-dashboard", label: "Factor Dashboard" },
    { path: "/etf-explorer", label: "ETF Explorer" },
    { path: "/bond-analytics", label: "Bond Analytics" },
    { path: "/options-analytics", label: "Options Analytics" },
    { path: "/futures-dashboard", label: "Futures Dashboard" },
    { path: "/crypto-dashboard", label: "Crypto Dashboard" },
    { path: "/portfolio-exposure", label: "Portfolio Exposure" },
    { path: "/asset-registry", label: "Asset Registry" },
    { path: "/cross-asset-explorer", label: "Cross-Asset Explorer" },
    { path: "/market-map", label: "Market Map" },
  ];

  return (
    <div style={{ padding: 24, color: "#f0f6fc", fontFamily: "monospace", maxWidth: 1200 }}>
      <div style={{ fontSize: 11, color: "#ffa657", letterSpacing: "0.1em", marginBottom: 4 }}>M16 — INSTITUTIONAL MULTI-ASSET ANALYTICS</div>
      <h1 style={HDR}>Multi-Asset Platform</h1>

      <div style={{ display: "flex", gap: 12, marginBottom: 24 }}>
        {["overview", "navigation", "capabilities"].map(t => (
          <button key={t} onClick={() => setActiveTab(t)} style={{
            padding: "6px 16px", borderRadius: 6, border: "1px solid",
            borderColor: activeTab === t ? "#ffa657" : "#21262d",
            background: activeTab === t ? "#ffa65722" : "transparent",
            color: activeTab === t ? "#ffa657" : "#8b949e",
            fontSize: 12, cursor: "pointer", fontFamily: "monospace",
          }}>{t.toUpperCase()}</button>
        ))}
      </div>

      {activeTab === "overview" && (
        <div>
          <div style={{ ...CARD, marginBottom: 20, padding: "20px 24px" }}>
            <div style={{ fontSize: 14, color: "#ffa657", fontWeight: 700, marginBottom: 8 }}>Bloomberg Terminal / FactSet / Refinitiv — Comparable</div>
            <div style={{ fontSize: 13, color: "#c9d1d9", lineHeight: 1.7 }}>
              Institutional-grade multi-asset analytics platform covering 9 asset classes with
              30+ API endpoints, pure-Python deterministic engines, and real-time cross-asset
              analytics. From equities to crypto, bonds to futures — unified in a single interface.
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 12 }}>
            {ASSET_CLASSES.map(ac => <AssetClassCard key={ac.label} {...ac} />)}
          </div>

          <div style={{ ...CARD, marginTop: 20 }}>
            <div style={LABEL}>Platform Architecture</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginTop: 12 }}>
              {[
                ["9 Services", "Pure Python engines — no scipy, no numpy, fully deterministic"],
                ["30+ Endpoints", "FastAPI router at /multi-asset with Pydantic v2 schemas"],
                ["12 Pages", "Dark institutional UI with SVG charts and lazy loading"],
              ].map(([title, desc]) => (
                <div key={title} style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 20, fontWeight: 700, color: "#ffa657" }}>{title}</div>
                  <div style={{ fontSize: 11, color: "#8b949e", marginTop: 4 }}>{desc}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === "navigation" && (
        <NavSection title="M16 — MULTI-ASSET PAGES" items={NAV_ITEMS} color="#ffa657" />
      )}

      {activeTab === "capabilities" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          {[
            ["Asset Registry", "9 asset types, ISIN/CUSIP/SEDOL lookup, multi-identifier"],
            ["Cross-Asset", "Correlation matrices, rolling betas, lead-lag, spillover, GEX"],
            ["Factor Engine", "10 factors, exposures, attribution, clustering"],
            ["ETF Intelligence", "Holdings, overlap, tracking difference, flow estimation"],
            ["Bond Analytics", "Duration, convexity, DV01, yield curves, credit buckets"],
            ["Options Analytics", "Greeks, IV rank/percentile, max pain, gamma flip"],
            ["Futures Analytics", "Contango, roll yield, carry ranking, term structure"],
            ["Crypto Intelligence", "Dominance, NVT proxy, market breadth, cycle phase"],
            ["Portfolio Exposure", "Sector, country, currency, factor, concentration metrics"],
          ].map(([title, desc]) => (
            <div key={title} style={{ ...CARD, borderLeft: "3px solid #ffa657" }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: "#ffa657", marginBottom: 4 }}>{title}</div>
              <div style={{ fontSize: 12, color: "#8b949e" }}>{desc}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
