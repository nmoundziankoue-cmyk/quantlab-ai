# QuantLab AI — Architecture

## Stack

| Layer | Technology |
|---|---|
| Backend runtime | Python 3.14, FastAPI, Uvicorn |
| Schema validation | Pydantic v2 |
| Database | PostgreSQL (SQLAlchemy 2, Alembic migrations) |
| Cache | Redis (optional; falls back to in-memory) |
| Frontend | React 18, React Router v6, Vite, Recharts |
| Containerisation | Docker / Docker Compose |

**Constraint (non-negotiable):** all quantitative computation uses pure Python. No scipy, numpy, pandas, TA-Lib, or QuantLib. Gaussian elimination, Pearson correlation, matrix inversion, and option pricing are all hand-implemented.

---

## Service Map

```
backend/
├── services/
│   ├── M1–M9    Portfolio, Market Data, Auth, Streaming, Options, AI Agents
│   ├── M10–M14  Alternative Data, Knowledge Graph, Portfolio Optimiser
│   ├── M15      Event Intelligence (Corporate + Macro Events)
│   ├── M16      Multi-Asset Engine
│   ├── M17      Institutional Trading & Order Management
│   ├── M18      Real-Time Analytics
│   │   ├── m18_alert_engine.py         AlertEngine — threshold alerts, rule registry
│   │   ├── m18_feature_engine.py       FeatureEngine — RSI, Kelly, signal generation
│   │   ├── m18_microstructure.py       Microstructure — bid-ask spread, VWAP, OBI
│   │   ├── m18_portfolio_intelligence.py PortfolioIntelligenceEngine — frontier, scoring
│   │   └── m18_risk_engine.py          RiskEngine — VaR, ES, stress tests, drawdown
│   ├── M19      Quant Research Engine
│   │   ├── m19_backtest_engine.py      Signal-driven backtester (LONG/SHORT/FLAT)
│   │   ├── m19_execution_simulator.py  Order simulation (MARKET/LIMIT/STOP/STOP_LIMIT)
│   │   ├── m19_walk_forward.py         ROLLING/EXPANDING walk-forward validation
│   │   ├── m19_monte_carlo.py          Bootstrap + GBM Monte Carlo, VaR/CVaR
│   │   ├── m19_factor_models.py        OLS factor regression, Gauss-Jordan, Pearson
│   │   └── m19_optimization_lab.py     MV/MinVar/MaxSharpe/RiskParity optimisation
│   └── M20      Quant Research Platform Closeout
│       ├── m20_regime_detection.py     RegimeDetectionEngine — BULL/BEAR/HIGH_VOL/LOW_VOL/RANGING
│       ├── m20_correlation_covariance.py CorrelationCovarianceEngine — N×N Pearson, rolling, clusters
│       └── m20_strategy_comparison.py  StrategyComparisonEngine — Sharpe/Sortino/Calmar ranking
├── routers/
│   ├── m19_research.py          112 endpoints, prefix /quant
│   └── m20_research_closeout.py  38 endpoints, prefix /quant/m20
├── schemas/
│   ├── m19_research.py          Pydantic v2 schemas for M19
│   └── m20_research.py          Pydantic v2 schemas for M20
└── main.py                       FastAPI app, router registration
```

---

## Data Flows

### Backtest → Strategy Comparison
```
Client
  └─POST /quant/m20/comparison/run-and-register
         ├─ StrategyComparisonEngine.run_and_register()
         │    ├─ BacktestEngine.run()          [M19]
         │    │    └─ equity_curve: List[EquityPoint]
         │    └─ _compute_metrics()
         │         ├─ _annualized_return(equity_floats)
         │         ├─ _annualized_vol(equity_floats)
         │         ├─ _sortino_ratio(equity_floats)
         │         └─ _calmar_ratio(ann_ret, max_drawdown)
         └─ returns strategy_id (UUID)

Client
  └─POST /quant/m20/comparison/compare
         └─ StrategyComparisonEngine.compare(strategy_ids, primary_metric)
              ├─ Normalise metrics (min-max)
              ├─ Composite score (40% Sharpe + 25% Sortino + 20% Calmar + 15% DD)
              ├─ Sort by primary_metric
              └─ Equity-curve Pearson correlation matrix (optional)
```

