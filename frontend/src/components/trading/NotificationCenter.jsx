import { useEffect } from "react";
import useTradingStore from "../../store/useTradingStore";

const TYPE_COLORS = {
  success: { bg: "#162a1e", border: "#16a34a", text: "#4ade80", label: "SUCCESS" },
  error: { bg: "#2a1a1a", border: "#b91c1c", text: "#f87171", label: "ERROR" },
  warning: { bg: "#2a2a1a", border: "#d97706", text: "#fbbf24", label: "WARNING" },
  info: { bg: "#1e2a3a", border: "#2563eb", text: "#60a5fa", label: "INFO" },
};

function NotificationItem({ notification, onDismiss }) {
  const colors = TYPE_COLORS[notification.type] || TYPE_COLORS.info;

  useEffect(() => {
    if (notification.autoClose !== false) {
      const timer = setTimeout(() => onDismiss(notification.id), notification.duration || 5000);
      return () => clearTimeout(timer);
    }
  }, [notification.id, notification.autoClose, notification.duration, onDismiss]);

  return (
    <div
      style={{
        background: colors.bg,
        border: `1px solid ${colors.border}`,
        borderRadius: 6,
        padding: "10px 14px",
        marginBottom: 8,
        display: "flex",
        alignItems: "flex-start",
        gap: 10,
        boxShadow: "0 4px 12px rgba(0,0,0,0.4)",
        maxWidth: 340,
        animation: "slideIn 0.15s ease-out",
      }}
    >
      <span
        style={{
          fontSize: 10,
          fontWeight: 700,
          letterSpacing: "0.06em",
          color: colors.text,
          flexShrink: 0,
          marginTop: 1,
          background: `${colors.border}22`,
          padding: "1px 6px",
          borderRadius: 3,
        }}
      >
        {colors.label}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        {notification.title && (
          <div style={{ fontSize: 12, fontWeight: 600, color: "#e2e8f0", marginBottom: 2 }}>
            {notification.title}
          </div>
        )}
        <div style={{ fontSize: 12, color: "#94a3b8", lineHeight: 1.4 }}>{notification.message}</div>
      </div>
      <button
        onClick={() => onDismiss(notification.id)}
        style={{
          background: "none",
          border: "none",
          color: "#475569",
          cursor: "pointer",
          fontSize: 14,
          lineHeight: 1,
          padding: 0,
          flexShrink: 0,
        }}
      >
        ×
      </button>
    </div>
  );
}

export default function NotificationCenter() {
  const notifications = useTradingStore((s) => s.notifications);
  const dismissNotification = useTradingStore((s) => s.dismissNotification);

  if (notifications.length === 0) return null;

  return (
    <div
      style={{
        position: "fixed",
        bottom: 24,
        right: 24,
        zIndex: 9999,
        display: "flex",
        flexDirection: "column",
        pointerEvents: "none",
      }}
    >
      <style>{`@keyframes slideIn { from { opacity: 0; transform: translateX(20px); } to { opacity: 1; transform: none; } }`}</style>
      {notifications.slice(0, 5).map((n) => (
        <div key={n.id} style={{ pointerEvents: "auto" }}>
          <NotificationItem notification={n} onDismiss={dismissNotification} />
        </div>
      ))}
    </div>
  );
}
