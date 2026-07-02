const STATUS_COLORS = {
  PENDING: { bg: "#1e2a3a", text: "#60a5fa", border: "#1e40af" },
  SUBMITTED: { bg: "#1e2a3a", text: "#93c5fd", border: "#2563eb" },
  ACCEPTED: { bg: "#1e2a3a", text: "#93c5fd", border: "#2563eb" },
  PARTIALLY_FILLED: { bg: "#2a2a1a", text: "#fbbf24", border: "#d97706" },
  FILLED: { bg: "#162a1e", text: "#4ade80", border: "#16a34a" },
  CANCELLED: { bg: "#1e1e1e", text: "#9ca3af", border: "#4b5563" },
  REJECTED: { bg: "#2a1a1a", text: "#f87171", border: "#b91c1c" },
  EXPIRED: { bg: "#1e1e1e", text: "#6b7280", border: "#374151" },
};

export default function OrderStatusBadge({ status }) {
  const colors = STATUS_COLORS[status] || STATUS_COLORS.PENDING;
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: "0.04em",
        background: colors.bg,
        color: colors.text,
        border: `1px solid ${colors.border}`,
        whiteSpace: "nowrap",
      }}
    >
      {status}
    </span>
  );
}
