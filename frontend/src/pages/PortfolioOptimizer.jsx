import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { portfolioOptimizationApi } from "../api/portfolioOptimizationApi";
import usePortfolioOptimizationStore from "../store/usePortfolioOptimizationStore";

// ---------------------------------------------------------------------------
// Shared styles
// ---------------------------------------------------------------------------
const S = {
  page: {
    padding: 28,
    background: "#0d1117",
    minHeight: "100vh",
    color: "#e6edf3",
    fontFamily: "'Inter', 'SF Mono', monospace",
  },
  card: {
    background: "#161b22",
    border: "1px solid #30363d",
    borderRadius: 8,
    padding: 20,
    marginBottom: 16,
  },
  cardTitle: { fontSize: 13, fontWeight: 700, color: "#8b949e", letterSpacing: "0.06em", marginBottom: 14, textTransform: "uppercase" },
  label: { fontSize: 12, color: "#8b949e", marginBottom: 4, display: "block" },
  input: {
    background: "#0d1117",
    border: "1px solid #30363d",
    borderRadius: 6,
    color: "#e6edf3",
    padding: "9px 12px",
    fontSize: 13,
    width: "100%",
    boxSizing: "border-box",
  },
  select: {
    background: "#0d1117",
    border: "1px solid #30363d",
    borderRadius: 6,
    color: "#e6edf3",
    padding: "9px 12px",
    fontSize: 13,
    width: "100%",
    boxSizing: "border-box",
  },
  btn: {
    background: "#1f6feb",
    border: "none",
    borderRadius: 6,
    color: "#fff",
    padding: "10px 20px",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
  },
  btnGreen: {
    background: "#238636",
    border: "none",
    borderRadius: 6,
    color: "#fff",
    padding: "10px 20px",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
  },
  btnDisabled: { opacity: 0.5, cursor: "not-allowed" },
  tab: {
    padding: "8px 18px",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
    borderRadius: "6px 6px 0 0",
    border: "1px solid transparent",
    background: "transparent",
    color: "#8b949e",
    marginRight: 2,
  },
  tabActive: {
    background: "#161b22",
    border: "1px solid #30363d",
    borderBottom: "1px solid #161b22",
    color: "#e6edf3",
  },
  grid2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 },
  grid3: { display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 },
  metricBox: {
    background: "#0d1117",
    border: "1px solid #21262d",
    borderRadius: 6,
    padding: "12px 14px",
    textAlign: "center",
  },
  metricValue: { fontSize: 22, fontWeight: 700, color: "#58a6ff", lineHeight: 1.2 },
  metricLabel: { fontSize: 11, color: "#8b949e", marginTop: 4, textTransform: "uppercase", letterSpacing: "0.06em" },
  errBox: {
    background: "#2d1317",
    border: "1px solid #f85149",
    borderRadius: 6,
    color: "#f85149",
    padding: "10px 14px",
    fontSize: 13,
    marginBottom: 14,
  },
  pill: {
    display: "inline-block",
    padding: "2px 8px",
    borderRadius: 4,
    fontSize: 11,
    fontWeight: 600,
  },
  tableWrap: { overflowX: "auto" },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 12 },
  th: { padding: "8px 10px", textAlign: "left", color: "#8b949e", borderBottom: "1px solid #21262d", fontWeight: 600, whiteSpace: "nowrap" },
  td: { padding: "7px 10px", borderBottom: "1px solid #21262d", color: "#e6edf3", whiteSpace: "nowrap" },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function fmt(n, decimals = 2) {
  if (n == null || isNaN(n)) return "—";
  return Number(n).toFixed(decimals);
}

function pct(n, decimals = 2) {
  if (n == null || isNaN(n)) return "—";
  return `${Number(n).toFixed(decimals)}%`;
}

