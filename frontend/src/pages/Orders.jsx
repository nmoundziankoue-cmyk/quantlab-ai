import { useState } from "react";
import { useOrders, useCancelOrder, useSubmitOrder } from "../hooks/useOrders";
import OrderStatusBadge from "../components/trading/OrderStatusBadge";
import useTradingStore from "../store/useTradingStore";

const STATUS_OPTIONS = ["", "PENDING", "SUBMITTED", "ACCEPTED", "PARTIALLY_FILLED", "FILLED", "CANCELLED", "REJECTED", "EXPIRED"];
const SIDE_OPTIONS = ["", "BUY", "SELL", "SELL_SHORT", "BUY_TO_COVER"];

function fmtUSD(v) {
  if (v == null) return "—";
  return "$" + Number(v).toFixed(2);
}

function fmtDate(v) {
  if (!v) return "—";
  return new Date(v).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function fmtQty(v) {
  if (v == null) return "—";
  return Number(v).toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 4 });
}

export default function Orders() {
  const filters = useTradingStore((s) => s.orderFilters);
  const setFilter = useTradingStore((s) => s.setOrderFilter);
  const addNotification = useTradingStore((s) => s.addNotification);

  const [ticker, setTicker] = useState(filters.ticker || "");
  const [status, setStatus] = useState(filters.status || "");
  const [side, setSide] = useState("");

  const params = { ticker: ticker || undefined, status: status || undefined, side: side || undefined, page_size: 100 };
  const { data, isLoading, error } = useOrders(params);
  const orders = data?.orders ?? data ?? [];

  const cancelOrder = useCancelOrder();
  const submitOrder = useSubmitOrder();

  const handleCancel = async (orderId) => {
    if (!window.confirm("Cancel this order?")) return;
    try {
      await cancelOrder.mutateAsync({ orderId, reason: "User cancelled" });
      addNotification({ type: "info", message: "Order cancelled" });
    } catch (err) {
      addNotification({ type: "error", message: err.response?.data?.detail || err.message });
    }
  };

  const handleSubmit = async (orderId) => {
    try {
      await submitOrder.mutateAsync(orderId);
      addNotification({ type: "success", message: "Order submitted to market" });
    } catch (err) {
      addNotification({ type: "error", message: err.response?.data?.detail || err.message });
    }
  };

  return (
    <div style={styles.root}>
      <div style={styles.headerRow}>
        <div>
          <h1 style={styles.h1}>Orders</h1>
          <p style={styles.sub}>All orders — live updates every 5 s</p>
        </div>
      </div>

      <div style={styles.filterBar}>
        <input
          style={styles.filterInput}
          placeholder="Ticker…"
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
        />
        <select style={styles.filterSelect} value={status} onChange={(e) => setStatus(e.target.value)}>
          {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s || "All Statuses"}</option>)}
        </select>
        <select style={styles.filterSelect} value={side} onChange={(e) => setSide(e.target.value)}>
          {SIDE_OPTIONS.map((s) => <option key={s} value={s}>{s || "All Sides"}</option>)}
        </select>
        <span style={styles.count}>{isLoading ? "Loading…" : `${Array.isArray(orders) ? orders.length : 0} orders`}</span>
      </div>

      {error && <div style={styles.errorBox}>Failed to load orders: {error.message}</div>}

      <div style={styles.tableWrap}>
        <table style={styles.table}>
          <thead>
            <tr>
              {["Time", "Ticker", "Side", "Type", "Qty", "Filled", "Limit", "Stop", "TIF", "Status", "Avg Fill", "Actions"].map((h) => (
                <th key={h} style={styles.th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.isArray(orders) && orders.map((o) => (
              <tr key={o.id} style={styles.tr}>
                <td style={styles.td}>{fmtDate(o.created_at)}</td>
                <td style={{ ...styles.td, fontWeight: 700, color: "#e2e8f0" }}>{o.ticker}</td>
                <td style={{ ...styles.td, color: o.side?.startsWith("BUY") ? "#4ade80" : "#f87171", fontWeight: 600 }}>{o.side}</td>
                <td style={styles.td}>{o.order_type}</td>
                <td style={styles.td}>{fmtQty(o.quantity)}</td>
                <td style={{ ...styles.td, color: o.filled_quantity > 0 ? "#60a5fa" : "#475569" }}>{fmtQty(o.filled_quantity)}</td>
                <td style={styles.td}>{fmtUSD(o.limit_price)}</td>
                <td style={styles.td}>{fmtUSD(o.stop_price)}</td>
                <td style={styles.td}>{o.time_in_force}</td>
                <td style={styles.td}><OrderStatusBadge status={o.status} /></td>
                <td style={{ ...styles.td, color: "#60a5fa" }}>{fmtUSD(o.average_fill_price)}</td>
                <td style={styles.tdActions}>
                  {o.status === "PENDING" && (
                    <button style={styles.btnSubmit} onClick={() => handleSubmit(o.id)}>Submit</button>
                  )}
                  {["PENDING", "SUBMITTED", "ACCEPTED", "PARTIALLY_FILLED"].includes(o.status) && (
                    <button style={styles.btnCancel} onClick={() => handleCancel(o.id)}>Cancel</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!isLoading && Array.isArray(orders) && orders.length === 0 && (
          <div style={styles.empty}>No orders match the current filters</div>
        )}
      </div>
    </div>
  );
}

const styles = {
  root: { padding: "28px 32px", minHeight: "100vh" },
  headerRow: { display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 20 },
  h1: { fontSize: 22, fontWeight: 700, color: "#e2e8f0", margin: "0 0 4px" },
  sub: { fontSize: 13, color: "#475569", margin: 0 },
  filterBar: { display: "flex", gap: 10, alignItems: "center", marginBottom: 16, flexWrap: "wrap" },
  filterInput: {
    background: "#111318", border: "1px solid #1e2230", borderRadius: 6,
    color: "#e2e8f0", fontSize: 13, padding: "7px 12px", outline: "none", width: 120,
  },
  filterSelect: {
    background: "#111318", border: "1px solid #1e2230", borderRadius: 6,
    color: "#e2e8f0", fontSize: 13, padding: "7px 12px", outline: "none", cursor: "pointer",
  },
  count: { fontSize: 12, color: "#475569", marginLeft: "auto" },
  errorBox: { background: "#2a1a1a", border: "1px solid #b91c1c", borderRadius: 6, color: "#f87171", fontSize: 13, padding: "10px 14px", marginBottom: 16 },
  tableWrap: { overflowX: "auto", background: "#111318", border: "1px solid #1e2230", borderRadius: 8 },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 12 },
  th: { padding: "10px 12px", textAlign: "left", fontSize: 10, fontWeight: 600, letterSpacing: "0.06em", color: "#475569", borderBottom: "1px solid #1e2230", whiteSpace: "nowrap" },
  tr: { borderBottom: "1px solid #0d0f14", transition: "background 0.1s" },
  td: { padding: "9px 12px", color: "#94a3b8", whiteSpace: "nowrap", fontVariantNumeric: "tabular-nums" },
  tdActions: { padding: "6px 12px", display: "flex", gap: 6, alignItems: "center" },
  btnSubmit: { background: "#1d4ed8", border: "none", borderRadius: 4, color: "#fff", fontSize: 11, fontWeight: 600, padding: "3px 10px", cursor: "pointer" },
  btnCancel: { background: "none", border: "1px solid #374151", borderRadius: 4, color: "#6b7280", fontSize: 11, fontWeight: 600, padding: "3px 10px", cursor: "pointer" },
  empty: { padding: "40px 0", textAlign: "center", color: "#475569", fontSize: 13 },
};
