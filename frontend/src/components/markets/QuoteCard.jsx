import { useDeleteWatchlistItem } from "../../hooks/useMarket";
import useMarketStore from "../../store/useMarketStore";

function fmt(v, digits = 2) {
  if (v == null) return "—";
  return Number(v).toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function fmtLarge(v) {
  if (v == null) return "—";
  if (v >= 1e12) return "$" + (v / 1e12).toFixed(2) + "T";
  if (v >= 1e9) return "$" + (v / 1e9).toFixed(2) + "B";
  if (v >= 1e6) return "$" + (v / 1e6).toFixed(2) + "M";
  return "$" + fmt(v);
}

export default function QuoteCard({ item, watchlistId }) {
  const focused = useMarketStore((s) => s.focusedTicker);
  const setFocused = useMarketStore((s) => s.setFocusedTicker);
  const deleteMutation = useDeleteWatchlistItem(watchlistId);

  const q = item.quote;
  const isPos = q ? q.change_pct >= 0 : null;
  const isFocused = focused === item.ticker;

  const pctColor = isPos === null ? "#94a3b8" : isPos ? "#4ade80" : "#f87171";

  return (
    <div
      style={{
        ...styles.card,
        ...(isFocused ? styles.cardFocused : {}),
      }}
      onClick={() => setFocused(isFocused ? null : item.ticker)}
    >
      <div style={styles.topRow}>
        <div>
          <div style={styles.ticker}>{item.ticker}</div>
          {q && <div style={styles.name}>{q.name}</div>}
        </div>
        <button
          style={styles.removeBtn}
          title="Remove from watchlist"
          onClick={(e) => {
            e.stopPropagation();
            deleteMutation.mutate(item.id);
          }}
        >
          ✕
        </button>
      </div>

      {q ? (
        <>
          <div style={styles.priceRow}>
            <span style={styles.price}>${fmt(q.price, 2)}</span>
            <span style={{ ...styles.change, color: pctColor }}>
              {isPos ? "+" : ""}{fmt(q.change, 2)} ({isPos ? "+" : ""}{fmt(q.change_pct, 2)}%)
            </span>
          </div>

          <div style={styles.metaGrid}>
            <MetaItem label="Mkt Cap" value={fmtLarge(q.market_cap)} />
            <MetaItem label="P/E" value={q.pe_ratio != null ? fmt(q.pe_ratio, 1) : "—"} />
            <MetaItem label="Vol" value={q.volume != null ? (q.volume / 1e6).toFixed(1) + "M" : "—"} />
            <MetaItem label="52W H" value={q.week_52_high != null ? "$" + fmt(q.week_52_high) : "—"} />
            <MetaItem label="52W L" value={q.week_52_low != null ? "$" + fmt(q.week_52_low) : "—"} />
            <MetaItem label="Sector" value={q.sector ?? "—"} />
          </div>

          {/* 52-week range bar */}
          {q.week_52_high && q.week_52_low && (
            <div style={styles.rangeWrapper}>
              <span style={styles.rangeLabel}>${fmt(q.week_52_low)}</span>
              <div style={styles.rangeBar}>
                <div
                  style={{
                    ...styles.rangeFill,
                    width:
                      ((q.price - q.week_52_low) /
                        (q.week_52_high - q.week_52_low)) *
                        100 +
                      "%",
                  }}
                />
              </div>
              <span style={styles.rangeLabel}>${fmt(q.week_52_high)}</span>
            </div>
          )}
        </>
      ) : (
        <div style={styles.noData}>No quote data</div>
      )}
    </div>
  );
}

function MetaItem({ label, value }) {
  return (
    <div style={styles.metaItem}>
      <div style={styles.metaLabel}>{label}</div>
      <div style={styles.metaValue}>{value}</div>
    </div>
  );
}

const styles = {
  card: {
    background: "#0d0f14",
    border: "1px solid #1e2230",
    borderRadius: 10,
    padding: "14px 16px",
    cursor: "pointer",
    transition: "border-color 0.15s",
    userSelect: "none",
  },
  cardFocused: { borderColor: "#3b82f6" },
  topRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 10,
  },
  ticker: { fontSize: 15, fontWeight: 700, color: "#93c5fd" },
  name: { fontSize: 11, color: "#475569", marginTop: 2, maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" },
  removeBtn: {
    background: "none",
    border: "none",
    color: "#334155",
    cursor: "pointer",
    fontSize: 13,
    padding: "0 2px",
    lineHeight: 1,
    flexShrink: 0,
  },
  priceRow: {
    display: "flex",
    alignItems: "baseline",
    gap: 10,
    marginBottom: 12,
  },
  price: { fontSize: 22, fontWeight: 700, color: "#e2e8f0" },
  change: { fontSize: 13, fontWeight: 600 },
  metaGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr 1fr",
    gap: "6px 0",
    marginBottom: 12,
  },
  metaItem: {},
  metaLabel: { fontSize: 10, color: "#334155", letterSpacing: "0.05em", fontWeight: 600 },
  metaValue: { fontSize: 12, color: "#94a3b8", marginTop: 1 },
  rangeWrapper: {
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  rangeBar: {
    flex: 1,
    height: 4,
    background: "#1e2230",
    borderRadius: 2,
    overflow: "hidden",
  },
  rangeFill: {
    height: "100%",
    background: "#3b82f6",
    borderRadius: 2,
    transition: "width 0.3s",
  },
  rangeLabel: { fontSize: 10, color: "#475569", flexShrink: 0 },
  noData: { color: "#334155", fontSize: 12, paddingTop: 6 },
};
