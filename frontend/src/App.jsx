import { lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import Shell from "./components/layout/Shell";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import ErrorBoundary from "./components/ui/ErrorBoundary";
import { ToastProvider } from "./context/ToastContext";

const Login = lazy(() => import("./pages/Login"));
const Register = lazy(() => import("./pages/Register"));

// Lazy-load every page so each chunk is only fetched when first navigated to.
// This keeps the initial JS bundle under 500 KB.
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Portfolio = lazy(() => import("./pages/Portfolio"));
const Markets = lazy(() => import("./pages/Markets"));
const Research = lazy(() => import("./pages/Research"));
const PortfolioAnalytics = lazy(() => import("./pages/PortfolioAnalytics"));
const Trading = lazy(() => import("./pages/Trading"));
const Orders = lazy(() => import("./pages/Orders"));
const TradeBlotter = lazy(() => import("./pages/TradeBlotter"));
const ExecutionAnalytics = lazy(() => import("./pages/ExecutionAnalytics"));
const PaperTrading = lazy(() => import("./pages/PaperTrading"));
const BrokerConnections = lazy(() => import("./pages/BrokerConnections"));
const ResearchDashboard = lazy(() => import("./pages/ResearchDashboard"));
const ResearchWorkspace = lazy(() => import("./pages/ResearchWorkspace"));
const AICopilot = lazy(() => import("./pages/AICopilot"));
const DocumentLibrary = lazy(() => import("./pages/DocumentLibrary"));
const NewsTerminal = lazy(() => import("./pages/NewsTerminal"));
const AlternativeData = lazy(() => import("./pages/AlternativeData"));
const ResearchReports = lazy(() => import("./pages/ResearchReports"));
const Screeners = lazy(() => import("./pages/Screeners"));
const AgentDashboard = lazy(() => import("./pages/AgentDashboard"));
const OptionsDesk = lazy(() => import("./pages/OptionsDesk"));
const MarketIntelligence = lazy(() => import("./pages/MarketIntelligence"));
const AgentOrchestrator = lazy(() => import("./pages/AgentOrchestrator"));
const EconomicCalendar = lazy(() => import("./pages/EconomicCalendar"));
const KnowledgeGraph = lazy(() => import("./pages/KnowledgeGraph"));
const NotificationCenter = lazy(() => import("./pages/NotificationCenter"));
const SecuritySettings = lazy(() => import("./pages/SecuritySettings"));
const SystemMetrics = lazy(() => import("./pages/SystemMetrics"));
const ProviderDashboard = lazy(() => import("./pages/ProviderDashboard"));
const StrategyBuilder = lazy(() => import("./pages/StrategyBuilder"));
const LiveMarkets = lazy(() => import("./pages/LiveMarkets"));
const RiskCenter = lazy(() => import("./pages/RiskCenter"));
const ExecutionMonitor = lazy(() => import("./pages/ExecutionMonitor"));
const ResearchNotebook = lazy(() => import("./pages/ResearchNotebook"));
const AgentWorkspace = lazy(() => import("./pages/AgentWorkspace"));
const KnowledgeExplorer = lazy(() => import("./pages/KnowledgeExplorer"));
const NewsIntelligence = lazy(() => import("./pages/NewsIntelligence"));
const PortfolioOptimizer = lazy(() => import("./pages/PortfolioOptimizer"));
const MarketDataExplorer = lazy(() => import("./pages/MarketDataExplorer"));
const DatasetBuilder = lazy(() => import("./pages/DatasetBuilder"));

// M14 — Alternative Data Intelligence Platform
const AltDataExplorer = lazy(() => import("./pages/AltDataExplorer"));
const AltDocumentViewer = lazy(() => import("./pages/AltDocumentViewer"));
const AltSECFilingReader = lazy(() => import("./pages/AltSECFilingReader"));
const AltKnowledgeGraphExplorer = lazy(() => import("./pages/AltKnowledgeGraphExplorer"));
const AltEventTimeline = lazy(() => import("./pages/AltEventTimeline"));
const AltInsiderActivity = lazy(() => import("./pages/AltInsiderActivity"));
const AltPatentIntelligence = lazy(() => import("./pages/AltPatentIntelligence"));
const AltTranscriptAnalyzer = lazy(() => import("./pages/AltTranscriptAnalyzer"));
const AltSearchDashboard = lazy(() => import("./pages/AltSearchDashboard"));

const MultiAssetDashboard = lazy(() => import("./pages/MultiAssetDashboard"));
const CorrelationMatrix = lazy(() => import("./pages/CorrelationMatrix"));
const FactorDashboard = lazy(() => import("./pages/FactorDashboard"));
const ETFExplorer = lazy(() => import("./pages/ETFExplorer"));
const BondAnalytics = lazy(() => import("./pages/BondAnalytics"));
const OptionsAnalytics = lazy(() => import("./pages/OptionsAnalytics"));
const FuturesDashboard = lazy(() => import("./pages/FuturesDashboard"));
const CryptoDashboard = lazy(() => import("./pages/CryptoDashboard"));
const PortfolioExposure = lazy(() => import("./pages/PortfolioExposure"));
const AssetRegistry = lazy(() => import("./pages/AssetRegistry"));
const CrossAssetExplorer = lazy(() => import("./pages/CrossAssetExplorer"));
const MarketMap = lazy(() => import("./pages/MarketMap"));

// M17 — Institutional Trading & Portfolio Management Platform
const M17TradingDashboard = lazy(() => import("./pages/M17TradingDashboard"));
const M17OMS = lazy(() => import("./pages/M17OMS"));
const M17OrderTicket = lazy(() => import("./pages/M17OrderTicket"));
const M17TradeBlotter = lazy(() => import("./pages/M17TradeBlotter"));
const M17Positions = lazy(() => import("./pages/M17Positions"));
const M17RiskLimits = lazy(() => import("./pages/M17RiskLimits"));
const M17TradeAnalytics = lazy(() => import("./pages/M17TradeAnalytics"));
const M17BrokerDashboard = lazy(() => import("./pages/M17BrokerDashboard"));
const M17PaperTrading = lazy(() => import("./pages/M17PaperTrading"));
const M17PortfolioAccounting = lazy(() => import("./pages/M17PortfolioAccounting"));
const M17PerformanceAttribution = lazy(() => import("./pages/M17PerformanceAttribution"));
const M17ExecutionCost = lazy(() => import("./pages/M17ExecutionCost"));
const M17ExecutionMonitor = lazy(() => import("./pages/M17ExecutionMonitor"));
const M17Orders = lazy(() => import("./pages/M17Orders"));
const M17ExecutionHistory = lazy(() => import("./pages/M17ExecutionHistory"));

// M18 — Real-Time Institutional Operating System
const M18Dashboard = lazy(() => import("./pages/M18Dashboard"));
const M18StreamingMonitor = lazy(() => import("./pages/M18StreamingMonitor"));
const M18MarketGateway = lazy(() => import("./pages/M18MarketGateway"));
const M18Microstructure = lazy(() => import("./pages/M18Microstructure"));
const M18FeatureEngine = lazy(() => import("./pages/M18FeatureEngine"));
const M18RiskEngine = lazy(() => import("./pages/M18RiskEngine"));
const M18PortfolioIntel = lazy(() => import("./pages/M18PortfolioIntel"));
const M18AlertCenter = lazy(() => import("./pages/M18AlertCenter"));
const M18EconomicIntel = lazy(() => import("./pages/M18EconomicIntel"));
const M18NewsIntel = lazy(() => import("./pages/M18NewsIntel"));
const M18EarningsIntel = lazy(() => import("./pages/M18EarningsIntel"));
const M18AgentConsole = lazy(() => import("./pages/M18AgentConsole"));
const M18Watchlists = lazy(() => import("./pages/M18Watchlists"));
const M18YieldCurve = lazy(() => import("./pages/M18YieldCurve"));
const M18StressTest = lazy(() => import("./pages/M18StressTest"));
const M18AttributionCenter = lazy(() => import("./pages/M18AttributionCenter"));
const M18EfficientFrontier = lazy(() => import("./pages/M18EfficientFrontier"));
const M18TrendDetector = lazy(() => import("./pages/M18TrendDetector"));
const M18EarningsCalendar = lazy(() => import("./pages/M18EarningsCalendar"));
const M18EconomicCalendar = lazy(() => import("./pages/M18EconomicCalendar"));

// M19 — Quant Research Engine
const M19Dashboard = lazy(() => import("./pages/M19Dashboard"));
const M19BacktestStudio = lazy(() => import("./pages/M19BacktestStudio"));
const M19EquityCurveViewer = lazy(() => import("./pages/M19EquityCurveViewer"));
const M19ExecutionSimulator = lazy(() => import("./pages/M19ExecutionSimulator"));
const M19WalkForwardAnalyzer = lazy(() => import("./pages/M19WalkForwardAnalyzer"));
const M19MonteCarloViewer = lazy(() => import("./pages/M19MonteCarloViewer"));
const M19FactorExposureDashboard = lazy(() => import("./pages/M19FactorExposureDashboard"));
const M19OptimizationLab = lazy(() => import("./pages/M19OptimizationLab"));
const M19StrategyComparison = lazy(() => import("./pages/M19StrategyComparison"));
const M19EfficientFrontier = lazy(() => import("./pages/M19EfficientFrontier"));
const M19ScenarioEngine = lazy(() => import("./pages/M19ScenarioEngine"));
const M19RiskDashboard = lazy(() => import("./pages/M19RiskDashboard"));

const M20Dashboard = lazy(() => import("./pages/M20Dashboard"));
const M20RegimeDashboard = lazy(() => import("./pages/M20RegimeDashboard"));
const M20CorrelationHeatmap = lazy(() => import("./pages/M20CorrelationHeatmap"));
const M20StrategyComparison = lazy(() => import("./pages/M20StrategyComparison"));

const EventDashboard = lazy(() => import("./pages/EventDashboard"));
const CorporateEvents = lazy(() => import("./pages/CorporateEvents"));
const MacroEvents = lazy(() => import("./pages/MacroEvents"));
const EventTimeline = lazy(() => import("./pages/EventTimeline"));
const EventCalendarPage = lazy(() => import("./pages/EventCalendar"));
const EventImpactAnalysis = lazy(() => import("./pages/EventImpactAnalysis"));
const EventStudyPage = lazy(() => import("./pages/EventStudy"));
const EventReports = lazy(() => import("./pages/EventReports"));
const CatalystDashboard = lazy(() => import("./pages/CatalystDashboard"));
const AIEventIntelligence = lazy(() => import("./pages/AIEventIntelligence"));
const EventSearch = lazy(() => import("./pages/EventSearch"));
const EventHeatmap = lazy(() => import("./pages/EventHeatmap"));

const PageLoader = () => (
  <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", background: "#0d1117", color: "#8b949e", fontSize: 14 }}>
    Loading…
  </div>
);

export default function App() {
  return (
    <ErrorBoundary>
      <ToastProvider>
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<Suspense fallback={<PageLoader />}><Login /></Suspense>} />
      <Route path="/register" element={<Suspense fallback={<PageLoader />}><Register /></Suspense>} />

      {/* Protected app shell */}
      <Route element={<ProtectedRoute><Shell /></ProtectedRoute>}>
        <Route index element={<Suspense fallback={<PageLoader />}><Dashboard /></Suspense>} />
        <Route path="portfolio-detail/:id" element={<Suspense fallback={<PageLoader />}><Portfolio /></Suspense>} />
        <Route path="markets" element={<Suspense fallback={<PageLoader />}><Markets /></Suspense>} />
        <Route path="research" element={<Suspense fallback={<PageLoader />}><Research /></Suspense>} />
        <Route path="analytics" element={<Suspense fallback={<PageLoader />}><PortfolioAnalytics /></Suspense>} />
        <Route path="analytics/:id" element={<Suspense fallback={<PageLoader />}><PortfolioAnalytics /></Suspense>} />
        <Route path="trading" element={<Suspense fallback={<PageLoader />}><Trading /></Suspense>} />
        <Route path="orders" element={<Suspense fallback={<PageLoader />}><Orders /></Suspense>} />
        <Route path="blotter" element={<Suspense fallback={<PageLoader />}><TradeBlotter /></Suspense>} />
        <Route path="execution-analytics" element={<Suspense fallback={<PageLoader />}><ExecutionAnalytics /></Suspense>} />
        <Route path="paper-trading" element={<Suspense fallback={<PageLoader />}><PaperTrading /></Suspense>} />
        <Route path="brokers" element={<Suspense fallback={<PageLoader />}><BrokerConnections /></Suspense>} />
        <Route path="research-dashboard" element={<Suspense fallback={<PageLoader />}><ResearchDashboard /></Suspense>} />
        <Route path="workspace" element={<Suspense fallback={<PageLoader />}><ResearchWorkspace /></Suspense>} />
        <Route path="copilot" element={<Suspense fallback={<PageLoader />}><AICopilot /></Suspense>} />
        <Route path="documents" element={<Suspense fallback={<PageLoader />}><DocumentLibrary /></Suspense>} />
        <Route path="news-terminal" element={<Suspense fallback={<PageLoader />}><NewsTerminal /></Suspense>} />
        <Route path="alternative-data" element={<Suspense fallback={<PageLoader />}><AlternativeData /></Suspense>} />
        <Route path="reports" element={<Suspense fallback={<PageLoader />}><ResearchReports /></Suspense>} />
        <Route path="screeners" element={<Suspense fallback={<PageLoader />}><Screeners /></Suspense>} />
        <Route path="agents" element={<Suspense fallback={<PageLoader />}><AgentDashboard /></Suspense>} />
        <Route path="options-desk" element={<Suspense fallback={<PageLoader />}><OptionsDesk /></Suspense>} />
        <Route path="market-intelligence" element={<Suspense fallback={<PageLoader />}><MarketIntelligence /></Suspense>} />
        <Route path="agent-orchestrator" element={<Suspense fallback={<PageLoader />}><AgentOrchestrator /></Suspense>} />
        <Route path="economic-calendar" element={<Suspense fallback={<PageLoader />}><EconomicCalendar /></Suspense>} />
        <Route path="knowledge-graph" element={<Suspense fallback={<PageLoader />}><KnowledgeGraph /></Suspense>} />
        <Route path="notifications" element={<Suspense fallback={<PageLoader />}><NotificationCenter /></Suspense>} />
        <Route path="security" element={<Suspense fallback={<PageLoader />}><SecuritySettings /></Suspense>} />
        <Route path="system-metrics" element={<Suspense fallback={<PageLoader />}><SystemMetrics /></Suspense>} />
        <Route path="provider-dashboard" element={<Suspense fallback={<PageLoader />}><ProviderDashboard /></Suspense>} />
        <Route path="strategy-builder" element={<Suspense fallback={<PageLoader />}><StrategyBuilder /></Suspense>} />
        <Route path="live-markets" element={<Suspense fallback={<PageLoader />}><LiveMarkets /></Suspense>} />
        <Route path="risk-center" element={<Suspense fallback={<PageLoader />}><RiskCenter /></Suspense>} />
        <Route path="execution-monitor" element={<Suspense fallback={<PageLoader />}><ExecutionMonitor /></Suspense>} />
        <Route path="research-notebook" element={<Suspense fallback={<PageLoader />}><ResearchNotebook /></Suspense>} />
        <Route path="agent-workspace" element={<Suspense fallback={<PageLoader />}><AgentWorkspace /></Suspense>} />
        <Route path="knowledge-explorer" element={<Suspense fallback={<PageLoader />}><KnowledgeExplorer /></Suspense>} />
        <Route path="news-intelligence" element={<Suspense fallback={<PageLoader />}><NewsIntelligence /></Suspense>} />
        <Route path="portfolio-optimizer" element={<Suspense fallback={<PageLoader />}><PortfolioOptimizer /></Suspense>} />
        <Route path="market-data-explorer" element={<Suspense fallback={<PageLoader />}><MarketDataExplorer /></Suspense>} />
        <Route path="dataset-builder" element={<Suspense fallback={<PageLoader />}><DatasetBuilder /></Suspense>} />
        {/* M14 — Alternative Data Intelligence Platform */}
        <Route path="alt-data-explorer" element={<Suspense fallback={<PageLoader />}><AltDataExplorer /></Suspense>} />
        <Route path="alt-document-viewer" element={<Suspense fallback={<PageLoader />}><AltDocumentViewer /></Suspense>} />
        <Route path="alt-sec-filing-reader" element={<Suspense fallback={<PageLoader />}><AltSECFilingReader /></Suspense>} />
        <Route path="alt-knowledge-graph" element={<Suspense fallback={<PageLoader />}><AltKnowledgeGraphExplorer /></Suspense>} />
        <Route path="alt-event-timeline" element={<Suspense fallback={<PageLoader />}><AltEventTimeline /></Suspense>} />
        <Route path="alt-insider-activity" element={<Suspense fallback={<PageLoader />}><AltInsiderActivity /></Suspense>} />
        <Route path="alt-patent-intelligence" element={<Suspense fallback={<PageLoader />}><AltPatentIntelligence /></Suspense>} />
        <Route path="alt-transcript-analyzer" element={<Suspense fallback={<PageLoader />}><AltTranscriptAnalyzer /></Suspense>} />
        <Route path="alt-search" element={<Suspense fallback={<PageLoader />}><AltSearchDashboard /></Suspense>} />
        {/* M16 — Institutional Multi-Asset Analytics Platform */}
        <Route path="multi-asset-dashboard" element={<Suspense fallback={<PageLoader />}><MultiAssetDashboard /></Suspense>} />
        <Route path="correlation-matrix" element={<Suspense fallback={<PageLoader />}><CorrelationMatrix /></Suspense>} />
        <Route path="factor-dashboard" element={<Suspense fallback={<PageLoader />}><FactorDashboard /></Suspense>} />
        <Route path="etf-explorer" element={<Suspense fallback={<PageLoader />}><ETFExplorer /></Suspense>} />
        <Route path="bond-analytics" element={<Suspense fallback={<PageLoader />}><BondAnalytics /></Suspense>} />
        <Route path="options-analytics" element={<Suspense fallback={<PageLoader />}><OptionsAnalytics /></Suspense>} />
        <Route path="futures-dashboard" element={<Suspense fallback={<PageLoader />}><FuturesDashboard /></Suspense>} />
        <Route path="crypto-dashboard" element={<Suspense fallback={<PageLoader />}><CryptoDashboard /></Suspense>} />
        <Route path="portfolio-exposure" element={<Suspense fallback={<PageLoader />}><PortfolioExposure /></Suspense>} />
        <Route path="asset-registry" element={<Suspense fallback={<PageLoader />}><AssetRegistry /></Suspense>} />
        <Route path="cross-asset-explorer" element={<Suspense fallback={<PageLoader />}><CrossAssetExplorer /></Suspense>} />
        <Route path="market-map" element={<Suspense fallback={<PageLoader />}><MarketMap /></Suspense>} />
        {/* M15 — Institutional Event Intelligence Platform */}
        <Route path="event-dashboard" element={<Suspense fallback={<PageLoader />}><EventDashboard /></Suspense>} />
        <Route path="corporate-events" element={<Suspense fallback={<PageLoader />}><CorporateEvents /></Suspense>} />
        <Route path="macro-events" element={<Suspense fallback={<PageLoader />}><MacroEvents /></Suspense>} />
        <Route path="event-timeline" element={<Suspense fallback={<PageLoader />}><EventTimeline /></Suspense>} />
        <Route path="event-calendar" element={<Suspense fallback={<PageLoader />}><EventCalendarPage /></Suspense>} />
        <Route path="event-study" element={<Suspense fallback={<PageLoader />}><EventStudyPage /></Suspense>} />
        <Route path="event-impact" element={<Suspense fallback={<PageLoader />}><EventImpactAnalysis /></Suspense>} />
        <Route path="catalyst-dashboard" element={<Suspense fallback={<PageLoader />}><CatalystDashboard /></Suspense>} />
        <Route path="ai-event-intelligence" element={<Suspense fallback={<PageLoader />}><AIEventIntelligence /></Suspense>} />
        <Route path="event-search" element={<Suspense fallback={<PageLoader />}><EventSearch /></Suspense>} />
        <Route path="event-reports" element={<Suspense fallback={<PageLoader />}><EventReports /></Suspense>} />
        <Route path="event-heatmap" element={<Suspense fallback={<PageLoader />}><EventHeatmap /></Suspense>} />
        {/* M18 — Real-Time Institutional Operating System */}
        <Route path="m18-dashboard" element={<Suspense fallback={<PageLoader />}><M18Dashboard /></Suspense>} />
        <Route path="m18-streaming" element={<Suspense fallback={<PageLoader />}><M18StreamingMonitor /></Suspense>} />
        <Route path="m18-gateway" element={<Suspense fallback={<PageLoader />}><M18MarketGateway /></Suspense>} />
        <Route path="m18-microstructure" element={<Suspense fallback={<PageLoader />}><M18Microstructure /></Suspense>} />
        <Route path="m18-features" element={<Suspense fallback={<PageLoader />}><M18FeatureEngine /></Suspense>} />
        <Route path="m18-risk" element={<Suspense fallback={<PageLoader />}><M18RiskEngine /></Suspense>} />
        <Route path="m18-portfolio-intel" element={<Suspense fallback={<PageLoader />}><M18PortfolioIntel /></Suspense>} />
        <Route path="m18-alerts" element={<Suspense fallback={<PageLoader />}><M18AlertCenter /></Suspense>} />
        <Route path="m18-economic" element={<Suspense fallback={<PageLoader />}><M18EconomicIntel /></Suspense>} />
        <Route path="m18-news" element={<Suspense fallback={<PageLoader />}><M18NewsIntel /></Suspense>} />
        <Route path="m18-earnings" element={<Suspense fallback={<PageLoader />}><M18EarningsIntel /></Suspense>} />
        <Route path="m18-agents" element={<Suspense fallback={<PageLoader />}><M18AgentConsole /></Suspense>} />
        <Route path="m18-agent-console" element={<Suspense fallback={<PageLoader />}><M18AgentConsole /></Suspense>} />
        <Route path="m18-watchlists" element={<Suspense fallback={<PageLoader />}><M18Watchlists /></Suspense>} />
        <Route path="m18-yield-curve" element={<Suspense fallback={<PageLoader />}><M18YieldCurve /></Suspense>} />
        <Route path="m18-stress-test" element={<Suspense fallback={<PageLoader />}><M18StressTest /></Suspense>} />
        <Route path="m18-attribution" element={<Suspense fallback={<PageLoader />}><M18AttributionCenter /></Suspense>} />
        <Route path="m18-frontier" element={<Suspense fallback={<PageLoader />}><M18EfficientFrontier /></Suspense>} />
        <Route path="m18-trends" element={<Suspense fallback={<PageLoader />}><M18TrendDetector /></Suspense>} />
        <Route path="m18-earnings-calendar" element={<Suspense fallback={<PageLoader />}><M18EarningsCalendar /></Suspense>} />
        <Route path="m18-economic-calendar" element={<Suspense fallback={<PageLoader />}><M18EconomicCalendar /></Suspense>} />
        {/* M19 — Quant Research Engine */}
        <Route path="m19-dashboard" element={<Suspense fallback={<PageLoader />}><M19Dashboard /></Suspense>} />
        <Route path="m19-backtest" element={<Suspense fallback={<PageLoader />}><M19BacktestStudio /></Suspense>} />
        <Route path="m19-equity-curve" element={<Suspense fallback={<PageLoader />}><M19EquityCurveViewer /></Suspense>} />
        <Route path="m19-execution" element={<Suspense fallback={<PageLoader />}><M19ExecutionSimulator /></Suspense>} />
        <Route path="m19-walk-forward" element={<Suspense fallback={<PageLoader />}><M19WalkForwardAnalyzer /></Suspense>} />
        <Route path="m19-monte-carlo" element={<Suspense fallback={<PageLoader />}><M19MonteCarloViewer /></Suspense>} />
        <Route path="m19-factor-models" element={<Suspense fallback={<PageLoader />}><M19FactorExposureDashboard /></Suspense>} />
        <Route path="m19-factor-exposure" element={<Suspense fallback={<PageLoader />}><M19FactorExposureDashboard /></Suspense>} />
        <Route path="m19-optimization" element={<Suspense fallback={<PageLoader />}><M19OptimizationLab /></Suspense>} />
        <Route path="m19-strategy-compare" element={<Suspense fallback={<PageLoader />}><M19StrategyComparison /></Suspense>} />
        <Route path="m19-frontier" element={<Suspense fallback={<PageLoader />}><M19EfficientFrontier /></Suspense>} />
        <Route path="m19-scenarios" element={<Suspense fallback={<PageLoader />}><M19ScenarioEngine /></Suspense>} />
        <Route path="m19-risk" element={<Suspense fallback={<PageLoader />}><M19RiskDashboard /></Suspense>} />
        {/* M20 — Quant Research Platform Closeout */}
        <Route path="m20" element={<Suspense fallback={<PageLoader />}><M20Dashboard /></Suspense>} />
        <Route path="m20/regime" element={<Suspense fallback={<PageLoader />}><M20RegimeDashboard /></Suspense>} />
        <Route path="m20/correlation" element={<Suspense fallback={<PageLoader />}><M20CorrelationHeatmap /></Suspense>} />
        <Route path="m20/comparison" element={<Suspense fallback={<PageLoader />}><M20StrategyComparison /></Suspense>} />
        {/* M17 — Institutional Trading & Portfolio Management Platform */}
        <Route path="m17-trading" element={<Suspense fallback={<PageLoader />}><M17TradingDashboard /></Suspense>} />
        <Route path="m17-oms" element={<Suspense fallback={<PageLoader />}><M17OMS /></Suspense>} />
        <Route path="m17-order-ticket" element={<Suspense fallback={<PageLoader />}><M17OrderTicket /></Suspense>} />
        <Route path="m17-blotter" element={<Suspense fallback={<PageLoader />}><M17TradeBlotter /></Suspense>} />
        <Route path="m17-positions" element={<Suspense fallback={<PageLoader />}><M17Positions /></Suspense>} />
        <Route path="m17-risk" element={<Suspense fallback={<PageLoader />}><M17RiskLimits /></Suspense>} />
        <Route path="m17-analytics" element={<Suspense fallback={<PageLoader />}><M17TradeAnalytics /></Suspense>} />
        <Route path="m17-brokers" element={<Suspense fallback={<PageLoader />}><M17BrokerDashboard /></Suspense>} />
        <Route path="m17-paper-trading" element={<Suspense fallback={<PageLoader />}><M17PaperTrading /></Suspense>} />
        <Route path="m17-accounting" element={<Suspense fallback={<PageLoader />}><M17PortfolioAccounting /></Suspense>} />
        <Route path="m17-attribution" element={<Suspense fallback={<PageLoader />}><M17PerformanceAttribution /></Suspense>} />
        <Route path="m17-tca" element={<Suspense fallback={<PageLoader />}><M17ExecutionCost /></Suspense>} />
        <Route path="m17-execution" element={<Suspense fallback={<PageLoader />}><M17ExecutionMonitor /></Suspense>} />
        <Route path="m17-orders" element={<Suspense fallback={<PageLoader />}><M17Orders /></Suspense>} />
        <Route path="m17-history" element={<Suspense fallback={<PageLoader />}><M17ExecutionHistory /></Suspense>} />
        <Route path="*" element={
          <div style={{ padding: "60px 40px", textAlign: "center" }}>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--accent)", letterSpacing: "0.1em", marginBottom: 12 }}>404</div>
            <h2 style={{ fontFamily: "var(--font-display)", fontSize: 22, color: "var(--text-1)", margin: "0 0 8px" }}>Page not found</h2>
            <p style={{ fontFamily: "var(--font-body)", fontSize: 13, color: "var(--text-3)", margin: "0 0 24px" }}>This route doesn't exist in QuantLab AI.</p>
            <a href="/" style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--accent)", textDecoration: "none", border: "1px solid var(--accent)", padding: "8px 20px", borderRadius: 6 }}>← Back to Dashboard</a>
          </div>
        } />
      </Route>
    </Routes>
      </ToastProvider>
    </ErrorBoundary>
  );
}
