import { createContext, useCallback, useContext, useRef, useState } from "react";

const ToastContext = createContext(null);

const COLORS = {
  success: { bg: "#065f46", border: "#10b981", icon: "✓" },
  error:   { bg: "#7f1d1d", border: "#ef4444", icon: "✕" },
  info:    { bg: "#1e3a5f", border: "#3b82f6", icon: "ℹ" },
  warning: { bg: "#78350f", border: "#f59e0b", icon: "⚠" },
};

let _nextId = 1;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const timers = useRef({});

  const dismiss = useCallback((id) => {
    clearTimeout(timers.current[id]);
    delete timers.current[id];
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback((message, { type = "info", duration = 4000 } = {}) => {
    const id = _nextId++;
    setToasts((prev) => [...prev.slice(-4), { id, message, type }]);
    if (duration > 0) {
      timers.current[id] = setTimeout(() => dismiss(id), duration);
    }
    return id;
  }, [dismiss]);

  const success = useCallback((msg, opts) => toast(msg, { type: "success", ...opts }), [toast]);
  const error   = useCallback((msg, opts) => toast(msg, { type: "error",   ...opts }), [toast]);
  const info    = useCallback((msg, opts) => toast(msg, { type: "info",    ...opts }), [toast]);
  const warning = useCallback((msg, opts) => toast(msg, { type: "warning", ...opts }), [toast]);

  return (
    <ToastContext.Provider value={{ toast, success, error, info, warning, dismiss }}>
      {children}
      <div style={styles.container} aria-live="polite">
        {toasts.map((t) => {
          const c = COLORS[t.type] || COLORS.info;
          return (
            <div key={t.id} style={{ ...styles.toast, background: c.bg, borderColor: c.border }}>
              <span style={styles.icon}>{c.icon}</span>
              <span style={styles.msg}>{t.message}</span>
              <button style={styles.close} onClick={() => dismiss(t.id)} aria-label="Dismiss">×</button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

const styles = {
  container: {
    position: "fixed", bottom: 24, right: 24, zIndex: 9999,
    display: "flex", flexDirection: "column", gap: 10, maxWidth: 360,
  },
  toast: {
    display: "flex", alignItems: "flex-start", gap: 10, padding: "12px 16px",
    borderRadius: 8, border: "1px solid", boxShadow: "0 4px 16px rgba(0,0,0,0.4)",
    animation: "slideIn 0.2s ease",
  },
  icon: { fontSize: 16, flexShrink: 0, lineHeight: "20px" },
  msg: { flex: 1, fontSize: 13, lineHeight: 1.5, color: "#e2e8f0", wordBreak: "break-word" },
  close: {
    background: "none", border: "none", color: "#94a3b8",
    cursor: "pointer", fontSize: 18, lineHeight: 1, padding: 0, flexShrink: 0,
  },
};
