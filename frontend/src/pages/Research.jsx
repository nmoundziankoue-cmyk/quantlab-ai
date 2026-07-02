/**
 * Research Page — M3 Quantitative Research Engine
 *
 * Layout:
 *   ┌────────────────────────────────────┐
 *   │  Ticker input + period controls    │
 *   ├──────────────────┬─────────────────┤
 *   │  Indicator chart │  Strategy       │
 *   │  (left panel)    │  Builder        │
 *   │                  │  (right panel)  │
 *   ├──────────────────┴─────────────────┤
 *   │  Backtest result (when available)  │
 *   ├────────────────────────────────────┤
 *   │  Backtest history                  │
 *   └────────────────────────────────────┘
 */

import { useState } from "react";
import { useIndicators, useBacktest } from "../hooks/useResearch";
import useResearchStore from "../store/useResearchStore";
import IndicatorChart from "../components/research/IndicatorChart";
import StrategyBuilder from "../components/research/StrategyBuilder";
import BacktestResults from "../components/research/BacktestResults";
import BacktestHistory from "../components/research/BacktestHistory";

const INDICATOR_OPTIONS = [
  { group: "Trend", items: [
    { key: "sma", label: "SMA 20", spec: { sma: [{ period: 20 }] } },
    { key: "sma50", label: "SMA 50", spec: { sma: [{ period: 50 }] } },
    { key: "ema", label: "EMA 12/26", spec: { ema: [{ period: 12 }, { period: 26 }] } },
    { key: "bbands", label: "Bollinger Bands", spec: { bbands: [{ period: 20, std_dev: 2.0 }] } },
  ]},
  { group: "Momentum", items: [
    { key: "rsi", label: "RSI 14", spec: { rsi: [{ period: 14 }] } },
    { key: "macd", label: "MACD", spec: { macd: [{}] } },
    { key: "stoch", label: "Stochastic", spec: { stoch: [{ k_period: 14, d_period: 3 }] } },
  ]},
  { group: "Volume", items: [
    { key: "obv", label: "OBV", spec: { obv: [{}] } },
  ]},
];

const PERIODS = ["1mo", "3mo", "6mo", "1y", "2y", "5y"];
const INTERVALS = ["1d", "1wk"];

function mergeIndicatorSpecs(enabledKeys) {
  const merged = {};
  INDICATOR_OPTIONS.forEach(({ items }) => {
    items.forEach(({ key, spec }) => {
      if (enabledKeys.has(key)) {
        Object.entries(spec).forEach(([indType, specList]) => {
          if (!merged[indType]) merged[indType] = [];
          // Deduplicate by period
          specList.forEach((s) => {
            const already = merged[indType].some(
              (x) => JSON.stringify(x) === JSON.stringify(s)
            );
            if (!already) merged[indType].push(s);
          });
        });
      }
    });
  });
  return merged;
}

