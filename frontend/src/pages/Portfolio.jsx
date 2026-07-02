import { useEffect } from "react";
import { useParams } from "react-router-dom";
import {
  usePortfolioSummary,
  usePortfolioPerformance,
  usePortfolioAllocation,
  useTransactions,
  useDeleteTransaction,
} from "../hooks/usePortfolio";
import usePortfolioStore from "../store/usePortfolioStore";
import HoldingsTable from "../components/portfolio/HoldingsTable";
import PerformanceChart from "../components/portfolio/PerformanceChart";
import AllocationChart from "../components/portfolio/AllocationChart";
import TransactionModal from "../components/portfolio/TransactionModal";

const TABS = ["Holdings", "Performance", "Allocation", "Transactions"];

function KpiCard({ label, value, positive }) {
  return (
    <div style={kpi.card}>
      <div style={kpi.label}>{label}</div>
      <div
        style={{
          ...kpi.value,
          color: positive === true ? "#4ade80" : positive === false ? "#f87171" : "#e2e8f0",
        }}
      >
        {value}
      </div>
    </div>
  );
}

function fmtUSD(v) {
  if (v == null) return "—";
  const abs = Math.abs(v);
  return (v < 0 ? "-$" : "$") + abs.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtPct(v) {
  if (v == null) return "—";
  return (v >= 0 ? "+" : "") + v.toFixed(2) + "%";
}

export default function Portfolio() {
  const { id } = useParams();
  const activeTab = usePortfolioStore((s) => s.activeTab);
  const setTab = usePortfolioStore((s) => s.setActiveTab);
  const setSelected = usePortfolioStore((s) => s.setSelectedPortfolioId);
  const modalOpen = usePortfolioStore((s) => s.transactionModalOpen);
  const openModal = usePortfolioStore((s) => s.openTransactionModal);

  useEffect(() => { setSelected(id); }, [id, setSelected]);

  const { data: summary, isLoading: sumLoading, error: sumError } = usePortfolioSummary(id);
  const { data: performance, isLoading: perfLoading } = usePortfolioPerformance(id);
  const { data: allocation } = usePortfolioAllocation(id);
  const { data: transactions = [] } = useTransactions(id);
  const deleteTx = useDeleteTransaction(id);

  if (sumLoading) return <div style={styles.loading}>Loading portfolio…</div>;
  if (sumError) return <div style={styles.error}>{sumError.message}</div>;

  const pnlPos = summary?.total_unrealized_pnl >= 0;

  return (
    <div style={styles.root}>
      {/* Header */}
      <div style={styles.pageHeader}>
        <div>
          <div style={styles.portfolioId}>Portfolio</div>
        </div>
        <button style={styles.addTxBtn} onClick={openModal}>
          + Add Transaction
        </button>
      </div>

      {/* KPI bar */}
      {summary && (
        <div style={styles.kpiBar}>
          <KpiCard label="Total Value" value={fmtUSD(summary.total_market_value)} />
          <KpiCard label="Equity" value={fmtUSD(summary.total_equity_value)} />
          <KpiCard label="Cash" value={fmtUSD(summary.cash_balance)} />
          <KpiCard label="Cost Basis" value={fmtUSD(summary.total_cost_basis)} />
          <KpiCard
            label="Unrealized P&L"
            value={fmtUSD(summary.total_unrealized_pnl)}
            positive={pnlPos}
          />
          <KpiCard
            label="P&L %"
            value={fmtPct(summary.total_unrealized_pnl_pct)}
            positive={pnlPos}
          />
          <KpiCard label="Positions" value={summary.holdings_count} />
          {performance && (
            <>
              <KpiCard
                label="Sharpe"
                value={performance.sharpe_ratio?.toFixed(2) ?? "—"}
                positive={performance.sharpe_ratio > 0 ? true : false}
              />
              <KpiCard
                label="Max DD"
                value={fmtPct(performance.max_drawdown_pct)}
                positive={false}
              />
            </>
          )}
        </div>
      )}

      {/* Tabs */}
      <div style={styles.tabs}>
        {TABS.map((t) => (
          <button
            key={t}
            style={{
              ...styles.tab,
              ...(activeTab === t.toLowerCase() ? styles.tabActive : {}),
            }}
            onClick={() => setTab(t.toLowerCase())}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div style={styles.content}>
        {activeTab === "holdings" && (
          <HoldingsTable holdings={summary?.holdings ?? []} />
        )}

        {activeTab === "performance" && (
          <div>
            {performance && (
              <div style={styles.perfMetrics}>
                {[
                  ["1D", performance.return_1d_pct],
                  ["1W", performance.return_1w_pct],
                  ["1M", performance.return_1m_pct],
                  ["YTD", performance.return_ytd_pct],
                  ["Total", performance.return_total_pct],
                  ["Ann.", performance.return_annualized_pct],
                  ["Vol.", performance.volatility_pct],
                ].map(([label, val]) => (
                  <div key={label} style={styles.perfKpi}>
                    <div style={styles.perfKpiLabel}>{label}</div>
                    <div
                      style={{
                        ...styles.perfKpiValue,
                        color: val >= 0 ? "#4ade80" : "#f87171",
                      }}
                    >
                      {fmtPct(val)}
                    </div>
                  </div>
                ))}
              </div>
            )}
            <PerformanceChart
              navSeries={performance?.nav_series ?? []}
              benchmark={performance?.benchmark ?? "SPY"}
              height={360}
            />
          </div>
        )}

        {activeTab === "allocation" && (
          <AllocationChart
            bySector={allocation?.by_sector ?? []}
            byTicker={allocation?.by_ticker ?? []}
          />
        )}

        {activeTab === "transactions" && (
          <div style={{ overflowX: "auto" }}>
            <table style={txStyles.table}>
              <thead>
                <tr>
                  {["Date", "Type", "Ticker", "Qty", "Price", "Fees", "Notes", ""].map((h) => (
                    <th key={h} style={txStyles.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {transactions.length === 0 ? (
                  <tr>
                    <td colSpan={8} style={txStyles.empty}>No transactions yet</td>
                  </tr>
                ) : (
                  transactions.map((tx) => (
                    <tr key={tx.id} style={txStyles.tr}>
                      <td style={txStyles.td}>{tx.transaction_date}</td>
                      <td style={{ ...txStyles.td, color: tx.transaction_type === "BUY" ? "#4ade80" : tx.transaction_type === "SELL" ? "#f87171" : "#93c5fd", fontWeight: 600 }}>
                        {tx.transaction_type}
                      </td>
                      <td style={{ ...txStyles.td, color: "#93c5fd", fontWeight: 600 }}>{tx.ticker ?? "—"}</td>
                      <td style={{ ...txStyles.td, textAlign: "right" }}>{tx.quantity}</td>
                      <td style={{ ...txStyles.td, textAlign: "right" }}>{fmtUSD(tx.price)}</td>
                      <td style={{ ...txStyles.td, textAlign: "right" }}>{fmtUSD(tx.fees)}</td>
                      <td style={txStyles.td}>{tx.notes ?? "—"}</td>
                      <td style={txStyles.td}>
                        <button
                          style={txStyles.deleteBtn}
                          onClick={() => deleteTx.mutate(tx.id)}
                          title="Delete transaction"
                        >
                          ✕
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {modalOpen && <TransactionModal />}
    </div>
  );
}

const styles = {
  root: { padding: "28px 32px" },
  loading: { padding: "48px 32px", color: "#64748b", fontSize: 14 },
  error: { padding: "48px 32px", color: "#f87171", fontSize: 14 },
  pageHeader: {
    display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24,
  },
  portfolioId: { fontSize: 22, fontWeight: 700, color: "#e2e8f0" },
  addTxBtn: {
    background: "#2563eb", border: "none", borderRadius: 8,
    color: "#fff", fontSize: 13, fontWeight: 600,
    padding: "9px 18px", cursor: "pointer",
  },
  kpiBar: {
    display: "flex", flexWrap: "wrap", gap: 12, marginBottom: 28,
  },
  tabs: { display: "flex", gap: 2, borderBottom: "1px solid #1e2230", marginBottom: 24 },
  tab: {
    background: "none", border: "none", borderBottom: "2px solid transparent",
    color: "#64748b", cursor: "pointer", fontSize: 13, fontWeight: 500,
    padding: "10px 16px", marginBottom: -1, transition: "color 0.12s",
  },
  tabActive: { color: "#e2e8f0", borderBottomColor: "#3b82f6" },
  content: {},
  perfMetrics: {
    display: "flex", flexWrap: "wrap", gap: 12, marginBottom: 20,
  },
  perfKpi: {
    background: "#0d0f14", border: "1px solid #1e2230", borderRadius: 8,
    padding: "10px 18px", minWidth: 80, textAlign: "center",
  },
  perfKpiLabel: { fontSize: 10, fontWeight: 600, color: "#475569", letterSpacing: "0.06em" },
  perfKpiValue: { fontSize: 15, fontWeight: 700, marginTop: 4 },
};

const kpi = {
  card: {
    background: "#0d0f14", border: "1px solid #1e2230", borderRadius: 8,
    padding: "12px 18px", minWidth: 100,
  },
  label: { fontSize: 10, fontWeight: 600, color: "#475569", letterSpacing: "0.06em", marginBottom: 6 },
  value: { fontSize: 16, fontWeight: 700 },
};

const txStyles = {
  table: { width: "100%", borderCollapse: "collapse", fontSize: 13 },
  th: {
    padding: "10px 14px", color: "#475569", fontWeight: 600, fontSize: 11,
    letterSpacing: "0.06em", borderBottom: "1px solid #1e2230",
    background: "#0d0f14", textAlign: "left",
  },
  tr: { borderBottom: "1px solid #111623" },
  td: { padding: "10px 14px", color: "#cbd5e1" },
  empty: { padding: "24px 14px", color: "#475569", textAlign: "center" },
  deleteBtn: {
    background: "none", border: "none", color: "#475569",
    cursor: "pointer", fontSize: 13, padding: "2px 6px",
  },
};
