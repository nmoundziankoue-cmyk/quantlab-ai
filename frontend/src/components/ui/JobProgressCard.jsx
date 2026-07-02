/**
 * JobProgressCard — displays a background job with progress bar and status.
 *
 * Props:
 *   job: { id, job_type, status, progress_pct, error_message, enqueued_at }
 *   onRetry?: (jobId) => void
 *   onDismiss?: (jobId) => void
 */

const STATUS_COLOR = {
  PENDING:   "#f59e0b",
  RUNNING:   "#3b82f6",
  COMPLETED: "#10b981",
  FAILED:    "#ef4444",
};

const STATUS_LABEL = {
  PENDING:   "Pending",
  RUNNING:   "Running",
  COMPLETED: "Completed",
  FAILED:    "Failed",
};

function ProgressBar({ pct, status }) {
  const color = STATUS_COLOR[status] || "#6b7280";
  const width = Math.min(100, Math.max(0, pct ?? 0));
  return (
    <div style={styles.track}>
      <div
        style={{
          ...styles.fill,
          width: `${width}%`,
          background: color,
          transition: "width 0.4s ease",
          ...(status === "RUNNING" ? styles.running : {}),
        }}
      />
    </div>
  );
}

export default function JobProgressCard({ job, onRetry, onDismiss }) {
  if (!job) return null;
  const { id, job_type, status, progress_pct, error_message, enqueued_at } = job;
  const color = STATUS_COLOR[status] || "#6b7280";

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <div style={styles.meta}>
          <span style={styles.type}>{job_type?.replace(/_/g, " ")}</span>
          <span style={{ ...styles.badge, color, borderColor: color }}>{STATUS_LABEL[status] || status}</span>
        </div>
        <div style={styles.actions}>
          {status === "FAILED" && onRetry && (
            <button style={styles.btn} onClick={() => onRetry(id)}>Retry</button>
          )}
          {onDismiss && (
            <button style={{ ...styles.btn, ...styles.btnGhost }} onClick={() => onDismiss(id)}>×</button>
          )}
        </div>
      </div>
      {(status === "RUNNING" || status === "PENDING") && (
        <ProgressBar pct={progress_pct} status={status} />
      )}
      {status === "RUNNING" && progress_pct != null && (
        <span style={styles.pct}>{Math.round(progress_pct)}%</span>
      )}
      {status === "FAILED" && error_message && (
        <p style={styles.error}>{error_message}</p>
      )}
      {enqueued_at && (
        <span style={styles.time}>{new Date(enqueued_at).toLocaleTimeString()}</span>
      )}
    </div>
  );
}

const styles = {
  card: {
    background: "#111827",
    border: "1px solid #1e293b",
    borderRadius: 8,
    padding: "12px 16px",
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center" },
  meta: { display: "flex", alignItems: "center", gap: 8 },
  type: { color: "#e2e8f0", fontSize: 13, fontWeight: 500, textTransform: "capitalize" },
  badge: {
    fontSize: 10, fontWeight: 600, border: "1px solid", borderRadius: 4,
    padding: "1px 6px", letterSpacing: "0.05em", textTransform: "uppercase",
  },
  actions: { display: "flex", gap: 6 },
  btn: {
    background: "#1e293b", color: "#94a3b8", border: "1px solid #334155",
    borderRadius: 4, padding: "3px 10px", cursor: "pointer", fontSize: 12,
  },
  btnGhost: { background: "none", border: "none", fontSize: 16, padding: "0 4px" },
  track: { height: 4, background: "#1e293b", borderRadius: 2, overflow: "hidden" },
  fill: { height: "100%", borderRadius: 2 },
  running: { animation: "jobPulse 2s ease-in-out infinite" },
  pct: { color: "#64748b", fontSize: 11 },
  error: { color: "#f87171", fontSize: 12, margin: 0, lineHeight: 1.5 },
  time: { color: "#475569", fontSize: 11 },
};

// Inject keyframes
if (typeof document !== "undefined" && !document.getElementById("__job-css")) {
  const s = document.createElement("style");
  s.id = "__job-css";
  s.textContent = `@keyframes jobPulse { 0%,100% { opacity: 1; } 50% { opacity: 0.6; } }`;
  document.head.appendChild(s);
}
