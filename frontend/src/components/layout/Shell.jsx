import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import WsIndicator from "../ui/WsIndicator";
import { useWebSocket } from "../../hooks/useWebSocket";

const WS_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8001")
  .replace(/^http/, "ws");

export default function Shell() {
  const { state: wsState } = useWebSocket({
    url: `${WS_BASE}/ws/v3?channels=system_metrics`,
    reconnect: true,
    reconnectAttempts: 20,
  });

  return (
    <div style={styles.root}>
      <Sidebar />
      <div style={styles.content}>
        <div style={styles.topbar}>
          <WsIndicator state={wsState} />
        </div>
        <main style={styles.main}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}

const styles = {
  root: {
    display: "flex",
    minHeight: "100vh",
    background: "#080a0f",
    fontFamily: "'Inter', 'SF Pro Text', system-ui, -apple-system, sans-serif",
    color: "#e2e8f0",
  },
  content: { flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" },
  topbar: {
    height: 36,
    display: "flex",
    alignItems: "center",
    justifyContent: "flex-end",
    padding: "0 20px",
    borderBottom: "1px solid #0f172a",
    flexShrink: 0,
  },
  main: {
    flex: 1,
    overflow: "auto",
    padding: "0 0 40px",
  },
};