### Regime Detection
```
Client
  └─POST /quant/m20/regime/detect
         └─ RegimeDetectionEngine.detect(ticker, bars)
              └─ _detect_from_series()
                   ├─ for each bar i:
                   │    ├─ fast_ma = _sma(closes[:i], 50)
                   │    ├─ slow_ma = _sma(closes[:i], 200)
                   │    ├─ momentum = _momentum(closes[:i], 20)
                   │    ├─ recent_vol = _realized_vol_annual(closes[:i], 20)
                   │    ├─ long_vol   = _realized_vol_annual(closes[:i], 252)
                   │    └─ _classify() → RegimeType + confidence
                   └─ RegimeResult (cached per ticker)
```

### Correlation Pipeline
```
Client
  └─POST /quant/m20/correlation/add-returns-batch  (seed N tickers)
  └─POST /quant/m20/correlation/matrix             → CorrelationMatrix (N×N Pearson)
  └─POST /quant/m20/correlation/rolling            → RollingCorrelation (sliding window)
  └─POST /quant/m20/correlation/clusters           → List[CorrelationCluster] (greedy single-linkage)
```

### M18 FeatureEngine Bridge (M19)
```
POST /quant/backtest/feature-driven
  └─ lazy import services.m18_feature_engine.FeatureEngine
       ├─ compute_rsi(prices)   → RSI-based signals
       ├─ compute_kelly(...)    → position sizing
       └─ BacktestEngine.run() [M19]   (no indicator duplication)
```

---

## Router Prefix Map

| Prefix | Milestone | File |
|---|---|---|
| `/research` | M18 | `routers/m18_realtime.py` |
| `/quant` | M19 | `routers/m19_research.py` |
| `/quant/m20` | M20 | `routers/m20_research_closeout.py` |
| `/events` | M15 | `routers/events.py` |
| `/portfolio` | M1–M10 | `routers/portfolio.py` |

---

## Design Decisions

### 1. Pure-Python Math
All matrix operations (OLS regression, Gauss-Jordan elimination, efficient frontier, Pearson correlation, annualised volatility) are implemented from scratch in Python. This eliminates C-extension dependencies and makes the Docker image ~400 MB smaller than a scipy-based equivalent.

### 2. No isinstance Overloading
M18 services originally used isinstance-dispatch to emulate method overloading (`fire_custom_alert`, `evaluate`, `compute_portfolio_var`, `run_stress_test`). M20 Part B eliminated all these patterns: each method now has a single clean signature. Alternative entry points are exposed as separate methods (`add_rule_object`, `compute_frontier_from_holdings`).

### 3. Singleton Engines + reset()
Each router module owns a module-level singleton (e.g., `_regime_engine = RegimeDetectionEngine()`). All engines implement `reset()`. Tests call `setup_method()` to create fresh instances, preventing cross-test state pollution discovered in M18.

### 4. Composition Over Inheritance
- `WalkForwardEngine(backtest_engine=_backtest_engine)` shares the M19 singleton.
- `OptimizationLab(factor_engine=_factor_engine)` consumes FactorModelEngine results directly.
- `StrategyComparisonEngine(backtest_engine=_backtest_engine_m20)` runs fresh backtests internally.

### 5. Router Prefix Isolation
M19 router uses `/quant` (not `/research`) to avoid shadowing M18's routes. M20 uses `/quant/m20` to avoid shadowing M19. FastAPI registers routes in declaration order; conflicts would cause the first-registered route to win silently.

### 6. Lazy React Imports
All 65+ frontend pages are loaded via `React.lazy` + `Suspense`. The initial bundle (`index.js`) is 242 kB, down from 1.18 MB before M8. Each page ships as a separate chunk.

---

## Test Coverage

| Module | Tests | Files |
|---|---|---|
| M1–M9 | ~1562 | Multiple |
| M10–M14 | ~503 | Multiple |
| M15 | 376 | 2 |
| M16–M18 | 723 | 6 |
| M19 | 422 | 9 |
| M20 | 236 | 5 |
| **Total** | **4,660** | **40+** |

332 test-collection errors are all `sqlalchemy.exc.OperationalError: connection refused port 5432` — expected in environments without a running PostgreSQL instance.

---

## Deployment

```bash
# Development (in-memory cache, SQLite-compatible)
cd apexquant-v25/backend
uvicorn main:app --reload

# Production (Docker Compose)
docker compose up --build

# Frontend only
cd frontend && npm run build && serve dist/
```

See [.env.example](backend/.env.example) for all required environment variables.
