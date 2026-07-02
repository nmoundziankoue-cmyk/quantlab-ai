/**
 * Portfolio Analytics — M4
 *
 * Layout:
 *   Tab bar: Risk | Optimization | Stress | Monte Carlo | Factors | Correlation
 *   Each tab renders its panel with a "Run Analysis" button and result area.
 *   All results are cached in Zustand so switching tabs doesn't re-fetch.
 */
import { useState } from "react";
import { useParams, Navigate } from "react-router-dom";
import usePortfolioStore from "../store/usePortfolioStore";
import useAnalyticsStore from "../store/useAnalyticsStore";

import {
  useRiskMetrics,
  useAllStressTests,
  useRunStressScenario,
  useRunMonteCarlo,
  useFactorExposures,
  useCorrelationMatrix,
  useMST,
  useClusters,
} from "../hooks/useAnalytics";

import VaRPanel from "../components/analytics/VaRPanel";
import RiskMetricsGrid from "../components/analytics/RiskMetricsGrid";
import RiskContributionChart from "../components/analytics/RiskContributionChart";
import StressTestPanel from "../components/analytics/StressTestPanel";
import MonteCarloFanChart from "../components/analytics/MonteCarloFanChart";
import FactorExposureChart from "../components/analytics/FactorExposureChart";
import CorrelationHeatmap from "../components/analytics/CorrelationHeatmap";
import CorrelationNetwork from "../components/analytics/CorrelationNetwork";
import OptimizationPanel from "../components/analytics/OptimizationPanel";

// ── Stress scenario selector ───────────────────────────────────────────────
const SCENARIOS = [
  { key: "all", label: "All Scenarios" },
  { key: "2008_financial_crisis", label: "2008 Crisis" },
  { key: "covid_crash", label: "COVID Crash" },
  { key: "dotcom_crash", label: "Dot-com Crash" },
  { key: "rate_shock_2022", label: "Rate Shock 2022" },
  { key: "inflation_shock_1973", label: "Inflation Shock" },
  { key: "oil_shock_2014", label: "Oil Shock 2014" },
  { key: "russia_ukraine_2022", label: "Russia-Ukraine" },
];

// ── Config constants ───────────────────────────────────────────────────────
const TABS = [
  { key: "risk", label: "Risk Metrics" },
  { key: "optimization", label: "Optimization" },
  { key: "stress", label: "Stress Tests" },
  { key: "montecarlo", label: "Monte Carlo" },
  { key: "factors", label: "Factor Analysis" },
  { key: "correlation", label: "Correlation" },
];

const LOOKBACK_OPTIONS = [
  { value: 63, label: "3 Months" },
  { value: 126, label: "6 Months" },
  { value: 252, label: "1 Year" },
  { value: 504, label: "2 Years" },
  { value: 756, label: "3 Years" },
];

const MC_MODELS = ["gbm", "student_t", "bootstrap"];
const MC_DAYS_OPTIONS = [
  { value: 63, label: "3 Months" },
  { value: 126, label: "6 Months" },
  { value: 252, label: "1 Year" },
  { value: 504, label: "2 Years" },
];
const MC_SIMS_OPTIONS = [
  { value: 1000, label: "1,000" },
  { value: 5000, label: "5,000" },
  { value: 10000, label: "10,000" },
  { value: 25000, label: "25,000" },
];

const CORR_METHODS = ["pearson", "spearman", "kendall"];

