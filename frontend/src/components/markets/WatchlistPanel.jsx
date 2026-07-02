import { useState } from "react";
import {
  useAddWatchlistItem,
  useCreateWatchlist,
  useDeleteWatchlist,
  useWatchlists,
} from "../../hooks/useMarket";
import useMarketStore from "../../store/useMarketStore";
import QuoteCard from "./QuoteCard";

export default function WatchlistPanel() {
  const { data: watchlists = [], isLoading } = useWatchlists();
  const activeId = useMarketStore((s) => s.activeWatchlistId);
  const setActive = useMarketStore((s) => s.setActiveWatchlistId);
  const createWl = useCreateWatchlist();
  const deleteWl = useDeleteWatchlist();
  const [newWlName, setNewWlName] = useState("");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [ticker, setTicker] = useState("");
  const [addError, setAddError] = useState("");

  // Auto-select first watchlist
  const currentWl =
    watchlists.find((w) => w.id === activeId) || watchlists[0] || null;
  const currentId = currentWl?.id ?? null;

  const addItem = useAddWatchlistItem(currentId);

  const handleCreateWl = async (e) => {
    e.preventDefault();
    if (!newWlName.trim()) return;
    const wl = await createWl.mutateAsync({ name: newWlName.trim() });
    setNewWlName("");
    setShowCreateForm(false);
    setActive(wl.id);
  };

  const handleAddTicker = async (e) => {
    e.preventDefault();
    if (!ticker.trim() || !currentId) return;
    setAddError("");
    try {
      await addItem.mutateAsync({ ticker: ticker.trim().toUpperCase() });
      setTicker("");
    } catch (err) {
      setAddError(err.message);
    }
  };

  return (
    <div style={styles.root}>
      {/* Watchlist tabs */}
      <div style={styles.header}>
        <div style={styles.tabs}>
          {watchlists.map((wl) => (
            <button
              key={wl.id}
              style={{
                ...styles.tab,
                ...(wl.id === (currentId) ? styles.tabActive : {}),
              }}
              onClick={() => setActive(wl.id)}
            >
              {wl.name}
              <span
                style={styles.tabDelete}
                title="Delete watchlist"
                onClick={(e) => {
                  e.stopPropagation();
                  deleteWl.mutate(wl.id);
                  if (wl.id === currentId) setActive(null);
                }}
              >
                ×
              </span>
            </button>
          ))}
          <button style={styles.newBtn} onClick={() => setShowCreateForm((v) => !v)}>
            + New list
          </button>
        </div>

        {showCreateForm && (
          <form onSubmit={handleCreateWl} style={styles.createForm}>
            <input
              autoFocus
              style={styles.input}
              placeholder="Watchlist name"
              value={newWlName}
              onChange={(e) => setNewWlName(e.target.value)}
            />
            <button style={styles.createBtn} type="submit">
              Create
            </button>
          </form>
        )}
      </div>

      {/* Add ticker row */}
      {currentId && (
        <form onSubmit={handleAddTicker} style={styles.addRow}>
          <input
            style={styles.tickerInput}
            placeholder="Add ticker (e.g. AAPL)"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
          />
          <button style={styles.addBtn} type="submit" disabled={addItem.isPending}>
            {addItem.isPending ? "…" : "Add"}
          </button>
          {addError && <span style={styles.addError}>{addError}</span>}
        </form>
      )}

      {/* Quote cards grid */}
      {isLoading ? (
        <div style={styles.empty}>Loading…</div>
      ) : !currentWl ? (
        <div style={styles.empty}>Create a watchlist to start tracking tickers.</div>
      ) : currentWl.items.length === 0 ? (
        <div style={styles.empty}>No tickers yet — add one above.</div>
      ) : (
        <div style={styles.grid}>
          {currentWl.items.map((item) => (
            <QuoteCard key={item.id} item={item} watchlistId={currentId} />
          ))}
        </div>
      )}
    </div>
  );
}

const styles = {
  root: {},
  header: { marginBottom: 16 },
  tabs: { display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center", marginBottom: 10 },
  tab: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    background: "#0d0f14",
    border: "1px solid #1e2230",
    borderRadius: 20,
    color: "#64748b",
    cursor: "pointer",
    fontSize: 12,
    fontWeight: 500,
    padding: "5px 12px",
  },
  tabActive: { borderColor: "#3b82f6", color: "#93c5fd" },
  tabDelete: {
    fontSize: 14,
    color: "#334155",
    marginLeft: 2,
    lineHeight: 1,
    cursor: "pointer",
  },
  newBtn: {
    background: "none",
    border: "1px dashed #1e2230",
    borderRadius: 20,
    color: "#475569",
    cursor: "pointer",
    fontSize: 12,
    padding: "5px 12px",
  },
  createForm: { display: "flex", gap: 8, alignItems: "center" },
  input: {
    background: "#111623",
    border: "1px solid #1e2230",
    borderRadius: 6,
    color: "#e2e8f0",
    fontSize: 13,
    padding: "6px 10px",
    outline: "none",
    width: 200,
  },
  createBtn: {
    background: "#2563eb",
    border: "none",
    borderRadius: 6,
    color: "#fff",
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 600,
    padding: "6px 14px",
  },
  addRow: { display: "flex", alignItems: "center", gap: 10, marginBottom: 20 },
  tickerInput: {
    background: "#111623",
    border: "1px solid #1e2230",
    borderRadius: 6,
    color: "#e2e8f0",
    fontSize: 13,
    padding: "8px 12px",
    outline: "none",
    width: 180,
    letterSpacing: "0.05em",
  },
  addBtn: {
    background: "#2563eb",
    border: "none",
    borderRadius: 6,
    color: "#fff",
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 600,
    padding: "8px 16px",
  },
  addError: { color: "#f87171", fontSize: 12 },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
    gap: 16,
  },
  empty: { color: "#475569", fontSize: 13, padding: "24px 0" },
};
