import { NavLink, useNavigate } from "react-router-dom";
import { usePortfolios, useCreatePortfolio } from "../../hooks/usePortfolio";
import usePortfolioStore from "../../store/usePortfolioStore";
import useAuthStore from "../../store/useAuthStore";
import { useState } from "react";

const NAV_ITEMS = [
  { label: "Dashboard", to: "/", exact: true },
  { label: "Markets", to: "/markets", exact: false },
  { label: "Research", to: "/research", exact: false },
  { label: "Analytics", to: "/analytics", exact: false },
  { label: "Trading", to: "/trading", exact: false },
  { label: "Orders", to: "/orders", exact: false },
  { label: "Trade Blotter", to: "/blotter", exact: false },
  { label: "Exec Analytics", to: "/execution-analytics", exact: false },
  { label: "Paper Trading", to: "/paper-trading", exact: false },
  { label: "Brokers", to: "/brokers", exact: false },
];

const M18_NAV_ITEMS = [
  { label: "M18 Dashboard", to: "/m18-dashboard", exact: false },
  { label: "Streaming Monitor", to: "/m18-streaming", exact: false },
  { label: "Market Gateway", to: "/m18-gateway", exact: false },
  { label: "Microstructure", to: "/m18-microstructure", exact: false },
  { label: "Feature Engine", to: "/m18-features", exact: false },
  { label: "Risk Engine", to: "/m18-risk", exact: false },
  { label: "Portfolio Intel", to: "/m18-portfolio-intel", exact: false },
  { label: "Alert Center", to: "/m18-alerts", exact: false },
  { label: "Economic Intel", to: "/m18-economic", exact: false },
  { label: "News Intel", to: "/m18-news", exact: false },
  { label: "Earnings Intel", to: "/m18-earnings", exact: false },
  { label: "AI Agents", to: "/m18-agents", exact: false },
  { label: "Watchlists", to: "/m18-watchlists", exact: false },
  { label: "Yield Curve", to: "/m18-yield-curve", exact: false },
  { label: "Stress Tests", to: "/m18-stress-test", exact: false },
  { label: "Attribution", to: "/m18-attribution", exact: false },
  { label: "Eff. Frontier", to: "/m18-frontier", exact: false },
  { label: "News Trends", to: "/m18-trends", exact: false },
  { label: "Earnings Calendar", to: "/m18-earnings-calendar", exact: false },
  { label: "Economic Calendar", to: "/m18-economic-calendar", exact: false },
];

const M17_NAV_ITEMS = [
  { label: "IMS Dashboard", to: "/m17-trading", exact: false },
  { label: "Order Management", to: "/m17-oms", exact: false },
  { label: "Order Ticket", to: "/m17-order-ticket", exact: false },
  { label: "Trade Blotter", to: "/m17-blotter", exact: false },
  { label: "Positions", to: "/m17-positions", exact: false },
  { label: "Risk Limits", to: "/m17-risk", exact: false },
  { label: "Trade Analytics", to: "/m17-analytics", exact: false },
  { label: "Broker Management", to: "/m17-brokers", exact: false },
  { label: "Paper Simulator", to: "/m17-paper-trading", exact: false },
  { label: "Portfolio Accounting", to: "/m17-accounting", exact: false },
  { label: "Performance Attribution", to: "/m17-attribution", exact: false },
  { label: "Execution Cost (TCA)", to: "/m17-tca", exact: false },
  { label: "Execution Monitor", to: "/m17-execution", exact: false },
  { label: "Order Book", to: "/m17-orders", exact: false },
  { label: "Execution History", to: "/m17-history", exact: false },
];

const M16_NAV_ITEMS = [
  { label: "Multi-Asset Dashboard", to: "/multi-asset-dashboard", exact: false },
  { label: "Correlation Matrix", to: "/correlation-matrix", exact: false },
  { label: "Factor Dashboard", to: "/factor-dashboard", exact: false },
  { label: "ETF Explorer", to: "/etf-explorer", exact: false },
  { label: "Bond Analytics", to: "/bond-analytics", exact: false },
  { label: "Options Analytics", to: "/options-analytics", exact: false },
  { label: "Futures Dashboard", to: "/futures-dashboard", exact: false },
  { label: "Crypto Dashboard", to: "/crypto-dashboard", exact: false },
  { label: "Portfolio Exposure", to: "/portfolio-exposure", exact: false },
  { label: "Asset Registry", to: "/asset-registry", exact: false },
  { label: "Cross-Asset Explorer", to: "/cross-asset-explorer", exact: false },
  { label: "Market Map", to: "/market-map", exact: false },
];

