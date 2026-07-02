import { useState } from "react";
import useTradingStore from "../../store/useTradingStore";
import { useCreateOrder, usePreviewOrder } from "../../hooks/useOrders";
import { useSubmitPaperOrder } from "../../hooks/usePaperTrading";

const ORDER_TYPES = ["MARKET", "LIMIT", "STOP", "STOP_LIMIT", "TRAILING_STOP"];
const SIDES = ["BUY", "SELL", "SELL_SHORT", "BUY_TO_COVER"];
const TIMES_IN_FORCE = ["DAY", "GTC", "IOC", "FOK"];

function Field({ label, children, error }) {
  return (
    <div style={styles.field}>
      <label style={styles.label}>{label}</label>
      {children}
      {error && <div style={styles.fieldError}>{error}</div>}
    </div>
  );
}

function Input({ ...props }) {
  return <input style={styles.input} {...props} />;
}

function Select({ children, ...props }) {
  return <select style={styles.select} {...props}>{children}</select>;
}

export default function OrderTicket({ paperAccountId, portfolioId, onSuccess }) {
  const ticket = useTradingStore((s) => s.orderTicket);
  const setField = useTradingStore((s) => s.setOrderTicketField);
  const resetTicket = useTradingStore((s) => s.resetOrderTicket);
  const preview = useTradingStore((s) => s.orderPreview);
  const setPreview = useTradingStore((s) => s.setOrderPreview);
  const clearPreview = useTradingStore((s) => s.clearOrderPreview);
  const addNotification = useTradingStore((s) => s.addNotification);

  const [error, setError] = useState(null);

  const createOrder = useCreateOrder();
  const previewMutation = usePreviewOrder();
  const submitPaper = useSubmitPaperOrder();

  const needsLimit = ["LIMIT", "STOP_LIMIT"].includes(ticket.orderType);
  const needsStop = ["STOP", "STOP_LIMIT", "TRAILING_STOP"].includes(ticket.orderType);
  const isTrailing = ticket.orderType === "TRAILING_STOP";

  const buildPayload = () => ({
    ticker: ticket.ticker.trim().toUpperCase(),
    order_type: ticket.orderType,
    side: ticket.side,
    quantity: ticket.quantity ? Number(ticket.quantity) : undefined,
    limit_price: needsLimit && ticket.limitPrice ? Number(ticket.limitPrice) : undefined,
    stop_price: needsStop && !isTrailing && ticket.stopPrice ? Number(ticket.stopPrice) : undefined,
    trail_amount: isTrailing && ticket.stopPrice ? Number(ticket.stopPrice) : undefined,
    trail_type: isTrailing ? "AMOUNT" : undefined,
    time_in_force: ticket.timeInForce,
    strategy_tag: ticket.strategyTag || undefined,
    notes: ticket.notes || undefined,
  });

  const handlePreview = async () => {
    setError(null);
    try {
      const result = await previewMutation.mutateAsync(buildPayload());
      setPreview(result);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const handleSubmit = async () => {
    setError(null);
    const payload = buildPayload();
    try {
      if (paperAccountId) {
        await submitPaper.mutateAsync({ accountId: paperAccountId, data: payload });
        addNotification({ type: "success", title: "Paper Order Submitted", message: `${payload.side} ${payload.quantity} ${payload.ticker} — executed in paper account` });
      } else {
        const order = await createOrder.mutateAsync({ data: payload, options: { portfolioId } });
        addNotification({ type: "success", title: "Order Created", message: `Order ${order.id.slice(0, 8)}… placed` });
      }
      clearPreview();
      resetTicket();
      onSuccess?.();
    } catch (err) {
      const detail = err.response?.data?.detail;
      const msg = Array.isArray(detail) ? detail.map((d) => d.msg).join("; ") : (detail || err.message);
      setError(msg);
      addNotification({ type: "error", title: "Order Failed", message: msg });
    }
  };

  const isPending = createOrder.isPending || submitPaper.isPending || previewMutation.isPending;

  return (
    <div style={styles.root}>
      <div style={styles.header}>Order Ticket {paperAccountId ? "(Paper)" : ""}</div>

      <div style={styles.row2}>
        <Field label="Ticker">
          <Input
            value={ticket.ticker}
            onChange={(e) => { setField("ticker", e.target.value.toUpperCase()); clearPreview(); }}
            placeholder="AAPL"
            style={{ ...styles.input, textTransform: "uppercase" }}
          />
        </Field>
        <Field label="Side">
          <Select value={ticket.side} onChange={(e) => { setField("side", e.target.value); clearPreview(); }}>
            {SIDES.map((s) => <option key={s} value={s}>{s}</option>)}
          </Select>
        </Field>
      </div>

      <div style={styles.row2}>
        <Field label="Order Type">
          <Select value={ticket.orderType} onChange={(e) => { setField("orderType", e.target.value); clearPreview(); }}>
            {ORDER_TYPES.map((t) => <option key={t} value={t}>{t.replace("_", " ")}</option>)}
          </Select>
        </Field>
        <Field label="Time in Force">
          <Select value={ticket.timeInForce} onChange={(e) => { setField("timeInForce", e.target.value); clearPreview(); }}>
            {TIMES_IN_FORCE.map((t) => <option key={t} value={t}>{t}</option>)}
          </Select>
        </Field>
      </div>

      <Field label="Quantity">
        <Input
          type="number"
          min="0"
          step="1"
          value={ticket.quantity}
          onChange={(e) => { setField("quantity", e.target.value); clearPreview(); }}
          placeholder="100"
        />
      </Field>

      {needsLimit && (
        <Field label="Limit Price">
          <Input
            type="number"
            min="0"
            step="0.01"
            value={ticket.limitPrice}
            onChange={(e) => { setField("limitPrice", e.target.value); clearPreview(); }}
            placeholder="0.00"
          />
        </Field>
      )}

      {needsStop && (
        <Field label={isTrailing ? "Trail Amount ($)" : "Stop Price"}>
          <Input
            type="number"
            min="0"
            step="0.01"
            value={ticket.stopPrice}
            onChange={(e) => { setField("stopPrice", e.target.value); clearPreview(); }}
            placeholder="0.00"
          />
        </Field>
      )}

      <div style={styles.row2}>
        <Field label="Strategy Tag">
          <Input
            value={ticket.strategyTag}
            onChange={(e) => setField("strategyTag", e.target.value)}
            placeholder="momentum"
          />
        </Field>
      </div>

      {error && <div style={styles.error}>{error}</div>}

      {preview && (
        <div style={styles.preview}>
          <div style={styles.previewTitle}>Order Preview</div>
          <div style={styles.previewGrid}>
            <span style={styles.pk}>Est. Fill</span><span style={styles.pv}>${Number(preview.estimated_fill_price ?? 0).toFixed(2)}</span>
            <span style={styles.pk}>Est. Cost</span><span style={styles.pv}>${Number(preview.estimated_gross_value ?? 0).toFixed(2)}</span>
            <span style={styles.pk}>Commission</span><span style={styles.pv}>${Number(preview.estimated_commission ?? 0).toFixed(2)}</span>
            <span style={styles.pk}>Slippage</span><span style={styles.pv}>${Number(preview.estimated_slippage ?? 0).toFixed(2)}</span>
            <span style={styles.pk}>Net Cost</span><span style={{ ...styles.pv, color: "#60a5fa", fontWeight: 700 }}>${Number(preview.estimated_net_value ?? 0).toFixed(2)}</span>
          </div>
        </div>
      )}

      <div style={styles.actions}>
        <button
          style={styles.btnSecondary}
          onClick={handlePreview}
          disabled={isPending || !ticket.ticker || !ticket.quantity}
        >
          {previewMutation.isPending ? "Calculating…" : "Preview"}
        </button>
        <button
          style={{ ...styles.btnPrimary, ...(ticket.side.startsWith("SELL") ? styles.btnSell : {}) }}
          onClick={handleSubmit}
          disabled={isPending || !ticket.ticker || !ticket.quantity}
        >
          {isPending ? "Submitting…" : `${ticket.side} ${ticket.quantity || ""} ${ticket.ticker || "…"}`}
        </button>
      </div>
    </div>
  );
}

const styles = {
  root: { display: "flex", flexDirection: "column", gap: 10 },
  header: { fontSize: 13, fontWeight: 700, color: "#e2e8f0", marginBottom: 4 },
  row2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 },
  field: { display: "flex", flexDirection: "column", gap: 4 },
  label: { fontSize: 11, fontWeight: 600, color: "#475569", letterSpacing: "0.04em" },
  fieldError: { fontSize: 11, color: "#f87171" },
  input: {
    background: "#1a1d24",
    border: "1px solid #2d3748",
    borderRadius: 5,
    color: "#e2e8f0",
    fontSize: 13,
    padding: "7px 10px",
    outline: "none",
    width: "100%",
    boxSizing: "border-box",
    fontVariantNumeric: "tabular-nums",
  },
  select: {
    background: "#1a1d24",
    border: "1px solid #2d3748",
    borderRadius: 5,
    color: "#e2e8f0",
    fontSize: 13,
    padding: "7px 10px",
    outline: "none",
    width: "100%",
    boxSizing: "border-box",
    cursor: "pointer",
  },
  error: {
    background: "#2a1a1a",
    border: "1px solid #b91c1c",
    borderRadius: 5,
    color: "#f87171",
    fontSize: 12,
    padding: "8px 10px",
  },
  preview: {
    background: "#0d1117",
    border: "1px solid #1e2230",
    borderRadius: 6,
    padding: "12px 14px",
  },
  previewTitle: { fontSize: 11, fontWeight: 600, color: "#475569", letterSpacing: "0.05em", marginBottom: 8 },
  previewGrid: { display: "grid", gridTemplateColumns: "auto 1fr", gap: "4px 16px", alignItems: "baseline" },
  pk: { fontSize: 12, color: "#64748b" },
  pv: { fontSize: 12, color: "#cbd5e1", textAlign: "right", fontVariantNumeric: "tabular-nums" },
  actions: { display: "flex", gap: 8, marginTop: 4 },
  btnPrimary: {
    flex: 1,
    background: "#1d4ed8",
    border: "none",
    borderRadius: 6,
    color: "#fff",
    fontSize: 13,
    fontWeight: 700,
    padding: "9px 12px",
    cursor: "pointer",
    letterSpacing: "0.02em",
  },
  btnSell: { background: "#b91c1c" },
  btnSecondary: {
    background: "#1e2230",
    border: "1px solid #2d3748",
    borderRadius: 6,
    color: "#94a3b8",
    fontSize: 13,
    fontWeight: 600,
    padding: "9px 16px",
    cursor: "pointer",
  },
};
