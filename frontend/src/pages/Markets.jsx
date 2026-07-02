import { useState } from "react";
import { useOHLCV, useNews } from "../hooks/useMarket";
import useMarketStore from "../store/useMarketStore";
import WatchlistPanel from "../components/markets/WatchlistPanel";
import NewsFeed from "../components/markets/NewsFeed";
import EconomicCalendar from "../components/markets/EconomicCalendar";
import PerformanceChart from "../components/portfolio/PerformanceChart";

const BOTTOM_TABS = ["Chart", "News", "Calendar"];

function OHLCVChart({ ticker }) {
  const [interval, setInterval] = useState("1d");
  const [period, setPeriod] = useState("6mo");
  const { data, isLoading } = useOHLCV(ticker, { interval, period });

  // Convert OHLCV bars to NavPoint-compatible format for PerformanceChart
  const navSeries =
    data?.data?.map((b) => ({
      date: b.time,
      nav: b.close,
      benchmark_nav: null,
    })) ?? [];

  return (
    <div>
      <div style={styles.chartControls}>
        <div style={styles.controlGroup}>
          {["1d", "1wk", "1mo"].map((i) => (
            <button
              key={i}
              style={{ ...styles.ctrlBtn, ...(interval === i ? styles.ctrlActive : {}) }}
              onClick={() => setInterval(i)}
            >
              {i}
            </button>
          ))}
        </div>
        <div style={styles.controlGroup}>
          {["1mo", "3mo", "6mo", "1y", "2y", "ytd"].map((p) => (
            <button
              key={p}
              style={{ ...styles.ctrlBtn, ...(period === p ? styles.ctrlActive : {}) }}
              onClick={() => setPeriod(p)}
            >
              {p}
            </button>
          ))}
        </div>
      </div>
      {isLoading ? (
        <div style={styles.chartLoading}>Loading chart…</div>
      ) : (
        <PerformanceChart navSeries={navSeries} benchmark="" height={300} />
      )}
    </div>
  );
}

export default function Markets() {
  const focusedTicker = useMarketStore((s) => s.focusedTicker);
  const [activeTab, setActiveTab] = useState("Chart");

  return (
    <div style={styles.root}>
      <div style={styles.pageHeader}>
        <h1 style={styles.h1}>Markets</h1>
        <p style={styles.sub}>Track tickers, read sentiment, and monitor macro events.</p>
      </div>

      {/* Watchlist section */}
      <section style={styles.section}>
        <div style={styles.sectionTitle}>Watchlists</div>
        <WatchlistPanel />
      </section>

      {/* Detail panel — shown when a ticker is focused from the watchlist */}
      {focusedTicker && (
        <section style={styles.section}>
          <div style={styles.detailHeader}>
            <div style={styles.sectionTitle}>{focusedTicker}</div>
            <div style={styles.bottomTabs}>
              {BOTTOM_TABS.map((t) => (
                <button
                  key={t}
                  style={{
                    ...styles.bTab,
                    ...(activeTab === t ? styles.bTabActive : {}),
                  }}
                  onClick={() => setActiveTab(t)}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <div style={styles.detailContent}>
            {activeTab === "Chart" && <OHLCVChart ticker={focusedTicker} />}
            {activeTab === "News" && <NewsFeed ticker={focusedTicker} />}
            {activeTab === "Calendar" && <EconomicCalendar daysAhead={30} />}
          </div>
        </section>
      )}

      {/* Always-visible calendar when nothing is focused */}
      {!focusedTicker && (
        <section style={styles.section}>
          <div style={styles.sectionTitle}>Economic Calendar · Next 30 Days</div>
          <EconomicCalendar daysAhead={30} />
        </section>
      )}
    </div>
  );
}

const styles = {
  root: { padding: "28px 32px" },
  pageHeader: { marginBottom: 28 },
  h1: { fontSize: 24, fontWeight: 700, color: "#e2e8f0", margin: "0 0 6px" },
  sub: { fontSize: 14, color: "#64748b", margin: 0 },
  section: {
    background: "#080c14",
    border: "1px solid #1e2230",
    borderRadius: 12,
    padding: "20px 22px",
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: 700,
    color: "#475569",
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    marginBottom: 16,
  },
  detailHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 16,
  },
  bottomTabs: { display: "flex", gap: 4 },
  bTab: {
    background: "none",
    border: "1px solid #1e2230",
    borderRadius: 6,
    color: "#64748b",
    cursor: "pointer",
    fontSize: 12,
    fontWeight: 500,
    padding: "5px 12px",
  },
  bTabActive: { background: "#1e2230", color: "#e2e8f0", borderColor: "#2d3748" },
  detailContent: {},
  chartControls: {
    display: "flex",
    gap: 16,
    marginBottom: 12,
    flexWrap: "wrap",
  },
  controlGroup: { display: "flex", gap: 4 },
  ctrlBtn: {
    background: "none",
    border: "1px solid #1e2230",
    borderRadius: 5,
    color: "#475569",
    cursor: "pointer",
    fontSize: 11,
    fontWeight: 600,
    padding: "4px 10px",
    letterSpacing: "0.04em",
  },
  ctrlActive: { background: "#1e2230", color: "#93c5fd", borderColor: "#2d3748" },
  chartLoading: { color: "#475569", fontSize: 13, padding: "40px 0", textAlign: "center" },
};
