import { useEffect, useState } from "react";
import { useAddTransaction } from "../../hooks/usePortfolio";
import usePortfolioStore from "../../store/usePortfolioStore";

const TX_TYPES = ["BUY", "SELL", "DIVIDEND", "DEPOSIT", "WITHDRAWAL"];
const EQUITY_TYPES = new Set(["BUY", "SELL", "DIVIDEND"]);

const INITIAL = {
  transaction_type: "BUY",
  transaction_date: new Date().toISOString().slice(0, 10),
  ticker: "",
  quantity: "",
  price: "",
  fees: "0",
  notes: "",
};

export default function TransactionModal() {
  const portfolioId = usePortfolioStore((s) => s.selectedPortfolioId);
  const close = usePortfolioStore((s) => s.closeTransactionModal);
  const addTx = useAddTransaction(portfolioId);

  const [form, setForm] = useState(INITIAL);
  const [error, setError] = useState("");

  useEffect(() => {
    setForm(INITIAL);
    setError("");
  }, []);

  const needsTicker = EQUITY_TYPES.has(form.transaction_type);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    const payload = {
      transaction_type: form.transaction_type,
      transaction_date: form.transaction_date,
      quantity: parseFloat(form.quantity),
      price: parseFloat(form.price),
      fees: parseFloat(form.fees || 0),
      notes: form.notes || null,
    };
    if (needsTicker) payload.ticker = form.ticker.toUpperCase();

    try {
      await addTx.mutateAsync(payload);
      close();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div style={styles.overlay} onClick={(e) => e.target === e.currentTarget && close()}>
      <div style={styles.modal}>
        <div style={styles.header}>
          <span style={styles.title}>Record Transaction</span>
          <button style={styles.closeBtn} onClick={close}>✕</button>
        </div>

        <form onSubmit={handleSubmit} style={styles.form}>
          <label style={styles.label}>Type</label>
          <select style={styles.select} value={form.transaction_type} onChange={set("transaction_type")}>
            {TX_TYPES.map((t) => <option key={t}>{t}</option>)}
          </select>

          <label style={styles.label}>Date</label>
          <input style={styles.input} type="date" value={form.transaction_date} onChange={set("transaction_date")} required />

          {needsTicker && (
            <>
              <label style={styles.label}>Ticker</label>
              <input
                style={styles.input}
                placeholder="e.g. AAPL"
                value={form.ticker}
                onChange={set("ticker")}
                required={needsTicker}
              />
            </>
          )}

          <div style={styles.row}>
            <div style={styles.col}>
              <label style={styles.label}>{needsTicker ? "Shares" : "Amount ($)"}</label>
              <input
                style={styles.input}
                type="number"
                step="any"
                min="0.0001"
                placeholder="0"
                value={form.quantity}
                onChange={set("quantity")}
                required
              />
            </div>
            <div style={styles.col}>
              <label style={styles.label}>{needsTicker ? "Price ($)" : "Price (use 1)"}</label>
              <input
                style={styles.input}
                type="number"
                step="any"
                min="0.0001"
                placeholder="0.00"
                value={form.price}
                onChange={set("price")}
                required
              />
            </div>
          </div>

          <label style={styles.label}>Fees ($)</label>
          <input
            style={styles.input}
            type="number"
            step="any"
            min="0"
            placeholder="0"
            value={form.fees}
            onChange={set("fees")}
          />

          <label style={styles.label}>Notes (optional)</label>
          <textarea
            style={{ ...styles.input, height: 64, resize: "vertical" }}
            placeholder="Optional notes"
            value={form.notes}
            onChange={set("notes")}
          />

          {error && <div style={styles.error}>{error}</div>}

          <div style={styles.actions}>
            <button type="button" style={styles.cancelBtn} onClick={close}>Cancel</button>
            <button type="submit" style={styles.submitBtn} disabled={addTx.isPending}>
              {addTx.isPending ? "Saving…" : "Save Transaction"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

const styles = {
  overlay: {
    position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)",
    display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
  },
  modal: {
    background: "#0d0f14", border: "1px solid #1e2230", borderRadius: 12,
    width: 460, maxHeight: "90vh", overflow: "auto",
    boxShadow: "0 24px 80px rgba(0,0,0,0.6)",
  },
  header: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    padding: "18px 20px 14px", borderBottom: "1px solid #1e2230",
  },
  title: { fontSize: 15, fontWeight: 600, color: "#e2e8f0" },
  closeBtn: {
    background: "none", border: "none", color: "#475569", cursor: "pointer", fontSize: 16,
  },
  form: { padding: "18px 20px 20px", display: "flex", flexDirection: "column", gap: 4 },
  label: { fontSize: 11, fontWeight: 600, color: "#475569", letterSpacing: "0.06em", marginTop: 10 },
  input: {
    background: "#111623", border: "1px solid #1e2230", borderRadius: 6,
    color: "#e2e8f0", fontSize: 13, padding: "8px 12px", outline: "none",
    width: "100%", boxSizing: "border-box",
  },
  select: {
    background: "#111623", border: "1px solid #1e2230", borderRadius: 6,
    color: "#e2e8f0", fontSize: 13, padding: "8px 12px", outline: "none",
    width: "100%", cursor: "pointer",
  },
  row: { display: "flex", gap: 12 },
  col: { flex: 1 },
  error: { color: "#f87171", fontSize: 12, marginTop: 4 },
  actions: { display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 14 },
  cancelBtn: {
    background: "none", border: "1px solid #1e2230", borderRadius: 6,
    color: "#94a3b8", fontSize: 13, fontWeight: 500, padding: "8px 18px", cursor: "pointer",
  },
  submitBtn: {
    background: "#2563eb", border: "none", borderRadius: 6,
    color: "#fff", fontSize: 13, fontWeight: 600, padding: "8px 20px", cursor: "pointer",
  },
};