function colorForReturn(v) {
  if (v > 0) return "#3fb950";
  if (v < 0) return "#f85149";
  return "#8b949e";
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function MetricCard({ label, value, unit = "", color }) {
  return (
    <div style={S.metricBox}>
      <div style={{ ...S.metricValue, color: color || "#58a6ff" }}>{value}{unit}</div>
      <div style={S.metricLabel}>{label}</div>
    </div>
  );
}

function WeightsBar({ weights }) {
  const entries = Object.entries(weights).sort((a, b) => b[1] - a[1]);
  const colors = ["#58a6ff", "#3fb950", "#d29922", "#f85149", "#a371f7", "#39d353", "#79c0ff", "#ffa657"];
  return (
    <div>
      <div style={{ display: "flex", borderRadius: 4, overflow: "hidden", height: 22, marginBottom: 10 }}>
        {entries.map(([ticker, w], i) => (
          <div
            key={ticker}
            style={{ width: `${w * 100}%`, background: colors[i % colors.length], display: "flex", alignItems: "center", justifyContent: "center" }}
            title={`${ticker}: ${pct(w * 100)}`}
          />
        ))}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 14px" }}>
        {entries.map(([ticker, w], i) => (
          <span key={ticker} style={{ fontSize: 12, color: "#e6edf3" }}>
            <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: 2, background: colors[i % colors.length], marginRight: 4 }} />
            {ticker} {pct(w * 100)}
          </span>
        ))}
      </div>
    </div>
  );
}

