import { useNavigate } from "react-router-dom";
import { usePortfolios } from "../hooks/usePortfolio";

function fmtUSD(v) {
  if (v == null) return "—";
  return "$" + Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function Dashboard() {
  const { data: portfolios = [], isLoading } = usePortfolios();
  const navigate = useNavigate();

  if (isLoading) return <div style={styles.loading}>Loading portfolios…</div>;

  return (
    <div style={styles.root}>
      <div style={styles.header}>
        <h1 style={styles.h1}>Dashboard</h1>
        <p style={styles.sub}>Select a portfolio from the sidebar or create a new one to get started.</p>
      </div>

      {portfolios.length === 0 ? (
        <div style={styles.empty}>
          <div style={styles.emptyIcon}>📊</div>
          <div style={styles.emptyTitle}>No portfolios yet</div>
          <div style={styles.emptyHint}>Click the + button in the sidebar to create your first portfolio.</div>
        </div>
      ) : (
        <div style={styles.grid}>
          {portfolios.map((p) => (
            <button
              key={p.id}
              style={styles.card}
              onClick={() => navigate(`/portfolio/${p.id}`)}
            >
              <div style={styles.cardName}>{p.name}</div>
              <div style={styles.cardMeta}>
                <span style={styles.badge}>{p.currency}</span>
                <span style={styles.benchmark}>vs {p.benchmark}</span>
              </div>
              <div style={styles.cardDate}>
                Created {new Date(p.created_at).toLocaleDateString()}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

const styles = {
  root: { padding: "32px 36px" },
  header: { marginBottom: 32 },
  h1: { fontSize: 24, fontWeight: 700, color: "#e2e8f0", margin: "0 0 6px" },
  sub: { fontSize: 14, color: "#64748b", margin: 0 },
  loading: { padding: "48px 36px", color: "#64748b", fontSize: 14 },
  empty: {
    textAlign: "center", padding: "80px 0",
  },
  emptyIcon: { fontSize: 48, marginBottom: 16 },
  emptyTitle: { fontSize: 18, fontWeight: 600, color: "#e2e8f0", marginBottom: 8 },
  emptyHint: { fontSize: 14, color: "#475569" },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
    gap: 20,
  },
  card: {
    background: "#0d0f14",
    border: "1px solid #1e2230",
    borderRadius: 12,
    padding: "20px 22px",
    textAlign: "left",
    cursor: "pointer",
    transition: "border-color 0.15s",
    color: "inherit",
    width: "100%",
  },
  cardName: { fontSize: 16, fontWeight: 600, color: "#e2e8f0", marginBottom: 10 },
  cardMeta: { display: "flex", alignItems: "center", gap: 8, marginBottom: 12 },
  badge: {
    background: "#1e2230",
    color: "#93c5fd",
    fontSize: 11,
    fontWeight: 600,
    padding: "2px 8px",
    borderRadius: 4,
  },
  benchmark: { fontSize: 12, color: "#475569" },
  cardDate: { fontSize: 11, color: "#334155" },
};