export default function PortfolioAnalytics() {
  const { id: routeId } = useParams();
  const selectedId = usePortfolioStore((s) => s.selectedPortfolioId);
  const portfolioId = routeId ?? selectedId;

  const store = useAnalyticsStore();

  const [selectedScenario, setSelectedScenario] = useState("all");

  // ── Mutation hooks ──────────────────────────────────────────────────────
  const runRisk = useRiskMetrics(portfolioId, {
    lookback_days: store.lookbackDays,
    benchmark: store.benchmark,
  });
  const runAllStress = useAllStressTests(portfolioId);
  const runSingleStress = useRunStressScenario(portfolioId);
  const runMC = useRunMonteCarlo(portfolioId);
  const runFactors = useFactorExposures(portfolioId);
  const runCorr = useCorrelationMatrix(portfolioId);
  const runMST = useMST(portfolioId);
  const runClusters = useClusters(portfolioId);

  if (!portfolioId) {
    return (
      <div style={styles.root}>
        <div style={styles.empty}>Select a portfolio from the sidebar to run analytics.</div>
      </div>
    );
  }

  const [riskError, setRiskError] = useState("");
  const [stressError, setStressError] = useState("");
  const [mcError, setMcError] = useState("");
  const [factorError, setFactorError] = useState("");
  const [corrError, setCorrError] = useState("");

  const handleRunRisk = async () => {
    setRiskError("");
    try {
      const result = await runRisk.mutateAsync();
      store.setRiskResult(result);
    } catch (err) { setRiskError(err.message); }
  };

  const handleRunStress = async () => {
    setStressError("");
    try {
      let result;
      if (selectedScenario === "all") {
        result = await runAllStress.mutateAsync();
      } else {
        result = await runSingleStress.mutateAsync(selectedScenario);
      }
      store.setStressResult(result);
    } catch (err) { setStressError(err.message); }
  };

  const handleRunMC = async () => {
    setMcError("");
    try {
      const result = await runMC.mutateAsync({
        model: store.mcModel,
        simulation_days: store.mcDays,
        n_simulations: store.mcSims,
        lookback_days: store.lookbackDays,
      });
      store.setMonteCarloResult(result);
    } catch (err) { setMcError(err.message); }
  };

  const handleRunFactors = async () => {
    setFactorError("");
    try {
      const result = await runFactors.mutateAsync(store.lookbackDays);
      store.setFactorResult(result);
    } catch (err) { setFactorError(err.message); }
  };

  const handleRunCorr = async () => {
    setCorrError("");
    try {
      const [corrResult, mstResult, clusterResult] = await Promise.all([
        runCorr.mutateAsync({ lookbackDays: store.lookbackDays, method: store.corrMethod }),
        runMST.mutateAsync(store.lookbackDays),
        runClusters.mutateAsync({ lookbackDays: store.lookbackDays, nClusters: store.nClusters }),
      ]);
      store.setCorrelationResult({ corr: corrResult, clusters: clusterResult });
      store.setMstResult(mstResult);
    } catch (err) { setCorrError(err.message); }
  };

  const isRunningRisk = runRisk.isPending;
  const isRunningStress = runAllStress.isPending || runSingleStress.isPending;
  const isRunningMC = runMC.isPending;
  const isRunningFactors = runFactors.isPending;
  const isRunningCorr = runCorr.isPending || runMST.isPending || runClusters.isPending;

  return (
    <div style={styles.root}>
      {/* Header */}
      <div style={styles.pageHeader}>
        <h1 style={styles.h1}>Portfolio Analytics</h1>
        <p style={styles.sub}>Risk · Optimization · Stress Testing · Monte Carlo · Factor Analysis · Correlation</p>
      </div>

      {/* Tab bar */}
      <div style={styles.tabBar}>
        {TABS.map((t) => (
          <button
            key={t.key}
            style={{ ...styles.tab, ...(store.activeTab === t.key ? styles.tabActive : {}) }}
            onClick={() => store.setActiveTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Risk Metrics Tab ─────────────────────────────────────────────── */}
      {store.activeTab === "risk" && (
        <div>
          {/* Controls */}
          <div style={styles.card}>
            <div style={styles.controlRow}>
              <div style={styles.field}>
                <label style={styles.label}>Lookback Period</label>
                <select style={styles.select} value={store.lookbackDays} onChange={(e) => store.setLookbackDays(Number(e.target.value))}>
                  {LOOKBACK_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div style={styles.field}>
                <label style={styles.label}>Benchmark</label>
                <input
                  style={styles.input}
                  value={store.benchmark}
                  onChange={(e) => store.setBenchmark(e.target.value.toUpperCase())}
                  maxLength={6}
                  placeholder="SPY"
                />
              </div>
              <button style={styles.runBtn} disabled={isRunningRisk} onClick={handleRunRisk}>
                {isRunningRisk ? "Computing…" : "Run Risk Analysis"}
              </button>
            </div>
            {riskError && <div style={styles.error}>{riskError}</div>}
          </div>

          {store.riskResult && (
            <>
              <div style={styles.twoCol}>
                <section style={{ ...styles.card, flex: 1, minWidth: 300 }}>
                  <VaRPanel metrics={store.riskResult} />
                </section>
                <section style={{ ...styles.card, flex: 2, minWidth: 300 }}>
                  <RiskMetricsGrid metrics={store.riskResult} />
                </section>
              </div>
              {store.riskResult.risk_contributions && (
                <section style={styles.card}>
                  <RiskContributionChart riskContributions={store.riskResult.risk_contributions} />
                </section>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Optimization Tab ─────────────────────────────────────────────── */}
      {store.activeTab === "optimization" && (
        <section style={styles.card}>
          <OptimizationPanel portfolioId={portfolioId} />
        </section>
      )}

      {/* ── Stress Tests Tab ─────────────────────────────────────────────── */}
      {store.activeTab === "stress" && (
        <div>
          <div style={styles.card}>
            <div style={styles.controlRow}>
              <div style={styles.field}>
                <label style={styles.label}>Scenario</label>
                <select style={styles.select} value={selectedScenario} onChange={(e) => setSelectedScenario(e.target.value)}>
                  {SCENARIOS.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
                </select>
              </div>
              <button style={styles.runBtn} disabled={isRunningStress} onClick={handleRunStress}>
                {isRunningStress ? "Running…" : "Run Stress Test"}
              </button>
            </div>
            {stressError && <div style={styles.error}>{stressError}</div>}
          </div>
          {store.stressResult && (
            <section style={styles.card}>
              <StressTestPanel result={store.stressResult} />
            </section>
          )}
        </div>
      )}

      {/* ── Monte Carlo Tab ──────────────────────────────────────────────── */}
      {store.activeTab === "montecarlo" && (
        <div>
          <div style={styles.card}>
            <div style={styles.controlRow}>
              <div style={styles.field}>
                <label style={styles.label}>Model</label>
                <select style={styles.select} value={store.mcModel} onChange={(e) => store.setMcModel(e.target.value)}>
                  {MC_MODELS.map((m) => <option key={m} value={m}>{m.replace("_", "-").toUpperCase()}</option>)}
                </select>
              </div>
              <div style={styles.field}>
                <label style={styles.label}>Horizon</label>
                <select style={styles.select} value={store.mcDays} onChange={(e) => store.setMcDays(Number(e.target.value))}>
                  {MC_DAYS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div style={styles.field}>
                <label style={styles.label}>Simulations</label>
                <select style={styles.select} value={store.mcSims} onChange={(e) => store.setMcSims(Number(e.target.value))}>
                  {MC_SIMS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div style={styles.field}>
                <label style={styles.label}>Lookback</label>
                <select style={styles.select} value={store.lookbackDays} onChange={(e) => store.setLookbackDays(Number(e.target.value))}>
                  {LOOKBACK_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <button style={styles.runBtn} disabled={isRunningMC} onClick={handleRunMC}>
                {isRunningMC ? "Simulating…" : "Run Simulation"}
              </button>
            </div>
            {mcError && <div style={styles.error}>{mcError}</div>}
          </div>
          {store.monteCarloResult && (
            <section style={styles.card}>
              <MonteCarloFanChart result={store.monteCarloResult} />
            </section>
          )}
        </div>
      )}

      {/* ── Factor Analysis Tab ──────────────────────────────────────────── */}
      {store.activeTab === "factors" && (
        <div>
          <div style={styles.card}>
            <div style={styles.controlRow}>
              <div style={styles.field}>
                <label style={styles.label}>Lookback Period</label>
                <select style={styles.select} value={store.lookbackDays} onChange={(e) => store.setLookbackDays(Number(e.target.value))}>
                  {LOOKBACK_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <button style={styles.runBtn} disabled={isRunningFactors} onClick={handleRunFactors}>
                {isRunningFactors ? "Computing…" : "Run Factor Analysis"}
              </button>
            </div>
            {factorError && <div style={styles.error}>{factorError}</div>}
          </div>
          {store.factorResult && (
            <section style={styles.card}>
              <FactorExposureChart result={store.factorResult} />
            </section>
          )}
        </div>
      )}

      {/* ── Correlation Tab ──────────────────────────────────────────────── */}
      {store.activeTab === "correlation" && (
        <div>
          <div style={styles.card}>
            <div style={styles.controlRow}>
              <div style={styles.field}>
                <label style={styles.label}>Lookback</label>
                <select style={styles.select} value={store.lookbackDays} onChange={(e) => store.setLookbackDays(Number(e.target.value))}>
                  {LOOKBACK_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div style={styles.field}>
                <label style={styles.label}>Method</label>
                <select style={styles.select} value={store.corrMethod} onChange={(e) => store.setCorrMethod(e.target.value)}>
                  {CORR_METHODS.map((m) => <option key={m} value={m}>{m.charAt(0).toUpperCase() + m.slice(1)}</option>)}
                </select>
              </div>
              <div style={styles.field}>
                <label style={styles.label}>Clusters</label>
                <select style={styles.select} value={store.nClusters} onChange={(e) => store.setNClusters(Number(e.target.value))}>
                  {[2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
                </select>
              </div>
              <button style={styles.runBtn} disabled={isRunningCorr} onClick={handleRunCorr}>
                {isRunningCorr ? "Computing…" : "Run Correlation"}
              </button>
            </div>
            {corrError && <div style={styles.error}>{corrError}</div>}
          </div>

          {store.correlationResult && (
            <div style={styles.twoCol}>
              <section style={{ ...styles.card, flex: 1 }}>
                <div style={styles.cardTitle}>Correlation Matrix</div>
                <CorrelationHeatmap
                  tickers={store.correlationResult.corr?.tickers}
                  matrix={store.correlationResult.corr?.matrix}
                />
              </section>
              <section style={{ ...styles.card, flex: 1 }}>
                <div style={styles.cardTitle}>Cluster Analysis</div>
                {store.correlationResult.clusters && (
                  <div>
                    {Object.entries(store.correlationResult.clusters.cluster_summary ?? {}).map(([label, info]) => (
                      <div key={label} style={styles.clusterRow}>
                        <span style={styles.clusterLabel}>Cluster {label}</span>
                        <span style={styles.clusterMembers}>{info.members.join(", ")}</span>
                        <span style={styles.clusterCorr}>avg ρ: {info.avg_within_correlation?.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </div>
          )}

          {store.mstResult && (
            <section style={styles.card}>
              <CorrelationNetwork mstData={store.mstResult} />
            </section>
          )}
        </div>
      )}
    </div>
  );
}

const styles = {
  root: { padding: "28px 32px" },
  pageHeader: { marginBottom: 24 },
  h1: { fontSize: 24, fontWeight: 700, color: "#e2e8f0", margin: "0 0 6px" },
  sub: { fontSize: 14, color: "#64748b", margin: 0 },
  tabBar: { display: "flex", gap: 4, marginBottom: 20, flexWrap: "wrap" },
  tab: {
    background: "none",
    border: "1px solid #1e2230",
    borderRadius: 6,
    color: "#64748b",
    cursor: "pointer",
    fontSize: 12,
    fontWeight: 600,
    padding: "7px 16px",
    letterSpacing: "0.03em",
  },
  tabActive: { background: "#1e2230", color: "#93c5fd", borderColor: "#2d3748" },
  card: {
    background: "#080c14",
    border: "1px solid #1e2230",
    borderRadius: 12,
    padding: "20px 22px",
    marginBottom: 20,
  },
  cardTitle: { fontSize: 11, fontWeight: 700, color: "#475569", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 14 },
  controlRow: { display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" },
  field: { display: "flex", flexDirection: "column", gap: 4 },
  label: { fontSize: 10, fontWeight: 600, color: "#475569", letterSpacing: "0.06em", textTransform: "uppercase" },
  select: { background: "#0d1117", border: "1px solid #1e2230", borderRadius: 6, color: "#e2e8f0", fontSize: 12, padding: "7px 10px", outline: "none" },
  input: { background: "#0d1117", border: "1px solid #1e2230", borderRadius: 6, color: "#e2e8f0", fontSize: 12, padding: "7px 10px", outline: "none", width: 80 },
  runBtn: { background: "#2563eb", border: "none", borderRadius: 6, color: "#fff", fontSize: 12, fontWeight: 700, padding: "8px 20px", cursor: "pointer", alignSelf: "flex-end" },
  error: { color: "#f87171", fontSize: 12, marginTop: 10 },
  twoCol: { display: "flex", gap: 20, alignItems: "flex-start", flexWrap: "wrap" },
  empty: { color: "#334155", fontSize: 14, padding: "48px 0", textAlign: "center" },
  clusterRow: { display: "flex", alignItems: "center", gap: 12, padding: "6px 0", borderBottom: "1px solid #0d1117" },
  clusterLabel: { fontSize: 11, fontWeight: 700, color: "#2563eb", width: 70 },
  clusterMembers: { flex: 1, fontSize: 12, color: "#94a3b8" },
  clusterCorr: { fontSize: 11, color: "#475569" },
};
