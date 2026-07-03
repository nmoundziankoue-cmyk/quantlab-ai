import { NavLink, useNavigate } from "react-router-dom";
import { usePortfolios, useCreatePortfolio } from "../../hooks/usePortfolio";
import usePortfolioStore from "../../store/usePortfolioStore";
import useAuthStore from "../../store/useAuthStore";
import useRegimeStore, { REGIME_COLORS } from "../../store/useRegimeStore";
import { useState } from "react";

// ── Navigation groups ─────────────────────────────────────────────────────────
const CORE_NAV = [
  { label: "Dashboard", to: "/" },
  { label: "Markets", to: "/markets" },
  { label: "Portfolio", to: "/portfolio" },
  { label: "Research", to: "/research" },
  { label: "Trading", to: "/trading" },
];

const M20_NAV = [
  { label: "M20 Overview", to: "/m20" },
  { label: "Regime Detection", to: "/m20/regime" },
  { label: "Correlation Matrix", to: "/m20/correlation" },
  { label: "Strategy Comparison", to: "/m20/comparison" },
];

const M19_NAV = [
  { label: "M19 Overview", to: "/m19-dashboard" },
  { label: "Backtest Studio", to: "/m19-backtest" },
  { label: "Monte Carlo", to: "/m19-monte-carlo" },
  { label: "Walk-Forward", to: "/m19-walkforward" },
  { label: "Factor Exposure", to: "/m19-factors" },
  { label: "Optimization Lab", to: "/m19-optimization" },
  { label: "Execution Sim.", to: "/m19-execution" },
  { label: "Risk Dashboard", to: "/m19-risk" },
  { label: "Equity Curves", to: "/m19-equity-curves" },
];

const M18_NAV = [
  { label: "M18 Overview", to: "/m18-dashboard" },
  { label: "Streaming Monitor", to: "/m18-streaming" },
  { label: "Market Gateway", to: "/m18-gateway" },
  { label: "Microstructure", to: "/m18-microstructure" },
  { label: "Feature Engine", to: "/m18-features" },
  { label: "Risk Engine", to: "/m18-risk" },
  { label: "Portfolio Intel", to: "/m18-portfolio-intel" },
  { label: "Alert Center", to: "/m18-alerts" },
  { label: "Yield Curve", to: "/m18-yield-curve" },
  { label: "Stress Tests", to: "/m18-stress-test" },
  { label: "Eff. Frontier", to: "/m18-frontier" },
  { label: "Agent Console", to: "/m18-agent-console" },
];

const M17_NAV = [
  { label: "IMS Dashboard", to: "/m17-trading" },
  { label: "Order Management", to: "/m17-oms" },
  { label: "Trade Blotter", to: "/m17-blotter" },
  { label: "Positions", to: "/m17-positions" },
  { label: "Risk Limits", to: "/m17-risk" },
  { label: "TCA", to: "/m17-tca" },
];

const M15_NAV = [
  { label: "Event Dashboard", to: "/event-dashboard" },
  { label: "Corporate Events", to: "/corporate-events" },
  { label: "Macro Events", to: "/macro-events" },
  { label: "Event Study", to: "/event-study" },
  { label: "Impact Analysis", to: "/event-impact" },
];

const M16_NAV = [
  { label: "Multi-Asset", to: "/multi-asset-dashboard" },
  { label: "Factor Dashboard", to: "/factor-dashboard" },
  { label: "Options Analytics", to: "/options-analytics" },
  { label: "Portfolio Exposure", to: "/portfolio-exposure" },
];

const LEGACY_NAV = [
  { label: "Portfolio Optimizer", to: "/portfolio-optimizer" },
  { label: "AI Copilot", to: "/copilot" },
  { label: "Agent Workspace", to: "/agent-workspace" },
  { label: "Risk Center", to: "/risk-center" },
  { label: "Live Markets", to: "/live-markets" },
  { label: "News Intelligence", to: "/news-intelligence" },
  { label: "Options Desk", to: "/options-desk" },
  { label: "Security", to: "/security" },
  { label: "System Metrics", to: "/system-metrics" },
];

// ── Section component ─────────────────────────────────────────────────────────
function NavSection({ title, color, items, accentBorder = false }) {
  const [open, setOpen] = useState(true);
  return (
    <div>
      <button
        onClick={() => setOpen((v) => !v)}
        style={{ ...S.sectionBtn, color }}
      >
        <span style={accentBorder ? { ...S.sectionDot, background: color } : undefined} />
        {title}
        <span style={{ marginLeft: "auto", opacity: 0.5, fontSize: 9 }}>{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <nav style={S.nav}>
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/" || item.to === "/m20" || item.to === "/m19-dashboard"}
              style={({ isActive }) => ({
                ...S.navLink,
                ...(isActive ? S.navActive : {}),
              })}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      )}
    </div>
  );
}

