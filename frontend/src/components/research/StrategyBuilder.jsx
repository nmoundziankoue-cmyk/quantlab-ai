/**
 * StrategyBuilder
 *
 * A form component that lets users configure a strategy and run a backtest.
 * Shows dynamic parameter fields based on the selected built-in strategy.
 */

import { useState } from "react";
import { useAvailableStrategies, useRunBacktest } from "../../hooks/useResearch";

const TODAY = new Date().toISOString().slice(0, 10);
const THREE_YEARS_AGO = new Date(Date.now() - 3 * 365.25 * 24 * 3600 * 1000).toISOString().slice(0, 10);

export default function StrategyBuilder({ ticker, onResult }) {
  const { data: available = [] } = useAvailableStrategies();
  const runBacktest = useRunBacktest();

  const [strategyName, setStrategyName] = useState("sma_crossover");
  const [startDate, setStartDate] = useState(THREE_YEARS_AGO);
  const [endDate, setEndDate] = useState(TODAY);
  const [capital, setCapital] = useState("100000");
  const [commission, setCommission] = useState("0.001");
  const [slippage, setSlippage] = useState("0.001");
  const [benchmark, setBenchmark] = useState("SPY");
  const [paramValues, setParamValues] = useState({});
  const [error, setError] = useState("");

  const activeStrategy = available.find((s) => s.key === strategyName);

  const handleStrategyChange = (key) => {
    setStrategyName(key);
    setParamValues({}); // reset to defaults
    setError("");
  };

  const handleParamChange = (key, value) => {
    setParamValues((prev) => ({ ...prev, [key]: value }));
  };

  const buildParams = () => {
    if (!activeStrategy) return {};
    const out = {};
    Object.entries(activeStrategy.params).forEach(([key, meta]) => {
      const raw = paramValues[key];
      if (raw !== undefined && raw !== "") {
        out[key] = meta.type === "int" ? parseInt(raw, 10) : parseFloat(raw);
      } else {
        out[key] = meta.default;
      }
    });
    return out;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!ticker) {
      setError("Enter a ticker symbol first.");
      return;
    }
    setError("");

    try {
      const result = await runBacktest.mutateAsync({
        ticker,
        benchmark,
        start_date: startDate,
        end_date: endDate,
        initial_capital: parseFloat(capital),
        commission_pct: parseFloat(commission),
        slippage_pct: parseFloat(slippage),
        position_size_pct: 1.0,
        strategy_name: strategyName,
        strategy_params: buildParams(),
      });
      if (onResult) onResult(result);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Strategy selector */}
      <div style={styles.field}>
        <label style={styles.label}>Strategy</label>
        <select
          style={styles.select}
          value={strategyName}
          onChange={(e) => handleStrategyChange(e.target.value)}
        >
          {available.map((s) => (
            <option key={s.key} value={s.key}>
              {s.display_name}
            </option>
          ))}
        </select>
        {activeStrategy && (
          <div style={styles.desc}>{activeStrategy.description}</div>
        )}
      </div>

      {/* Dynamic strategy parameters */}
      {activeStrategy && Object.entries(activeStrategy.params).length > 0 && (
        <div style={styles.paramGrid}>
          {Object.entries(activeStrategy.params).map(([key, meta]) => (
            <div key={key} style={styles.field}>
              <label style={styles.label}>
                {key.replace(/_/g, " ")}
                <span style={styles.rangeHint}>
                  {meta.min !== undefined && meta.max !== undefined
                    ? ` (${meta.min}–${meta.max})`
                    : ""}
                </span>
              </label>
              <input
                style={styles.input}
                type="number"
                step={meta.type === "float" ? "0.1" : "1"}
                placeholder={`default: ${meta.default}`}
                value={paramValues[key] ?? ""}
                onChange={(e) => handleParamChange(key, e.target.value)}
              />
            </div>
          ))}
        </div>
      )}

      {/* Date range */}
      <div style={styles.row}>
        <div style={styles.field}>
          <label style={styles.label}>Start Date</label>
          <input style={styles.input} type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </div>
        <div style={styles.field}>
          <label style={styles.label}>End Date</label>
          <input style={styles.input} type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        </div>
      </div>

      {/* Capital & costs */}
      <div style={styles.row}>
        <div style={styles.field}>
          <label style={styles.label}>Initial Capital ($)</label>
          <input style={styles.input} type="number" min="1000" step="1000" value={capital} onChange={(e) => setCapital(e.target.value)} />
        </div>
        <div style={styles.field}>
          <label style={styles.label}>Benchmark</label>
          <input style={styles.input} type="text" maxLength={6} value={benchmark} onChange={(e) => setBenchmark(e.target.value.toUpperCase())} />
        </div>
      </div>

      <div style={styles.row}>
        <div style={styles.field}>
          <label style={styles.label}>Commission %</label>
          <input style={styles.input} type="number" step="0.0001" min="0" max="0.05" value={commission} onChange={(e) => setCommission(e.target.value)} />
        </div>
        <div style={styles.field}>
          <label style={styles.label}>Slippage %</label>
          <input style={styles.input} type="number" step="0.0001" min="0" max="0.05" value={slippage} onChange={(e) => setSlippage(e.target.value)} />
        </div>
      </div>

      {error && <div style={styles.error}>{error}</div>}

      <button
        type="submit"
        style={{ ...styles.btn, opacity: runBacktest.isPending ? 0.6 : 1, cursor: runBacktest.isPending ? "not-allowed" : "pointer" }}
        disabled={runBacktest.isPending}
      >
        {runBacktest.isPending ? "Running backtest…" : "Run Backtest"}
      </button>
    </form>
  );
}

const styles = {
  field: { display: "flex", flexDirection: "column", gap: 4, flex: 1, minWidth: 160 },
  label: { fontSize: 10, fontWeight: 600, color: "#475569", letterSpacing: "0.06em", textTransform: "uppercase" },
  rangeHint: { fontWeight: 400, color: "#334155" },
  input: {
    background: "#0d1117",
    border: "1px solid #1e2230",
    borderRadius: 6,
    color: "#e2e8f0",
    fontSize: 13,
    padding: "7px 10px",
    outline: "none",
    width: "100%",
    boxSizing: "border-box",
  },
  select: {
    background: "#0d1117",
    border: "1px solid #1e2230",
    borderRadius: 6,
    color: "#e2e8f0",
    fontSize: 13,
    padding: "7px 10px",
    outline: "none",
    width: "100%",
    boxSizing: "border-box",
  },
  desc: { fontSize: 11, color: "#334155", marginTop: 2 },
  paramGrid: { display: "flex", flexWrap: "wrap", gap: 12, marginBottom: 12 },
  row: { display: "flex", gap: 12, marginBottom: 12 },
  error: { color: "#f87171", fontSize: 12, marginBottom: 10 },
  btn: {
    background: "#2563eb",
    border: "none",
    borderRadius: 8,
    color: "#fff",
    fontSize: 13,
    fontWeight: 700,
    padding: "10px 24px",
    letterSpacing: "0.04em",
    width: "100%",
    marginTop: 4,
  },
};