function OptimizeTab({ tickers, mu, cov, rfr }) {
  const { method, setMethod, optimization, setOptimization, availableMethods } = usePortfolioOptimizationStore();

  const mut = useMutation({
    mutationFn: () => portfolioOptimizationApi.optimize({ tickers, mu, cov, risk_free_rate: rfr, method }),
    onSuccess: (r) => setOptimization(r.data),
  });

  const res = optimization;

  return (
    <div>
      <div style={{ display: "flex", gap: 10, marginBottom: 20, alignItems: "flex-end" }}>
        <div style={{ flex: 1 }}>
          <label style={S.label}>Optimization Method</label>
          <select style={S.select} value={method} onChange={e => setMethod(e.target.value)}>
            {availableMethods.map(m => (
              <option key={m.key} value={m.key}>{m.label}</option>
            ))}
          </select>
        </div>
        <button
          style={{ ...S.btn, ...(mut.isPending ? S.btnDisabled : {}) }}
          onClick={() => mut.mutate()}
          disabled={mut.isPending}
        >
          {mut.isPending ? "Optimizing…" : "Run Optimization"}
        </button>
      </div>

      {mut.error && <div style={S.errBox}>{mut.error.response?.data?.detail || mut.error.message}</div>}

      {res && (
        <>
          <div style={{ ...S.card, marginBottom: 16 }}>
            <div style={S.cardTitle}>Allocation</div>
            <WeightsBar weights={res.weights} />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 16 }}>
            <MetricCard label="Expected Return" value={pct(res.expected_return * 100)} color={colorForReturn(res.expected_return)} />
            <MetricCard label="Volatility" value={pct(res.expected_volatility * 100)} color="#d29922" />
            <MetricCard label="Sharpe Ratio" value={fmt(res.sharpe_ratio)} color="#58a6ff" />
            <MetricCard label="Effective N" value={fmt(res.effective_n, 1)} color="#a371f7" />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 16 }}>
            <MetricCard label="Diversification Ratio" value={fmt(res.diversification_ratio)} color="#3fb950" />
            <MetricCard label="Concentration (HHI)" value={fmt(res.concentration_score, 4)} color="#d29922" />
            <MetricCard label="Gross Exposure" value={pct(res.gross_exposure * 100)} />
          </div>

          {res.risk_contributions && Object.keys(res.risk_contributions).length > 0 && (
            <div style={S.card}>
              <div style={S.cardTitle}>Risk Contributions</div>
              <div style={S.tableWrap}>
                <table style={S.table}>
                  <thead>
                    <tr>
                      <th style={S.th}>Ticker</th>
                      <th style={S.th}>Weight</th>
                      <th style={S.th}>Risk Contrib %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(res.weights).map(([t, w]) => (
                      <tr key={t}>
                        <td style={S.td}>{t}</td>
                        <td style={S.td}>{pct(w * 100)}</td>
                        <td style={S.td}>{pct((res.risk_contributions[t] || 0) * 100)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {res.warnings?.length > 0 && (
            <div style={{ ...S.errBox, background: "#2d1f00", borderColor: "#d29922", color: "#d29922", marginTop: 8 }}>
              {res.warnings.map((w, i) => <div key={i}>{w}</div>)}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function CompareTab({ tickers, mu, cov, rfr, availableMethods }) {
  const [selected, setSelected] = useState(["equal_weight", "min_variance", "max_sharpe", "risk_parity", "hrp"]);
  const { comparison, setComparison } = usePortfolioOptimizationStore();

  const toggle = (key) => setSelected(s => s.includes(key) ? s.filter(k => k !== key) : [...s, key]);

  const mut = useMutation({
    mutationFn: () => portfolioOptimizationApi.compare({ tickers, mu, cov, risk_free_rate: rfr, methods: selected }),
    onSuccess: (r) => setComparison(r.data),
  });

  return (
    <div>
      <div style={S.card}>
        <div style={S.cardTitle}>Select Methods to Compare</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 14 }}>
          {availableMethods.map(m => (
            <button
              key={m.key}
              onClick={() => toggle(m.key)}
              style={{
                padding: "4px 10px", fontSize: 11, borderRadius: 4, cursor: "pointer", fontWeight: 600,
                background: selected.includes(m.key) ? "#1f6feb" : "#21262d",
                border: `1px solid ${selected.includes(m.key) ? "#58a6ff" : "#30363d"}`,
                color: selected.includes(m.key) ? "#fff" : "#8b949e",
              }}
            >
              {m.label}
            </button>
          ))}
        </div>
        <button
          style={{ ...S.btn, ...(mut.isPending ? S.btnDisabled : {}) }}
          onClick={() => mut.mutate()}
          disabled={mut.isPending || selected.length === 0}
        >
          {mut.isPending ? "Comparing…" : `Compare ${selected.length} Methods`}
        </button>
      </div>

      {mut.error && <div style={S.errBox}>{mut.error.response?.data?.detail || mut.error.message}</div>}

      {comparison && (
        <div style={S.tableWrap}>
          <table style={{ ...S.table, marginTop: 4 }}>
            <thead>
              <tr>
                <th style={S.th}>Method</th>
                <th style={S.th}>Return (ann)</th>
                <th style={S.th}>Volatility (ann)</th>
                <th style={S.th}>Sharpe</th>
                <th style={S.th}>Div. Ratio</th>
                <th style={S.th}>Eff. N</th>
                <th style={S.th}>Converged</th>
              </tr>
            </thead>
            <tbody>
              {comparison.map((r) => (
                <tr key={r.method}>
                  <td style={{ ...S.td, fontWeight: 700 }}>{r.method}</td>
                  <td style={{ ...S.td, color: colorForReturn(r.expected_return) }}>{pct(r.expected_return * 100)}</td>
                  <td style={S.td}>{pct(r.expected_volatility * 100)}</td>
                  <td style={{ ...S.td, color: "#58a6ff" }}>{fmt(r.sharpe_ratio)}</td>
                  <td style={S.td}>{fmt(r.diversification_ratio)}</td>
                  <td style={S.td}>{fmt(r.effective_n, 1)}</td>
                  <td style={S.td}>
                    <span style={{ ...S.pill, background: r.converged ? "#1a3a25" : "#2d1317", color: r.converged ? "#3fb950" : "#f85149" }}>
                      {r.converged ? "YES" : "NO"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function FrontierTab({ tickers, mu, cov, rfr }) {
  const { nFrontierPoints, setNFrontierPoints, frontier, setFrontier } = usePortfolioOptimizationStore();

  const mut = useMutation({
    mutationFn: () => portfolioOptimizationApi.frontier({ tickers, mu, cov, risk_free_rate: rfr, n_points: nFrontierPoints }),
    onSuccess: (r) => setFrontier(r.data),
  });

  return (
    <div>
      <div style={{ display: "flex", gap: 10, marginBottom: 20, alignItems: "flex-end" }}>
        <div>
          <label style={S.label}>Number of Points</label>
          <select style={{ ...S.select, width: 140 }} value={nFrontierPoints} onChange={e => setNFrontierPoints(+e.target.value)}>
            {[25, 50, 100, 250].map(n => <option key={n} value={n}>{n} points</option>)}
          </select>
        </div>
        <button
          style={{ ...S.btn, ...(mut.isPending ? S.btnDisabled : {}) }}
          onClick={() => mut.mutate()}
          disabled={mut.isPending}
        >
          {mut.isPending ? "Computing…" : "Compute Frontier"}
        </button>
      </div>

      {mut.error && <div style={S.errBox}>{mut.error.response?.data?.detail || mut.error.message}</div>}

      {frontier && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 16 }}>
            <MetricCard label="Min Variance Return" value={pct(frontier.min_variance_point?.expected_return * 100)} color="#d29922" />
            <MetricCard label="Max Sharpe Return" value={pct(frontier.max_sharpe_point?.expected_return * 100)} color="#3fb950" />
            <MetricCard label="Max Sharpe Ratio" value={fmt(frontier.max_sharpe_point?.sharpe_ratio)} color="#58a6ff" />
          </div>

          <div style={S.card}>
            <div style={S.cardTitle}>Efficient Frontier — Risk/Return Tradeoff</div>
            <FrontierPlot points={frontier.points} />
          </div>

          {frontier.equal_weight_point && (
            <div style={S.card}>
              <div style={S.cardTitle}>Equal Weight Reference</div>
              <div style={S.grid3}>
                <MetricCard label="Return" value={pct(frontier.equal_weight_point.expected_return * 100)} />
                <MetricCard label="Volatility" value={pct(frontier.equal_weight_point.expected_volatility * 100)} />
                <MetricCard label="Sharpe" value={fmt(frontier.equal_weight_point.sharpe_ratio)} />
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function FrontierPlot({ points }) {
  if (!points?.length) return null;
  const W = 600, H = 280, PAD = 48;
  const vols = points.map(p => p.expected_volatility * 100);
  const rets = points.map(p => p.expected_return * 100);
  const minV = Math.min(...vols), maxV = Math.max(...vols);
  const minR = Math.min(...rets), maxR = Math.max(...rets);
  const rangeV = maxV - minV || 1, rangeR = maxR - minR || 1;
  const x = v => PAD + ((v - minV) / rangeV) * (W - PAD * 2);
  const y = r => H - PAD - ((r - minR) / rangeR) * (H - PAD * 2);

  const pathD = points
    .map((p, i) => `${i === 0 ? "M" : "L"}${x(p.expected_volatility * 100)},${y(p.expected_return * 100)}`)
    .join(" ");

  // Find max Sharpe point
  const maxSharpeIdx = points.reduce((best, p, i) => p.sharpe_ratio > points[best].sharpe_ratio ? i : best, 0);

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: "block" }}>
      {/* Axes */}
      <line x1={PAD} y1={H - PAD} x2={W - PAD + 8} y2={H - PAD} stroke="#30363d" strokeWidth={1} />
      <line x1={PAD} y1={PAD - 8} x2={PAD} y2={H - PAD} stroke="#30363d" strokeWidth={1} />
      {/* Axis labels */}
      <text x={W / 2} y={H - 4} fill="#8b949e" fontSize={10} textAnchor="middle">Volatility (%)</text>
      <text x={10} y={H / 2} fill="#8b949e" fontSize={10} textAnchor="middle" transform={`rotate(-90,10,${H / 2})`}>Return (%)</text>
      {/* Frontier curve */}
      <path d={pathD} fill="none" stroke="#1f6feb" strokeWidth={2} />
      {/* Dots */}
      {points.map((p, i) => (
        <circle
          key={i}
          cx={x(p.expected_volatility * 100)}
          cy={y(p.expected_return * 100)}
          r={i === maxSharpeIdx ? 5 : 2.5}
          fill={i === maxSharpeIdx ? "#3fb950" : "#58a6ff"}
          opacity={0.8}
        />
      ))}
      {/* Max Sharpe label */}
      <text
        x={x(points[maxSharpeIdx].expected_volatility * 100) + 7}
        y={y(points[maxSharpeIdx].expected_return * 100) - 4}
        fill="#3fb950"
        fontSize={9}
        fontWeight="bold"
      >
        Max Sharpe
      </text>
    </svg>
  );
}

function StressTab({ tickers, weights }) {
  const { stressResults, setStressResults } = usePortfolioOptimizationStore();

  const wMap = weights
    ? Object.fromEntries(tickers.map((t, i) => [t, weights[i]]))
    : Object.fromEntries(tickers.map((t) => [t, 1 / tickers.length]));

  const mut = useMutation({
    mutationFn: () => portfolioOptimizationApi.stress({ tickers, weights: wMap }),
    onSuccess: (r) => setStressResults(r.data.scenarios),
  });

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <button
          style={{ ...S.btnGreen, ...(mut.isPending ? S.btnDisabled : {}) }}
          onClick={() => mut.mutate()}
          disabled={mut.isPending}
        >
          {mut.isPending ? "Running…" : "Run All 10 Stress Scenarios"}
        </button>
      </div>

      {mut.error && <div style={S.errBox}>{mut.error.response?.data?.detail || mut.error.message}</div>}

      {stressResults && (
        <div style={S.tableWrap}>
          <table style={S.table}>
            <thead>
              <tr>
                <th style={S.th}>Scenario</th>
                <th style={S.th}>Period</th>
                <th style={S.th}>Portfolio Impact</th>
                <th style={S.th}>Severity</th>
              </tr>
            </thead>
            <tbody>
              {stressResults.map((s) => (
                <tr key={s.scenario_key}>
                  <td style={{ ...S.td, fontWeight: 700 }}>{s.scenario_name}</td>
                  <td style={{ ...S.td, color: "#8b949e" }}>{s.historical_period || "—"}</td>
                  <td style={{ ...S.td, color: s.portfolio_impact_pct < -20 ? "#f85149" : s.portfolio_impact_pct < -10 ? "#d29922" : "#3fb950" }}>
                    {pct(s.portfolio_impact_pct)}
                  </td>
                  <td style={S.td}>
                    <span style={{
                      ...S.pill,
                      background: s.portfolio_impact_pct < -25 ? "#2d1317" : s.portfolio_impact_pct < -15 ? "#2d1f00" : "#1a3a25",
                      color: s.portfolio_impact_pct < -25 ? "#f85149" : s.portfolio_impact_pct < -15 ? "#d29922" : "#3fb950",
                    }}>
                      {s.portfolio_impact_pct < -25 ? "SEVERE" : s.portfolio_impact_pct < -15 ? "HIGH" : s.portfolio_impact_pct < -5 ? "MODERATE" : "LOW"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function MonteCarloTab({ tickers, mu, cov }) {
  const { mcSimulations, setMcSimulations, mcDays, setMcDays, mcModel, setMcModel, monteCarloResult, setMonteCarloResult } = usePortfolioOptimizationStore();
  const n = tickers.length;
  const weights = Array(n).fill(1 / n);

  const mut = useMutation({
    mutationFn: () => portfolioOptimizationApi.monteCarlo({
      weights,
      mu,
      cov,
      n_simulations: mcSimulations,
      simulation_days: mcDays,
      model: mcModel,
    }),
    onSuccess: (r) => setMonteCarloResult(r.data),
  });

  const res = monteCarloResult;

  return (
    <div>
      <div style={{ display: "flex", gap: 12, marginBottom: 20, alignItems: "flex-end", flexWrap: "wrap" }}>
        <div>
          <label style={S.label}>Simulations</label>
          <select style={{ ...S.select, width: 130 }} value={mcSimulations} onChange={e => setMcSimulations(+e.target.value)}>
            {[500, 1000, 2000, 5000].map(n => <option key={n} value={n}>{n.toLocaleString()}</option>)}
          </select>
        </div>
        <div>
          <label style={S.label}>Horizon (days)</label>
          <select style={{ ...S.select, width: 130 }} value={mcDays} onChange={e => setMcDays(+e.target.value)}>
            {[63, 126, 252, 504].map(n => <option key={n} value={n}>{n === 63 ? "3 months" : n === 126 ? "6 months" : n === 252 ? "1 year" : "2 years"}</option>)}
          </select>
        </div>
        <div>
          <label style={S.label}>Model</label>
          <select style={{ ...S.select, width: 160 }} value={mcModel} onChange={e => setMcModel(e.target.value)}>
            <option value="gbm">GBM (Geometric Brownian)</option>
            <option value="student_t">Student-t (Fat Tails)</option>
            <option value="regime_switching">Regime Switching</option>
          </select>
        </div>
        <button
          style={{ ...S.btn, ...(mut.isPending ? S.btnDisabled : {}) }}
          onClick={() => mut.mutate()}
          disabled={mut.isPending}
        >
          {mut.isPending ? "Simulating…" : "Run Monte Carlo"}
        </button>
      </div>

      {mut.error && <div style={S.errBox}>{mut.error.response?.data?.detail || mut.error.message}</div>}

      {res && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 16 }}>
            <MetricCard label="Expected Terminal" value={`$${Math.round(res.expected_terminal).toLocaleString()}`} color="#58a6ff" />
            <MetricCard label="Median Terminal" value={`$${Math.round(res.median_terminal).toLocaleString()}`} color="#3fb950" />
            <MetricCard label="Prob. of Loss" value={pct(res.probability_of_loss * 100)} color={res.probability_of_loss > 0.3 ? "#f85149" : "#d29922"} />
            <MetricCard label="VaR 95%" value={`$${Math.round(res.var_95).toLocaleString()}`} color="#f85149" />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 16 }}>
            <MetricCard label="CVaR 95%" value={`$${Math.round(res.cvar_95).toLocaleString()}`} color="#f85149" />
            <MetricCard label="Median Max Drawdown" value={pct(res.median_max_drawdown_pct)} color="#d29922" />
            <MetricCard label="P95 Max Drawdown" value={pct(res.p95_max_drawdown_pct)} color="#f85149" />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12, marginBottom: 16 }}>
            <MetricCard label="Best Case (P95)" value={`$${Math.round(res.best_case).toLocaleString()}`} color="#3fb950" />
            <MetricCard label="Worst Case (P5)" value={`$${Math.round(res.worst_case).toLocaleString()}`} color="#f85149" />
          </div>

          {res.percentile_paths && (
            <div style={S.card}>
              <div style={S.cardTitle}>Simulation Fan Chart — Equal Weight Portfolio</div>
              <MCFanChart paths={res.percentile_paths} />
            </div>
          )}

          {res.warnings?.length > 0 && (
            <div style={{ ...S.errBox, background: "#2d1f00", borderColor: "#d29922", color: "#d29922" }}>
              {res.warnings.map((w, i) => <div key={i}>{w}</div>)}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function MCFanChart({ paths }) {
  const W = 600, H = 260, PAD = 44;
  const keys = ["p5", "p25", "p50", "p75", "p95"];
  const allVals = keys.flatMap(k => paths[k] || []);
  const minV = Math.min(...allVals), maxV = Math.max(...allVals);
  const len = paths.p50?.length || 1;
  const rangeV = maxV - minV || 1;
  const x = (i) => PAD + (i / (len - 1)) * (W - PAD * 2);
  const y = (v) => H - PAD - ((v - minV) / rangeV) * (H - PAD * 2);
  const pathLine = (key) => (paths[key] || []).map((v, i) => `${i === 0 ? "M" : "L"}${x(i)},${y(v)}`).join(" ");
  const areaFill = (kLow, kHigh) => {
    const lo = paths[kLow] || [];
    const hi = paths[kHigh] || [];
    const forward = hi.map((v, i) => `${i === 0 ? "M" : "L"}${x(i)},${y(v)}`).join(" ");
    const backward = lo.slice().reverse().map((v, i) => `L${x(lo.length - 1 - i)},${y(v)}`).join(" ");
    return `${forward} ${backward} Z`;
  };

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: "block" }}>
      <line x1={PAD} y1={H - PAD} x2={W - PAD + 6} y2={H - PAD} stroke="#30363d" strokeWidth={1} />
      <line x1={PAD} y1={PAD - 6} x2={PAD} y2={H - PAD} stroke="#30363d" strokeWidth={1} />
      <text x={W / 2} y={H - 4} fill="#8b949e" fontSize={10} textAnchor="middle">Days</text>
      <text x={10} y={H / 2} fill="#8b949e" fontSize={10} textAnchor="middle" transform={`rotate(-90,10,${H / 2})`}>Portfolio Value ($)</text>
      <path d={areaFill("p5", "p95")} fill="#1f6feb" opacity={0.08} />
      <path d={areaFill("p25", "p75")} fill="#1f6feb" opacity={0.14} />
      <path d={pathLine("p5")} fill="none" stroke="#f85149" strokeWidth={1} strokeDasharray="3,3" />
      <path d={pathLine("p25")} fill="none" stroke="#d29922" strokeWidth={1} />
      <path d={pathLine("p50")} fill="none" stroke="#3fb950" strokeWidth={2} />
      <path d={pathLine("p75")} fill="none" stroke="#58a6ff" strokeWidth={1} />
      <path d={pathLine("p95")} fill="none" stroke="#a371f7" strokeWidth={1} strokeDasharray="3,3" />
      {["P5 (Bear)", "P25", "P50 (Median)", "P75", "P95 (Bull)"].map((label, i) => (
        <g key={i}>
          <rect x={PAD + 4 + i * 90} y={PAD - 6} width={8} height={8} rx={2}
            fill={["#f85149","#d29922","#3fb950","#58a6ff","#a371f7"][i]} />
          <text x={PAD + 14 + i * 90} y={PAD + 1} fill="#8b949e" fontSize={9}>{label}</text>
        </g>
      ))}
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
export default function PortfolioOptimizer() {
  const {
    tickersRaw, setTickersRaw,
    riskFreeRate, setRiskFreeRate,
    activeTab, setActiveTab,
    availableMethods, setAvailableMethods,
    setError, clearError, error,
    optimization,
  } = usePortfolioOptimizationStore();

  const [inputError, setInputError] = useState(null);
  const [parsed, setParsed] = useState(null);   // { tickers, mu, cov }

  // Load available methods once
  useQuery({
    queryKey: ["po-methods"],
    queryFn: () => portfolioOptimizationApi.getMethods().then(r => r.data),
    onSuccess: (d) => setAvailableMethods(d.methods),
    staleTime: Infinity,
  });

  // Parse tickers input into synthetic mu/cov (users provide tickers; we
  // generate synthetic equal-volatility inputs as a demo scaffold; in
  // production this would call a data-fetch endpoint)
  const buildInputs = () => {
    setInputError(null);
    const tickers = tickersRaw
      .split(/[\s,]+/)
      .map(t => t.trim().toUpperCase())
      .filter(Boolean);
    if (tickers.length < 2) {
      setInputError("Enter at least 2 tickers separated by commas.");
      return;
    }
    if (tickers.length > 20) {
      setInputError("Maximum 20 tickers supported.");
      return;
    }
    const n = tickers.length;
    // Synthetic daily inputs — equal expected returns / diagonal cov as demo
    const mu = Array(n).fill(0.0004);
    const sigma = Array(n).fill(0.015);
    const cov = Array.from({ length: n }, (_, i) =>
      Array.from({ length: n }, (_, j) =>
        i === j ? sigma[i] ** 2 : sigma[i] * sigma[j] * 0.3
      )
    );
    setParsed({ tickers, mu, cov });
  };

  const TABS = [
    { key: "optimize", label: "Optimize" },
    { key: "compare", label: "Compare Methods" },
    { key: "frontier", label: "Efficient Frontier" },
    { key: "stress", label: "Stress Testing" },
    { key: "montecarlo", label: "Monte Carlo" },
  ];

  return (
    <div style={S.page}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: "#e6edf3" }}>Portfolio Optimizer</h1>
        <p style={{ color: "#8b949e", margin: "4px 0 0", fontSize: 13 }}>
          Institutional portfolio optimization — 14 methods · Efficient frontier · Stress testing · Monte Carlo
        </p>
      </div>

      {/* Input panel */}
      <div style={S.card}>
        <div style={S.cardTitle}>Universe Setup</div>
        <div style={{ display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" }}>
          <div style={{ flex: 2, minWidth: 260 }}>
            <label style={S.label}>Tickers (comma separated)</label>
            <input
              style={S.input}
              value={tickersRaw}
              onChange={e => setTickersRaw(e.target.value)}
              placeholder="AAPL, MSFT, GOOGL, AMZN, NVDA"
            />
          </div>
          <div style={{ width: 140 }}>
            <label style={S.label}>Risk-Free Rate</label>
            <input
              style={S.input}
              type="number"
              step="0.01"
              min="0"
              max="0.20"
              value={riskFreeRate}
              onChange={e => setRiskFreeRate(+e.target.value)}
            />
          </div>
          <button style={S.btnGreen} onClick={buildInputs}>
            Load Universe
          </button>
        </div>
        {inputError && <div style={{ ...S.errBox, marginTop: 10, marginBottom: 0 }}>{inputError}</div>}
        {parsed && (
          <div style={{ marginTop: 10, fontSize: 12, color: "#8b949e" }}>
            Universe: {parsed.tickers.join(", ")} &mdash; {parsed.tickers.length} assets loaded
          </div>
        )}
      </div>

      {!parsed && (
        <div style={{ ...S.card, textAlign: "center", padding: 60, color: "#8b949e" }}>
          Enter tickers above and click <strong>Load Universe</strong> to begin optimization.
        </div>
      )}

      {parsed && (
        <>
          {/* Tab bar */}
          <div style={{ display: "flex", borderBottom: "1px solid #30363d", marginBottom: 0 }}>
            {TABS.map(t => (
              <button
                key={t.key}
                style={{ ...S.tab, ...(activeTab === t.key ? S.tabActive : {}) }}
                onClick={() => setActiveTab(t.key)}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div style={{ ...S.card, borderTopLeftRadius: 0, marginTop: 0, borderTop: "none" }}>
            {activeTab === "optimize" && (
              <OptimizeTab tickers={parsed.tickers} mu={parsed.mu} cov={parsed.cov} rfr={riskFreeRate} />
            )}
            {activeTab === "compare" && (
              <CompareTab tickers={parsed.tickers} mu={parsed.mu} cov={parsed.cov} rfr={riskFreeRate} availableMethods={availableMethods} />
            )}
            {activeTab === "frontier" && (
              <FrontierTab tickers={parsed.tickers} mu={parsed.mu} cov={parsed.cov} rfr={riskFreeRate} />
            )}
            {activeTab === "stress" && (
              <StressTab
                tickers={parsed.tickers}
                weights={optimization?.weights ? parsed.tickers.map(t => optimization.weights[t] || 1 / parsed.tickers.length) : null}
              />
            )}
            {activeTab === "montecarlo" && (
              <MonteCarloTab tickers={parsed.tickers} mu={parsed.mu} cov={parsed.cov} />
            )}
          </div>
        </>
      )}
    </div>
  );
}