// ── Main Sidebar ──────────────────────────────────────────────────────────────
export default function Sidebar() {
  const { data: portfolios = [], isLoading } = usePortfolios();
  const createPortfolio = useCreatePortfolio();
  const setSelected = usePortfolioStore((s) => s.setSelectedPortfolioId);
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const regime = useRegimeStore((s) => s.regime);
  const regimeColor = REGIME_COLORS[regime] ?? "#7A84A0";

  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [formError, setFormError] = useState("");

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setFormError("");
    try {
      const p = await createPortfolio.mutateAsync({ name: name.trim(), currency: "USD", benchmark: "SPY" });
      setName("");
      setShowForm(false);
      setSelected(p.id);
      navigate(`/portfolio/${p.id}`);
    } catch (err) {
      setFormError(err.message);
    }
  };

  return (
    <aside style={{ ...S.sidebar, borderTop: `3px solid ${regimeColor}` }}>
      {/* Brand */}
      <div style={S.brand}>
        <div style={{ ...S.brandMark, borderColor: regimeColor }}>
          <span style={S.brandQ}>Q</span>
        </div>
        <div>
          <div style={S.brandName}>QuantLab AI</div>
          <div style={S.brandSub}>Precision Instrument</div>
        </div>
      </div>

      {/* Scrollable nav area */}
      <div style={S.scrollArea}>
        {/* Core pages */}
        <nav style={{ ...S.nav, paddingTop: 8 }}>
          {CORE_NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              style={({ isActive }) => ({
                ...S.navLink,
                ...(isActive ? S.navActive : {}),
              })}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div style={S.divider} />

        <NavSection title="M20 — QUANT PLATFORM" color="#E2A52B" items={M20_NAV} accentBorder />
        <NavSection title="M19 — QUANT RESEARCH" color="#9D7FEA" items={M19_NAV} />
        <NavSection title="M18 — REAL-TIME OS" color="#567EFF" items={M18_NAV} />
        <NavSection title="M17 — TRADING IMS" color="#27C784" items={M17_NAV} />
        <NavSection title="M16 — MULTI-ASSET" color="#7A84A0" items={M16_NAV} />
        <NavSection title="M15 — EVENTS" color="#7A84A0" items={M15_NAV} />
        <NavSection title="LEGACY M6–M14" color="#454D66" items={LEGACY_NAV} />

        {/* Portfolios */}
        <div style={S.divider} />
        <div style={S.portfolioHeader}>
          <span style={S.portfolioLabel}>PORTFOLIOS</span>
          <button style={S.addBtn} onClick={() => setShowForm((v) => !v)}>+</button>
        </div>
        {showForm && (
          <form onSubmit={handleCreate} style={{ padding: "0 8px 8px" }}>
            <input
              autoFocus
              placeholder="Portfolio name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              style={{ width: "100%", marginBottom: 6 }}
            />
            {formError && <div style={{ color: "var(--negative)", fontSize: 11, marginBottom: 4 }}>{formError}</div>}
            <button
              type="submit"
              disabled={createPortfolio.isPending}
              style={S.submitBtn}
            >
              {createPortfolio.isPending ? "Creating…" : "Create"}
            </button>
          </form>
        )}
        {isLoading ? (
          <div style={S.empty}>Loading…</div>
        ) : portfolios.length === 0 ? (
          <div style={S.empty}>No portfolios yet</div>
        ) : (
          <nav style={S.nav}>
            {portfolios.map((p) => (
              <NavLink
                key={p.id}
                to={`/portfolio/${p.id}`}
                onClick={() => setSelected(p.id)}
                style={({ isActive }) => ({
                  ...S.navLink,
                  ...(isActive ? S.navActive : {}),
                })}
              >
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.name}</span>
                <span style={{ fontSize: 10, color: "var(--text-3)", marginLeft: 6, flexShrink: 0 }}>{p.currency}</span>
              </NavLink>
            ))}
          </nav>
        )}
      </div>

      {/* Footer */}
      <div style={S.footer}>
        {user && (
          <div style={S.userRow}>
            <div style={{ ...S.userAvatar, background: "var(--accent)" }}>
              {(user.email?.[0] ?? "?").toUpperCase()}
            </div>
            <div style={{ overflow: "hidden" }}>
              <div style={S.userName}>{user.full_name || user.email}</div>
              <div style={S.userRole}>{user.role ?? "analyst"}</div>
            </div>
          </div>
        )}
        <button
          style={S.logoutBtn}
          onClick={async () => { await logout(); navigate("/login"); }}
        >
          Sign out
        </button>
      </div>
    </aside>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────
const S = {
  sidebar: {
    width: 224,
    minHeight: "100vh",
    background: "var(--panel)",
    borderRight: "1px solid var(--border)",
    display: "flex",
    flexDirection: "column",
    flexShrink: 0,
    /* border-top is set dynamically from regime color */
  },
  brand: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "16px 16px 14px",
    borderBottom: "1px solid var(--border)",
    flexShrink: 0,
  },
  brandMark: {
    width: 30,
    height: 30,
    border: "2px solid",
    borderRadius: 6,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
    transition: "border-color 0.3s",
  },
  brandQ: {
    fontFamily: "var(--font-display)",
    fontWeight: 700,
    fontSize: 15,
    color: "var(--text-1)",
    lineHeight: 1,
  },
  brandName: {
    fontFamily: "var(--font-display)",
    fontWeight: 600,
    fontSize: 13,
    color: "var(--text-1)",
    lineHeight: 1.2,
  },
  brandSub: {
    fontFamily: "var(--font-mono)",
    fontSize: 9,
    color: "var(--text-3)",
    textTransform: "uppercase",
    letterSpacing: "0.1em",
    marginTop: 2,
  },
  scrollArea: {
    flex: 1,
    overflowY: "auto",
    overflowX: "hidden",
    padding: "0 0 8px",
  },
  divider: {
    height: 1,
    background: "var(--border)",
    margin: "8px 8px",
  },
  nav: { padding: "0 6px" },
  navLink: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "6px 10px",
    borderRadius: 5,
    color: "var(--text-2)",
    fontSize: 12,
    fontWeight: 500,
    textDecoration: "none",
    marginBottom: 1,
    transition: "background 0.1s, color 0.1s",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  navActive: {
    background: "var(--panel-hover)",
    color: "var(--text-1)",
    fontWeight: 600,
  },
  sectionBtn: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    width: "100%",
    padding: "10px 10px 4px 16px",
    background: "none",
    border: "none",
    fontSize: 9,
    fontFamily: "var(--font-display)",
    fontWeight: 700,
    letterSpacing: "0.1em",
    cursor: "pointer",
    textAlign: "left",
  },
  sectionDot: {
    width: 5,
    height: 5,
    borderRadius: "50%",
    flexShrink: 0,
  },
  portfolioHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "10px 16px 4px",
  },
  portfolioLabel: {
    fontFamily: "var(--font-display)",
    fontSize: 9,
    fontWeight: 700,
    letterSpacing: "0.1em",
    color: "var(--text-3)",
    textTransform: "uppercase",
  },
  addBtn: {
    background: "none",
    border: "none",
    color: "var(--text-3)",
    fontSize: 16,
    lineHeight: 1,
    padding: "0 2px",
    cursor: "pointer",
  },
  empty: {
    padding: "4px 16px",
    color: "var(--text-3)",
    fontSize: 11,
  },
  submitBtn: {
    width: "100%",
    background: "var(--accent)",
    border: "none",
    borderRadius: 5,
    color: "#fff",
    fontSize: 12,
    fontWeight: 600,
    padding: "7px 0",
    cursor: "pointer",
  },
  footer: {
    padding: "10px 8px 16px",
    borderTop: "1px solid var(--border)",
    display: "flex",
    flexDirection: "column",
    gap: 4,
    flexShrink: 0,
  },
  userRow: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "6px 8px",
  },
  userAvatar: {
    width: 24,
    height: 24,
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 10,
    fontWeight: 700,
    color: "#fff",
    flexShrink: 0,
  },
  userName: {
    fontFamily: "var(--font-body)",
    fontSize: 11,
    fontWeight: 600,
    color: "var(--text-1)",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  userRole: {
    fontFamily: "var(--font-mono)",
    fontSize: 9,
    color: "var(--text-3)",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  logoutBtn: {
    margin: "0 4px",
    padding: "6px 10px",
    background: "none",
    border: "1px solid var(--border)",
    borderRadius: 5,
    color: "var(--text-2)",
    fontSize: 11,
    cursor: "pointer",
    textAlign: "left",
  },
};