const M15_NAV_ITEMS = [
  { label: "Event Dashboard", to: "/event-dashboard", exact: false },
  { label: "Corporate Events", to: "/corporate-events", exact: false },
  { label: "Macro Events", to: "/macro-events", exact: false },
  { label: "Event Timeline", to: "/event-timeline", exact: false },
  { label: "Event Calendar", to: "/event-calendar", exact: false },
  { label: "Event Study", to: "/event-study", exact: false },
  { label: "Impact Analysis", to: "/event-impact", exact: false },
  { label: "Catalyst Dashboard", to: "/catalyst-dashboard", exact: false },
  { label: "AI Intelligence", to: "/ai-event-intelligence", exact: false },
  { label: "Event Search", to: "/event-search", exact: false },
  { label: "Research Reports", to: "/event-reports", exact: false },
  { label: "Event Heatmap", to: "/event-heatmap", exact: false },
];

const M14_NAV_ITEMS = [
  { label: "Alt Data Explorer", to: "/alt-data-explorer", exact: false },
  { label: "Document Viewer", to: "/alt-document-viewer", exact: false },
  { label: "SEC Filing Reader", to: "/alt-sec-filing-reader", exact: false },
  { label: "KG Explorer", to: "/alt-knowledge-graph", exact: false },
  { label: "Event Timeline", to: "/alt-event-timeline", exact: false },
  { label: "Insider Activity", to: "/alt-insider-activity", exact: false },
  { label: "Patent Intelligence", to: "/alt-patent-intelligence", exact: false },
  { label: "Transcript Analyzer", to: "/alt-transcript-analyzer", exact: false },
  { label: "Alt Search", to: "/alt-search", exact: false },
];

const M13_NAV_ITEMS = [
  { label: "Market Data Explorer", to: "/market-data-explorer", exact: false },
  { label: "Dataset Builder", to: "/dataset-builder", exact: false },
];

const M12_NAV_ITEMS = [
  { label: "Portfolio Optimizer", to: "/portfolio-optimizer", exact: false },
];

const M9_NAV_ITEMS = [
  { label: "Live Markets", to: "/live-markets", exact: false },
  { label: "Risk Center", to: "/risk-center", exact: false },
  { label: "Strategy Builder", to: "/strategy-builder", exact: false },
  { label: "Execution Monitor", to: "/execution-monitor", exact: false },
  { label: "Agent Workspace", to: "/agent-workspace", exact: false },
  { label: "Research Notebook", to: "/research-notebook", exact: false },
  { label: "Knowledge Explorer", to: "/knowledge-explorer", exact: false },
  { label: "News Intelligence", to: "/news-intelligence", exact: false },
  { label: "Provider Dashboard", to: "/provider-dashboard", exact: false },
  { label: "System Metrics", to: "/system-metrics", exact: false },
];

const M8_NAV_ITEMS = [
  { label: "Notifications", to: "/notifications", exact: false },
  { label: "Security", to: "/security", exact: false },
];

const M7_NAV_ITEMS = [
  { label: "Options Desk", to: "/options-desk", exact: false },
  { label: "Market Intel", to: "/market-intelligence", exact: false },
  { label: "Orchestrator", to: "/agent-orchestrator", exact: false },
  { label: "Econ Calendar", to: "/economic-calendar", exact: false },
  { label: "Knowledge Graph", to: "/knowledge-graph", exact: false },
];

const M6_NAV_ITEMS = [
  { label: "Research Hub", to: "/research-dashboard", exact: false },
  { label: "Workspace", to: "/workspace", exact: false },
  { label: "AI Copilot", to: "/copilot", exact: false },
  { label: "Documents", to: "/documents", exact: false },
  { label: "News Terminal", to: "/news-terminal", exact: false },
  { label: "Alt Data", to: "/alternative-data", exact: false },
  { label: "Reports", to: "/reports", exact: false },
  { label: "Screeners", to: "/screeners", exact: false },
  { label: "AI Agents", to: "/agents", exact: false },
];

