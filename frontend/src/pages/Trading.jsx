import { useState } from "react";
import { useOrders, useCancelOrder } from "../hooks/useOrders";
import useTradingStore from "../store/useTradingStore";
import OrderTicket from "../components/trading/OrderTicket";
import OrderStatusBadge from "../components/trading/OrderStatusBadge";
import NotificationCenter from "../components/trading/NotificationCenter";

function fmtUSD(v) {
  if (v == null) return "—";
  return "$" + Number(v).toFixed(2);
}

function fmtDate(v) {
  if (!v) return "—";
  return new Date(v).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

const TABS = [
  { key: "order-ticket", label: "Order Ticket" },
  { key: "active-orders", label: "Active Orders" },
  { key: "recent-fills", label: "Recent Fills" },
];

export default function Trading() {
  const tab = useTradingStore((s) => s.tradingTab);
  const setTab = useTradingStore((s) => s.setTradingTab);
  const addNotification = useTradingStore((s) => s.addNotification);

  const activeParams = { status: ["PENDING", "SUBMITTED", "ACCEPTED", "PARTIALLY_FILLED"].join(","), page_size: 50 };
  const fillParams = { status: "FILLED", page_size: 30 };

  const { data: activeData, isLoading: activeLoading } = useOrders(activeParams);
  const { data: fillData, isLoading: fillsLoading } = useOrders(fillParams);
  const activeOrders = activeData?.orders ?? activeData ?? [];
  const recentFills = fillData?.orders ?? fillData ?? [];

  const cancelOrder = useCancelOrder();

  const handleCancel = async (orderId) => {
    try {
      await cancelOrder.mutateAsync({ orderId, reason: "User cancelled from trading hub" });
      addNotification({ type: "info", message: "Order cancelled" });
    } catch (err) {
      addNotification({ type: "error", message: err.response?.data?.detail || err.message });
    }
  };

  return (
    <div style={styles.root}>
      <NotificationCenter />
      <div style={styles.layout}>
        <div style={styles.left}>
          <div style={styles.panelTitle}>New Order</div>
          <OrderTicket onSuccess={() => setTab("active-orders")} />
        </div>

        <div style={styles.right}>
          <div style={styles.tabBar}>
            {TABS.map((t) => (
              <button
                key={t.key}
                style={{ ...styles.tabBtn, ...(tab === t.key ? styles.tabBtnActive : {}) }}
                onClick={() => setTab(t.key)}
              >
                {t.label}
                {t.key === "active-orders" && Array.isArray(activeOrders) && activeOrders.length > 0 && (
                  <span style={styles.badge}>{activeOrders.length}</span>
                )}
              </button>
            ))}
          </div>

          <div style={styles.tabContent}>
            {tab === "order-ticket" && (
              <div style={styles.centeredHint}>
                <div style={styles.hintTitle}>Order Ticket</div>
                <div style={styles.hintText}>Fill in the form on the left to place a new order. Use the tabs above to monitor active orders and recent fills.</div>
              </div>
            )}

            {tab === "active-orders" && (
              <div style={styles.tableWrap}>
                {activeLoading && <div style={styles.loading}>Loading…</div>}
                <table style={styles.table}>
                  <thead>
                    <tr>
                      {["Time", "Ticker", "Side", "Type", "Qty", "Filled", "Limit", "TIF", "Status", "Actions"].map((h) => (
                        <th key={h} style={styles.th}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {Array.isArray(activeOrders) && activeOrders.map((o) => (
                      <tr key={o.id} style={styles.tr}>
                        <td style={styles.tdTime}>{fmtDate(o.created_at)}</td>
                        <td style={{ ...styles.td, fontWeight: 700, color: "#e2e8f0" }}>{o.ticker}</td>
                        <td style={{ ...styles.td, color: o.side?.startsWith("BUY") ? "#4ade80" : "#f87171", fontWeight: 600 }}>{o.side}</td>
                        <td style={styles.td}>{o.order_type}</td>
                        <td style={styles.td}>{Number(o.quantity).toLocaleString()}</td>
                        <td style={{ ...styles.td, color: "#60a5fa" }}>{Number(o.filled_quantity || 0).toLocaleString()}</td>
                        <td style={styles.td}>{fmtUSD(o.limit_price)}</td>
                        <td style={styles.td}>{o.time_in_force}</td>
                        <td style={styles.td}><OrderStatusBadge status={o.status} /></td>
                        <td style={styles.td}>
                          <button style={styles.btnCancel} onClick={() => handleCancel(o.id)}>Cancel</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!activeLoading && Array.isArray(activeOrders) && activeOrders.length === 0 && (
                  <div style={styles.empty}>No active orders</div>
                )}
              </div>
            )}

            {tab === "recent-fills" && (
              <div style={styles.tableWrap}>
                {fillsLoading && <div style={styles.loading}>Loading…</div>}
                <table style={styles.table}>
                  <thead>
                    <tr>
                      {["Time", "Ticker", "Side", "Type", "Qty", "Avg Fill", "Status"].map((h) => (
                        <th key={h} style={styles.th}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {Array.isArray(recentFills) && recentFills.map((o) => (
                      <tr key={o.id} style={styles.tr}>
                        <td style={styles.tdTime}>{fmtDate(o.updated_at || o.created_at)}</td>
                        <td style={{ ...styles.td, fontWeight: 700, color: "#e2e8f0" }}>{o.ticker}</td>
                        <td style={{ ...styles.td, color: o.side?.startsWith("BUY") ? "#4ade80" : "#f87171", fontWeight: 600 }}>{o.side}</td>
                        <td style={styles.td}>{o.order_type}</td>
                        <td style={styles.td}>{Number(o.quantity).toLocaleString()}</td>
                        <td style={{ ...styles.td, color: "#4ade80", fontWeight: 600 }}>{fmtUSD(o.average_fill_price)}</td>
                        <td style={styles.td}><OrderStatusBadge status={o.status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!fillsLoading && Array.isArray(recentFills) && recentFills.length === 0 && (
                  <div style={styles.empty}>No recent fills</div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

const styles = {
  root: { padding: "28px 32px", minHeight: "100vh" },
  layout: { display: "grid", gridTemplateColumns: "320px 1fr", gap: 24, alignItems: "start" },
  left: {
    background: "#111318",
    border: "1px solid #1e2230",
    borderRadius: 10,
    padding: "18px 18px",
    position: "sticky",
    top: 24,
  },
  panelTitle: { fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", color: "#475569", marginBottom: 14 },
  right: { minWidth: 0 },
  tabBar: { display: "flex", gap: 0, borderBottom: "1px solid #1e2230", marginBottom: 0 },
  tabBtn: {
    background: "none", border: "none", borderBottom: "2px solid transparent",
    color: "#64748b", fontSize: 13, fontWeight: 600, padding: "10px 18px",
    cursor: "pointer", marginBottom: -1, display: "flex", alignItems: "center", gap: 6,
  },
  tabBtnActive: { color: "#e2e8f0", borderBottomColor: "#2563eb" },
  badge: {
    background: "#1d4ed8", color: "#fff", fontSize: 10, fontWeight: 700,
    padding: "1px 6px", borderRadius: 10, minWidth: 18, textAlign: "center",
  },
  tabContent: { background: "#111318", border: "1px solid #1e2230", borderTopLeftRadius: 0, borderTopRightRadius: 0, borderRadius: 8 },
  centeredHint: { padding: "60px 32px", textAlign: "center" },
  hintTitle: { fontSize: 16, fontWeight: 600, color: "#475569", marginBottom: 8 },
  hintText: { fontSize: 13, color: "#374151", maxWidth: 420, margin: "0 auto" },
  tableWrap: { overflowX: "auto" },
  loading: { color: "#475569", fontSize: 13, padding: "24px 16px" },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 12 },
  th: { padding: "10px 14px", textAlign: "left", fontSize: 10, fontWeight: 600, letterSpacing: "0.06em", color: "#475569", borderBottom: "1px solid #1e2230", whiteSpace: "nowrap" },
  tr: { borderBottom: "1px solid #0d0f14" },
  td: { padding: "9px 14px", color: "#94a3b8", whiteSpace: "nowrap", fontVariantNumeric: "tabular-nums" },
  tdTime: { padding: "9px 14px", color: "#64748b", fontSize: 11, whiteSpace: "nowrap" },
  btnCancel: { background: "none", border: "1px solid #374151", borderRadius: 4, color: "#6b7280", fontSize: 11, fontWeight: 600, padding: "3px 10px", cursor: "pointer" },
  empty: { padding: "40px 0", textAlign: "center", color: "#475569", fontSize: 13 },
};
