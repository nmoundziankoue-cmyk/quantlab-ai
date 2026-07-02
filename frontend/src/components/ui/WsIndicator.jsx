/**
 * WebSocket connection status indicator pill.
 *
 * Reads from the zustand auth store's WebSocket state (if provided),
 * or accepts an explicit `state` prop.
 *
 * States: "connecting" | "open" | "closed" | "error"
 */

const STATE_CONFIG = {
  open:       { label: "Live",        color: "#10b981", dot: "#22c55e" },
  connecting: { label: "Connecting",  color: "#f59e0b", dot: "#fbbf24" },
  closed:     { label: "Disconnected",color: "#6b7280", dot: "#9ca3af" },
  error:      { label: "WS Error",    color: "#ef4444", dot: "#f87171" },
};

export default function WsIndicator({ state = "closed", compact = false }) {
  const cfg = STATE_CONFIG[state] || STATE_CONFIG.closed;

  return (
    <div
      title={`WebSocket: ${cfg.label}`}
      style={{ display: "inline-flex", alignItems: "center", gap: 6, ...styles.pill }}
    >
      <span
        style={{
          width: 7, height: 7, borderRadius: "50%",
          background: cfg.dot,
          ...(state === "open" ? styles.pulse : {}),
          boxShadow: state === "open" ? `0 0 6px ${cfg.dot}` : "none",
        }}
      />
      {!compact && <span style={{ ...styles.label, color: cfg.color }}>{cfg.label}</span>}
    </div>
  );
}

const styles = {
  pill: {
    background: "#0f172a",
    border: "1px solid #1e293b",
    borderRadius: 20,
    padding: "3px 10px 3px 6px",
    fontSize: 11,
    fontWeight: 500,
    letterSpacing: "0.02em",
    userSelect: "none",
  },
  label: { lineHeight: 1 },
  pulse: {
    animation: "wsPulse 1.8s ease-in-out infinite",
  },
};

// Inject pulse keyframes once
if (typeof document !== "undefined" && !document.getElementById("__ws-css")) {
  const s = document.createElement("style");
  s.id = "__ws-css";
  s.textContent = `@keyframes wsPulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }`;
  document.head.appendChild(s);
}
