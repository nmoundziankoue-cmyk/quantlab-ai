import { useState } from "react";
import {
  usePaperAccounts,
  usePaperAccount,
  usePaperPositions,
  usePaperTrades,
  useCreatePaperAccount,
  useRefreshPaperPrices,
} from "../hooks/usePaperTrading";
import useTradingStore from "../store/useTradingStore";
import OrderTicket from "../components/trading/OrderTicket";
import PositionsTable from "../components/trading/PositionsTable";
import PnLCard from "../components/trading/PnLCard";
import BuyingPowerCard from "../components/trading/BuyingPowerCard";

function fmtUSD(v) {
  if (v == null) return "—";
  return "$" + Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtDate(v) {
  if (!v) return "—";
  return new Date(v).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function CreateAccountForm({ onClose }) {
  const [name, setName] = useState("");
  const [cash, setCash] = useState("100000");
  const [commType, setCommType] = useState("PER_SHARE");
  const [commRate, setCommRate] = useState("0.005");
  const [minComm, setMinComm] = useState("1.00");
  const [slippageBps, setSlippageBps] = useState("10");
  const [error, setError] = useState(null);
  const addNotification = useTradingStore((s) => s.addNotification);
  const create = useCreatePaperAccount();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      await create.mutateAsync({
        name: name.trim(),
        initial_cash: Number(cash),
        commission_type: commType,
        commission_rate: Number(commRate),
        min_commission: Number(minComm),
        slippage_bps: Number(slippageBps),
      });
      addNotification({ type: "success", message: `Paper account "${name}" created` });
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  return (
    <div style={styles.modal}>
      <div style={styles.modalBox}>
        <div style={styles.modalTitle}>New Paper Account</div>
        <form onSubmit={handleSubmit} style={styles.createForm}>
          <div style={styles.formRow}>
            <div style={styles.formField}>
              <label style={styles.fl}>Account Name</label>
              <input style={styles.inp} value={name} onChange={(e) => setName(e.target.value)} placeholder="My Paper Account" required />
            </div>
            <div style={styles.formField}>
              <label style={styles.fl}>Initial Capital ($)</label>
              <input style={styles.inp} type="number" value={cash} onChange={(e) => setCash(e.target.value)} placeholder="100000" required />
            </div>
          </div>
          <div style={styles.formRow}>
            <div style={styles.formField}>
              <label style={styles.fl}>Commission Type</label>
              <select style={styles.sel} value={commType} onChange={(e) => setCommType(e.target.value)}>
                <option value="PER_SHARE">Per Share ($0.005/sh)</option>
                <option value="FLAT">Flat</option>
                <option value="PERCENT">Percent</option>
              </select>
            </div>
            <div style={styles.formField}>
              <label style={styles.fl}>Commission Rate</label>
              <input style={styles.inp} type="number" step="0.0001" value={commRate} onChange={(e) => setCommRate(e.target.value)} />
            </div>
          </div>
          <div style={styles.formRow}>
            <div style={styles.formField}>
              <label style={styles.fl}>Min Commission ($)</label>
              <input style={styles.inp} type="number" step="0.01" value={minComm} onChange={(e) => setMinComm(e.target.value)} />
            </div>
            <div style={styles.formField}>
              <label style={styles.fl}>Slippage (bps)</label>
              <input style={styles.inp} type="number" value={slippageBps} onChange={(e) => setSlippageBps(e.target.value)} />
            </div>
          </div>
          {error && <div style={styles.createError}>{error}</div>}
          <div style={styles.modalActions}>
            <button type="button" style={styles.btnCancel} onClick={onClose}>Cancel</button>
            <button type="submit" style={styles.btnCreate} disabled={create.isPending}>
              {create.isPending ? "Creating…" : "Create Account"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function PaperTrading() {
  const activePaperAccountId = useTradingStore((s) => s.activePaperAccountId);
  const setActivePaperAccountId = useTradingStore((s) => s.setActivePaperAccountId);
  const addNotification = useTradingStore((s) => s.addNotification);
  const [showCreate, setShowCreate] = useState(false);
  const [tab, setTab] = useState("positions");

  const { data: accounts = [], isLoading: accountsLoading } = usePaperAccounts();
  const { data: account } = usePaperAccount(activePaperAccountId);
  const { data: positions = [], isLoading: posLoading } = usePaperPositions(activePaperAccountId);
  const { data: tradesData } = usePaperTrades(activePaperAccountId, { page_size: 100 });
  const trades = tradesData?.trades ?? tradesData ?? [];

  const refresh = useRefreshPaperPrices();

  const handleRefresh = async () => {
    if (!activePaperAccountId) return;
    try {
      await refresh.mutateAsync(activePaperAccountId);
      addNotification({ type: "success", message: "Prices refreshed" });
    } catch (err) {
      addNotification({ type: "error", message: err.message });
    }
  };

  return (
    <div style={styles.root}>
      {showCreate && <CreateAccountForm onClose={() => setShowCreate(false)} />}

      <div style={styles.headerRow}>
        <div>
          <h1 style={styles.h1}>Paper Trading</h1>
          <p style={styles.sub}>Virtual broker — risk-free strategy testing</p>
        </div>
        <button style={styles.btnNew} onClick={() => setShowCreate(true)}>+ New Account</button>
      </div>

      <div style={styles.layout}>
        <div style={styles.left}>
          <div style={styles.sectionLabel}>ACCOUNTS</div>
          {accountsLoading && <div style={styles.empty}>Loading…</div>}
          {accounts.map((acc) => (
            <button
              key={acc.id}
              style={{ ...styles.accountBtn, ...(acc.id === activePaperAccountId ? styles.accountBtnActive : {}) }}
              onClick={() => setActivePaperAccountId(acc.id)}
            >
              <div style={styles.accName}>{acc.name}</div>
              <div style={styles.accEquity}>{fmtUSD(acc.total_equity)}</div>
            </button>
          ))}
          {accounts.length === 0 && !accountsLoading && (
            <div style={styles.empty}>No paper accounts yet</div>
          )}

          {activePaperAccountId && (
            <div style={{ marginTop: 20 }}>
              <OrderTicket paperAccountId={activePaperAccountId} />
            </div>
          )}
        </div>

        <div style={styles.right}>
          {!activePaperAccountId ? (
            <div style={styles.noAccount}>Select a paper account from the left panel</div>
          ) : (
            <>
              <div style={styles.summaryRow}>
                <div style={{ flex: 1 }}><PnLCard account={account} /></div>
                <div style={{ flex: 1 }}><BuyingPowerCard account={account} /></div>
              </div>

              <div style={styles.tabBar}>
                {["positions", "trades"].map((t) => (
                  <button
                    key={t}
                    style={{ ...styles.tab, ...(tab === t ? styles.tabActive : {}) }}
                    onClick={() => setTab(t)}
                  >
                    {t === "positions" ? "Open Positions" : "Trade History"}
                  </button>
                ))}
                <button style={styles.refreshBtn} onClick={handleRefresh} disabled={refresh.isPending}>
                  {refresh.isPending ? "Refreshing…" : "Refresh Prices"}
                </button>
              </div>

              <div style={styles.tableSection}>
                {tab === "positions" && (
                  <PositionsTable positions={positions} isLoading={posLoading} />
                )}
                {tab === "trades" && (
                  <div style={{ overflowX: "auto" }}>
                    <table style={styles.table}>
                      <thead>
                        <tr>
                          {["Time", "Ticker", "Side", "Qty", "Fill Price", "Commission", "Slippage", "Net Cost", "Realized P&L"].map((h) => (
                            <th key={h} style={styles.th}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {Array.isArray(trades) && trades.map((t) => (
                          <tr key={t.id} style={styles.tr}>
                            <td style={styles.tdTime}>{fmtDate(t.executed_at)}</td>
                            <td style={{ ...styles.td, fontWeight: 700, color: "#e2e8f0" }}>{t.ticker}</td>
                            <td style={{ ...styles.td, color: t.side?.startsWith("BUY") ? "#4ade80" : "#f87171", fontWeight: 600 }}>{t.side}</td>
                            <td style={styles.td}>{Number(t.quantity).toLocaleString()}</td>
                            <td style={{ ...styles.td, color: "#60a5fa" }}>{fmtUSD(t.fill_price)}</td>
                            <td style={{ ...styles.td, color: "#fbbf24" }}>{fmtUSD(t.commission)}</td>
                            <td style={{ ...styles.td, color: "#f87171" }}>{fmtUSD(t.slippage_cost)}</td>
                            <td style={styles.td}>{fmtUSD(t.net_cost)}</td>
                            <td style={{ ...styles.td, color: t.realized_pnl >= 0 ? "#4ade80" : "#f87171", fontWeight: 600 }}>
                              {fmtUSD(t.realized_pnl)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {Array.isArray(trades) && trades.length === 0 && (
                      <div style={styles.empty}>No trades yet</div>
                    )}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

const styles = {
  root: { padding: "28px 32px", minHeight: "100vh" },
  headerRow: { display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 24 },
  h1: { fontSize: 22, fontWeight: 700, color: "#e2e8f0", margin: "0 0 4px" },
  sub: { fontSize: 13, color: "#475569", margin: 0 },
  btnNew: { background: "#1d4ed8", border: "none", borderRadius: 6, color: "#fff", fontSize: 13, fontWeight: 600, padding: "9px 16px", cursor: "pointer" },
  layout: { display: "grid", gridTemplateColumns: "260px 1fr", gap: 20 },
  left: { display: "flex", flexDirection: "column", gap: 8 },
  right: { minWidth: 0 },
  sectionLabel: { fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", color: "#475569", marginBottom: 4 },
  accountBtn: {
    background: "#111318", border: "1px solid #1e2230", borderRadius: 6,
    color: "#94a3b8", cursor: "pointer", padding: "10px 14px", textAlign: "left",
    display: "flex", justifyContent: "space-between", alignItems: "center",
  },
  accountBtnActive: { border: "1px solid #2563eb", color: "#e2e8f0", background: "#1a2340" },
  accName: { fontSize: 13, fontWeight: 600 },
  accEquity: { fontSize: 12, color: "#60a5fa", fontVariantNumeric: "tabular-nums" },
  empty: { color: "#475569", fontSize: 12, padding: "8px 0" },
  noAccount: { color: "#475569", fontSize: 14, textAlign: "center", padding: "80px 0" },
  summaryRow: { display: "flex", gap: 16, marginBottom: 16 },
  tabBar: { display: "flex", gap: 0, borderBottom: "1px solid #1e2230", marginBottom: 0, alignItems: "center" },
  tab: {
    background: "none", border: "none", borderBottom: "2px solid transparent",
    color: "#64748b", fontSize: 13, fontWeight: 600, padding: "10px 18px",
    cursor: "pointer", marginBottom: -1,
  },
  tabActive: { color: "#e2e8f0", borderBottomColor: "#2563eb" },
  refreshBtn: {
    marginLeft: "auto", background: "#1e2230", border: "1px solid #2d3748",
    borderRadius: 6, color: "#94a3b8", fontSize: 12, fontWeight: 600,
    padding: "6px 12px", cursor: "pointer",
  },
  tableSection: { background: "#111318", border: "1px solid #1e2230", borderRadius: 8, borderTopLeftRadius: 0, borderTopRightRadius: 0, padding: "16px" },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 12 },
  th: { padding: "8px 12px", textAlign: "right", fontSize: 10, fontWeight: 600, letterSpacing: "0.06em", color: "#475569", borderBottom: "1px solid #1e2230", whiteSpace: "nowrap" },
  tr: { borderBottom: "1px solid #0d0f14" },
  td: { padding: "8px 12px", color: "#94a3b8", textAlign: "right", whiteSpace: "nowrap", fontVariantNumeric: "tabular-nums" },
  tdTime: { padding: "8px 12px", color: "#64748b", textAlign: "left", fontSize: 11 },
  modal: { position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", zIndex: 999, display: "flex", alignItems: "center", justifyContent: "center" },
  modalBox: { background: "#111318", border: "1px solid #1e2230", borderRadius: 10, padding: "24px 28px", width: 540, maxWidth: "90vw" },
  modalTitle: { fontSize: 16, fontWeight: 700, color: "#e2e8f0", marginBottom: 20 },
  createForm: { display: "flex", flexDirection: "column", gap: 14 },
  formRow: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 },
  formField: { display: "flex", flexDirection: "column", gap: 4 },
  fl: { fontSize: 11, fontWeight: 600, color: "#475569", letterSpacing: "0.04em" },
  inp: { background: "#1a1d24", border: "1px solid #2d3748", borderRadius: 5, color: "#e2e8f0", fontSize: 13, padding: "8px 10px", outline: "none" },
  sel: { background: "#1a1d24", border: "1px solid #2d3748", borderRadius: 5, color: "#e2e8f0", fontSize: 13, padding: "8px 10px", outline: "none", cursor: "pointer" },
  createError: { background: "#2a1a1a", border: "1px solid #b91c1c", borderRadius: 5, color: "#f87171", fontSize: 12, padding: "8px 10px" },
  modalActions: { display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 4 },
  btnCancel: { background: "#1e2230", border: "1px solid #2d3748", borderRadius: 6, color: "#94a3b8", fontSize: 13, fontWeight: 600, padding: "8px 20px", cursor: "pointer" },
  btnCreate: { background: "#1d4ed8", border: "none", borderRadius: 6, color: "#fff", fontSize: 13, fontWeight: 700, padding: "8px 20px", cursor: "pointer" },
};