export default function Sidebar() {
  const { data: portfolios = [], isLoading } = usePortfolios();
  const createPortfolio = useCreatePortfolio();
  const setSelected = usePortfolioStore((s) => s.setSelectedPortfolioId);
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setError("");
    try {
      const p = await createPortfolio.mutateAsync({ name: name.trim(), currency: "USD", benchmark: "SPY" });
      setName("");
      setShowForm(false);
      setSelected(p.id);
      navigate(`/portfolio/${p.id}`);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <aside style={styles.sidebar}>
      <div style={styles.brand}>
        <span style={styles.brandLogo}>Q</span>
        <span style={styles.brandName}>QuantLab AI</span>
      </div>

      <nav style={styles.nav}>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.exact}
            style={({ isActive }) => ({
              ...styles.navLink,
              ...(isActive ? styles.navLinkActive : {}),
            })}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div style={{ padding: "12px 8px 4px", fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", color: "#79c0ff" }}>
        M18 — REAL-TIME INSTITUTIONAL OS
      </div>
      <nav style={styles.nav}>
        {M18_NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.exact}
            style={({ isActive }) => ({
              ...styles.navLink,
              ...(isActive ? styles.navLinkActive : {}),
            })}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div style={{ padding: "12px 8px 4px", fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", color: "#3fb950" }}>
        M17 — INSTITUTIONAL TRADING IMS
      </div>
      <nav style={styles.nav}>
        {M17_NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.exact}
            style={({ isActive }) => ({
              ...styles.navLink,
              ...(isActive ? styles.navLinkActive : {}),
            })}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div style={{ padding: "12px 8px 4px", fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", color: "#ffa657" }}>
        M16 — MULTI-ASSET ANALYTICS
      </div>
      <nav style={styles.nav}>
        {M16_NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.exact}
            style={({ isActive }) => ({
              ...styles.navLink,
              ...(isActive ? styles.navLinkActive : {}),
            })}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div style={{ padding: "12px 8px 4px", fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", color: "#d2a8ff" }}>
        M15 — EVENT INTELLIGENCE
      </div>
      <nav style={styles.nav}>
        {M15_NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.exact}
            style={({ isActive }) => ({
              ...styles.navLink,
              ...(isActive ? styles.navLinkActive : {}),
            })}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div style={{ padding: "12px 8px 4px", fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", color: "#1f6feb" }}>
        M14 — ALT DATA INTELLIGENCE
      </div>
      <nav style={styles.nav}>
        {M14_NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.exact}
            style={({ isActive }) => ({
              ...styles.navLink,
              ...(isActive ? styles.navLinkActive : {}),
            })}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div style={{ padding: "12px 8px 4px", fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", color: "#475569" }}>
        M13 — MARKET DATA PLATFORM
      </div>
      <nav style={styles.nav}>
        {M13_NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.exact}
            style={({ isActive }) => ({
              ...styles.navLink,
              ...(isActive ? styles.navLinkActive : {}),
            })}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div style={{ padding: "12px 8px 4px", fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", color: "#475569" }}>
        M12 — PORTFOLIO OPTIMIZATION
      </div>
      <nav style={styles.nav}>
        {M12_NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.exact}
            style={({ isActive }) => ({
              ...styles.navLink,
              ...(isActive ? styles.navLinkActive : {}),
            })}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div style={{ padding: "12px 8px 4px", fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", color: "#475569" }}>
        M9 — INTELLIGENCE
      </div>
      <nav style={styles.nav}>
        {M9_NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.exact}
            style={({ isActive }) => ({
              ...styles.navLink,
              ...(isActive ? styles.navLinkActive : {}),
            })}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div style={{ padding: "12px 8px 4px", fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", color: "#475569" }}>
        M8 — PRODUCTION
      </div>
      <nav style={styles.nav}>
        {M8_NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.exact}
            style={({ isActive }) => ({
              ...styles.navLink,
              ...(isActive ? styles.navLinkActive : {}),
            })}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div style={{ padding: "12px 8px 4px", fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", color: "#475569" }}>
        M7 — INSTITUTIONAL
      </div>
      <nav style={styles.nav}>
        {M7_NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.exact}
            style={({ isActive }) => ({
              ...styles.navLink,
              ...(isActive ? styles.navLinkActive : {}),
            })}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div style={{ padding: "12px 8px 4px", fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", color: "#475569" }}>
        M6 — AI RESEARCH
      </div>
      <nav style={styles.nav}>
        {M6_NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.exact}
            style={({ isActive }) => ({
              ...styles.navLink,
              ...(isActive ? styles.navLinkActive : {}),
            })}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div style={styles.section}>
        <div style={styles.sectionHeader}>
          <span style={styles.sectionLabel}>PORTFOLIOS</span>
          <button style={styles.addBtn} onClick={() => setShowForm((v) => !v)} title="New portfolio">
            +
          </button>
        </div>

        {showForm && (
          <form onSubmit={handleCreate} style={styles.form}>
            <input
              autoFocus
              style={styles.input}
              placeholder="Portfolio name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            {error && <div style={styles.formError}>{error}</div>}
            <button style={styles.submitBtn} type="submit" disabled={createPortfolio.isPending}>
              {createPortfolio.isPending ? "Creating…" : "Create"}
            </button>
          </form>
        )}

        {isLoading ? (
          <div style={styles.empty}>Loading…</div>
        ) : portfolios.length === 0 ? (
          <div style={styles.empty}>No portfolios yet</div>
        ) : (
          portfolios.map((p) => (
            <NavLink
              key={p.id}
              to={`/portfolio/${p.id}`}
              onClick={() => setSelected(p.id)}
              style={({ isActive }) => ({
                ...styles.portfolioLink,
                ...(isActive ? styles.portfolioLinkActive : {}),
              })}
            >
              <span style={styles.portfolioName}>{p.name}</span>
              <span style={styles.portfolioCcy}>{p.currency}</span>
            </NavLink>
          ))
        )}
      </div>

      <div style={styles.footer}>
        {user && (
          <div style={styles.userRow}>
            <div style={styles.userAvatar}>{(user.email?.[0] ?? "?").toUpperCase()}</div>
            <div style={styles.userInfo}>
              <div style={styles.userName}>{user.full_name || user.email}</div>
              <div style={styles.userRole}>{user.role}</div>
            </div>
          </div>
        )}
        <button
          style={styles.logoutBtn}
          onClick={async () => { await logout(); navigate("/login"); }}
        >
          Sign out
        </button>
        <span style={styles.footerVersion}>QuantLab AI v2.0</span>
      </div>
    </aside>
  );
}

const styles = {
  sidebar: {
    width: 220,
    minHeight: "100vh",
    background: "#0d0f14",
    borderRight: "1px solid #1e2230",
    display: "flex",
    flexDirection: "column",
    flexShrink: 0,
  },
  brand: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "20px 16px",
    borderBottom: "1px solid #1e2230",
  },
  brandLogo: {
    width: 28,
    height: 28,
    borderRadius: 6,
    background: "#2563eb",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 700,
    fontSize: 14,
    color: "#fff",
    lineHeight: "28px",
    textAlign: "center",
  },
  brandName: { color: "#e2e8f0", fontWeight: 600, fontSize: 15 },
  nav: { padding: "12px 8px 0" },
  navLink: {
    display: "block",
    padding: "8px 12px",
    borderRadius: 6,
    color: "#94a3b8",
    fontSize: 13,
    fontWeight: 500,
    textDecoration: "none",
    marginBottom: 2,
  },
  navLinkActive: { background: "#1e2230", color: "#e2e8f0" },
  section: { flex: 1, padding: "16px 8px 0" },
  sectionHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "0 8px 8px",
  },
  sectionLabel: { fontSize: 10, fontWeight: 600, letterSpacing: "0.08em", color: "#475569" },
  addBtn: {
    background: "none",
    border: "none",
    color: "#475569",
    cursor: "pointer",
    fontSize: 18,
    lineHeight: 1,
    padding: "0 2px",
  },
  form: { padding: "0 4px 10px" },
  input: {
    width: "100%",
    background: "#1e2230",
    border: "1px solid #2d3748",
    borderRadius: 6,
    color: "#e2e8f0",
    fontSize: 13,
    padding: "6px 10px",
    marginBottom: 6,
    outline: "none",
    boxSizing: "border-box",
  },
  formError: { color: "#f87171", fontSize: 11, marginBottom: 4 },
  submitBtn: {
    width: "100%",
    background: "#2563eb",
    border: "none",
    borderRadius: 6,
    color: "#fff",
    fontSize: 13,
    fontWeight: 600,
    padding: "7px 0",
    cursor: "pointer",
  },
  portfolioLink: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "7px 12px",
    borderRadius: 6,
    color: "#94a3b8",
    fontSize: 13,
    textDecoration: "none",
    marginBottom: 2,
  },
  portfolioLinkActive: { background: "#1e2230", color: "#e2e8f0" },
  portfolioName: { overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" },
  portfolioCcy: { fontSize: 10, color: "#475569", flexShrink: 0, marginLeft: 6 },
  empty: { padding: "4px 12px", color: "#475569", fontSize: 12 },
  footer: {
    padding: "12px 8px 20px",
    display: "flex",
    flexDirection: "column",
    gap: 2,
    borderTop: "1px solid #1e2230",
    marginTop: "auto",
  },
  userRow: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "8px 12px",
    marginBottom: 4,
  },
  userAvatar: {
    width: 26,
    height: 26,
    borderRadius: "50%",
    background: "#2563eb",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 11,
    fontWeight: 700,
    color: "#fff",
    flexShrink: 0,
  },
  userInfo: { overflow: "hidden" },
  userName: {
    fontSize: 12,
    fontWeight: 600,
    color: "#e2e8f0",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  userRole: { fontSize: 10, color: "#475569" },
  logoutBtn: {
    margin: "0 8px 4px",
    padding: "7px 12px",
    background: "none",
    border: "1px solid #2d3748",
    borderRadius: 6,
    color: "#94a3b8",
    fontSize: 12,
    cursor: "pointer",
    textAlign: "left",
    width: "calc(100% - 16px)",
  },
  footerVersion: {
    padding: "7px 12px",
    color: "#2d3748",
    fontSize: 11,
  },
};
