import { Outlet, useLocation } from "react-router-dom";
import { useState, useEffect } from "react";
import Sidebar from "./Sidebar";
import useRegimeStore, { REGIME_COLORS } from "../../store/useRegimeStore";
import ErrorBoundary from "../ui/ErrorBoundary";

const WS_LABELS = { connecting: "Connecting", open: "Live", closed: "Offline" };
const WS_COLORS = { connecting: "#E2A52B", open: "#27C784", closed: "#454D66" };

function useBackendStatus() {
  const [state, setState] = useState("connecting");
  useEffect(() => {
    let alive = true;
    const probe = () => {
      fetch("/health", { signal: AbortSignal.timeout(8000) })
        .then((r) => { if (alive) setState(r.ok ? "open" : "closed"); })
        .catch(() => { if (alive) setState("closed"); });
    };
    probe();
    const id = setInterval(probe, 30_000);
    return () => { alive = false; clearInterval(id); };
  }, []);
  return state;
}

function Topbar({ wsState }) {
  const regime = useRegimeStore((s) => s.regime);
  const confidence = useRegimeStore((s) => s.confidence);
  const color = REGIME_COLORS[regime] ?? "#7A84A0";
  const wsColor = WS_COLORS[wsState] ?? "#454D66";
  const wsLabel = WS_LABELS[wsState] ?? wsState;

  return (
    <div style={S.topbar}>
      {/* Regime badge — signature element */}
      <div style={S.regimeBadge}>
        <span style={{ ...S.regimeDot, background: color }} />
        <span style={{ ...S.regimeLabel, color }}>{regime}</span>
        {confidence > 0 && (
          <span style={S.regimeConf}>{(confidence * 100).toFixed(0)}%</span>
        )}
      </div>

      {/* Right cluster */}
      <div style={S.topbarRight}>
        <span style={{ ...S.wsStatus, color: wsColor }}>
          <span style={{ ...S.wsDot, background: wsColor }} />
          {wsLabel}
        </span>
        <span style={S.version}>QuantLab AI v2.0</span>
      </div>
    </div>
  );
}

export default function Shell() {
  const wsState = useBackendStatus();
  const { pathname } = useLocation();

  return (
    <div style={S.root}>
      <Sidebar />
      <div style={S.content}>
        <Topbar wsState={wsState} />
        <main style={S.main}>
          <div key={pathname} className="ql-page-enter">
            <ErrorBoundary key={pathname}>
              <Outlet />
            </ErrorBoundary>
          </div>
        </main>
      </div>
    </div>
  );
}

const S = {
  root: {
    display: "flex",
    minHeight: "100vh",
    background: "var(--canvas)",
    fontFamily: "var(--font-body)",
    color: "var(--text-1)",
  },
  content: { flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", minWidth: 0 },
  topbar: {
    height: 44,
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "0 24px",
    borderBottom: "1px solid var(--border)",
    background: "var(--panel)",
    flexShrink: 0,
  },
  regimeBadge: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    fontFamily: "var(--font-mono)",
    fontSize: 11,
    fontWeight: 500,
  },
  regimeDot: {
    width: 6,
    height: 6,
    borderRadius: "50%",
    flexShrink: 0,
  },
  regimeLabel: {
    fontWeight: 600,
    letterSpacing: "0.05em",
  },
  regimeConf: {
    color: "var(--text-3)",
    fontSize: 10,
  },
  topbarRight: {
    display: "flex",
    alignItems: "center",
    gap: 20,
  },
  wsStatus: {
    display: "flex",
    alignItems: "center",
    gap: 5,
    fontFamily: "var(--font-mono)",
    fontSize: 10,
    fontWeight: 500,
    letterSpacing: "0.04em",
  },
  wsDot: {
    width: 5,
    height: 5,
    borderRadius: "50%",
    flexShrink: 0,
  },
  version: {
    fontFamily: "var(--font-display)",
    fontSize: 10,
    fontWeight: 500,
    color: "var(--text-3)",
    letterSpacing: "0.04em",
  },
  main: {
    flex: 1,
    overflow: "auto",
    padding: "0 0 48px",
  },
};