export default function Research() {
  const store = useResearchStore();
  const [enabledIndicators, setEnabledIndicators] = useState(new Set(["sma", "rsi"]));
  const [activeBacktestResult, setActiveBacktestResult] = useState(null);
  const [historySelectedId, setHistorySelectedId] = useState(null);
  const [tickerInput, setTickerInput] = useState("");

  // Fetch indicators only when ticker is set
  const indicatorBody = store.ticker
    ? {
        ticker: store.ticker,
        period: store.period,
        interval: store.interval,
        indicators: mergeIndicatorSpecs(enabledIndicators),
      }
    : null;

  const { data: indicatorData, isLoading: chartLoading, error: chartError } = useIndicators(
    indicatorBody,
    !!store.ticker
  );

  // Load a backtest from history
  const { data: historyBacktest } = useBacktest(historySelectedId);

  const displayedResult = historySelectedId ? historyBacktest : activeBacktestResult;

  const handleTickerSubmit = (e) => {
    e.preventDefault();
    if (tickerInput.trim()) store.setTicker(tickerInput.trim());
  };

  const toggleIndicator = (key) => {
    setEnabledIndicators((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const handleBacktestResult = (result) => {
    setHistorySelectedId(null);
    setActiveBacktestResult(result);
    // Scroll to results
    setTimeout(() => {
      document.getElementById("backtest-anchor")?.scrollIntoView({ behavior: "smooth" });
    }, 100);
  };

  const handleHistorySelect = (id) => {
    setActiveBacktestResult(null);
    setHistorySelectedId(id);
    setTimeout(() => {
      document.getElementById("backtest-anchor")?.scrollIntoView({ behavior: "smooth" });
    }, 100);
  };

  return (
    <div style={styles.root}>
      {/* Page header */}
      <div style={styles.pageHeader}>
        <h1 style={styles.h1}>Research Lab</h1>
        <p style={styles.sub}>
          Technical analysis · Strategy backtesting · Performance analytics
        </p>
      </div>

      {/* Ticker + period controls */}
      <section style={styles.card}>
        <div style={styles.controlBar}>
          <form onSubmit={handleTickerSubmit} style={styles.tickerForm}>
            <input
              style={styles.tickerInput}
              placeholder="Ticker (e.g. AAPL)"
              value={tickerInput}
              onChange={(e) => setTickerInput(e.target.value.toUpperCase())}
            />
            <button type="submit" style={styles.goBtn}>
              Load
            </button>
          </form>

          {/* Period */}
          <div style={styles.controlGroup}>
            {PERIODS.map((p) => (
              <button
                key={p}
                style={{ ...styles.ctrlBtn, ...(store.period === p ? styles.ctrlActive : {}) }}
                onClick={() => store.setPeriod(p)}
              >
                {p}
              </button>
            ))}
          </div>

          {/* Interval */}
          <div style={styles.controlGroup}>
            {INTERVALS.map((iv) => (
              <button
                key={iv}
                style={{ ...styles.ctrlBtn, ...(store.interval === iv ? styles.ctrlActive : {}) }}
                onClick={() => store.setInterval(iv)}
              >
                {iv}
              </button>
            ))}
          </div>
        </div>

        {/* Indicator toggles */}
        <div style={styles.indRow}>
          {INDICATOR_OPTIONS.map(({ group, items }) => (
            <div key={group} style={styles.indGroup}>
              <span style={styles.indGroupLabel}>{group}</span>
              {items.map(({ key, label }) => (
                <button
                  key={key}
                  style={{
                    ...styles.indBtn,
                    ...(enabledIndicators.has(key) ? styles.indBtnOn : {}),
                  }}
                  onClick={() => toggleIndicator(key)}
                >
                  {label}
                </button>
              ))}
            </div>
          ))}
        </div>
      </section>

      {/* Main two-column layout: chart + strategy builder */}
      <div style={styles.twoCol}>
        {/* Chart panel */}
        <section style={{ ...styles.card, flex: 3, minWidth: 0 }}>
          <div style={styles.cardTitle}>
            {store.ticker || "— Select a ticker above —"}
          </div>

          {!store.ticker && (
            <div style={styles.empty}>Enter a ticker to load the chart.</div>
          )}

          {store.ticker && chartLoading && (
            <div style={styles.empty}>Loading chart data…</div>
          )}

          {chartError && (
            <div style={styles.errorBox}>
              {chartError.message}
            </div>
          )}

          {indicatorData && (
            <IndicatorChart
              ohlcv={indicatorData.ohlcv}
              indicators={indicatorData.indicators}
              height={440}
            />
          )}
        </section>

        {/* Strategy builder panel */}
        <section style={{ ...styles.card, flex: 1.5, minWidth: 280, maxWidth: 420 }}>
          <div style={styles.cardTitle}>Strategy Builder</div>
          {!store.ticker && (
            <div style={styles.empty}>Load a ticker first to run a backtest.</div>
          )}
          {store.ticker && (
            <StrategyBuilder ticker={store.ticker} onResult={handleBacktestResult} />
          )}
        </section>
      </div>

      {/* Backtest result panel */}
      <div id="backtest-anchor" />
      {displayedResult && (
        <section style={styles.card}>
          <div style={styles.cardTitle}>Backtest Result</div>
          <BacktestResults result={displayedResult} />
        </section>
      )}

      {/* Backtest history */}
      <section style={styles.card}>
        <div style={styles.cardTitle}>Backtest History</div>
        <BacktestHistory onSelect={handleHistorySelect} />
      </section>
    </div>
  );
}

const styles = {
  root: { padding: "28px 32px" },
  pageHeader: { marginBottom: 24 },
  h1: { fontSize: 24, fontWeight: 700, color: "#e2e8f0", margin: "0 0 6px" },
  sub: { fontSize: 14, color: "#64748b", margin: 0 },
  card: {
    background: "#080c14",
    border: "1px solid #1e2230",
    borderRadius: 12,
    padding: "20px 22px",
    marginBottom: 20,
  },
  cardTitle: {
    fontSize: 12,
    fontWeight: 700,
    color: "#475569",
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    marginBottom: 14,
  },
  controlBar: {
    display: "flex",
    flexWrap: "wrap",
    gap: 12,
    alignItems: "center",
    marginBottom: 14,
  },
  tickerForm: { display: "flex", gap: 6, flex: "0 0 auto" },
  tickerInput: {
    background: "#0d1117",
    border: "1px solid #1e2230",
    borderRadius: 6,
    color: "#e2e8f0",
    fontSize: 13,
    fontWeight: 600,
    padding: "6px 12px",
    outline: "none",
    width: 130,
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  goBtn: {
    background: "#2563eb",
    border: "none",
    borderRadius: 6,
    color: "#fff",
    fontSize: 13,
    fontWeight: 600,
    padding: "6px 16px",
    cursor: "pointer",
  },
  controlGroup: { display: "flex", gap: 4, flexWrap: "wrap" },
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
  indRow: { display: "flex", flexWrap: "wrap", gap: 16 },
  indGroup: { display: "flex", alignItems: "center", gap: 6 },
  indGroupLabel: { fontSize: 9, fontWeight: 700, color: "#334155", letterSpacing: "0.08em", textTransform: "uppercase", marginRight: 2 },
  indBtn: {
    background: "#0d1117",
    border: "1px solid #1e2230",
    borderRadius: 5,
    color: "#475569",
    cursor: "pointer",
    fontSize: 11,
    padding: "3px 9px",
  },
  indBtnOn: { background: "#1e3a5f", color: "#93c5fd", borderColor: "#2563eb" },
  twoCol: { display: "flex", gap: 20, alignItems: "flex-start", flexWrap: "wrap" },
  empty: { color: "#334155", fontSize: 13, padding: "24px 0", textAlign: "center" },
  errorBox: {
    background: "#1c0808",
    border: "1px solid #7f1d1d",
    borderRadius: 6,
    color: "#f87171",
    fontSize: 12,
    padding: "10px 14px",
    marginTop: 6,
  },
};
