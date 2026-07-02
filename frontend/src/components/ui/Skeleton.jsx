/**
 * Loading skeleton — animated placeholder while content loads.
 *
 * Usage:
 *   <Skeleton width={200} height={20} />
 *   <Skeleton variant="circle" size={40} />
 *   <Skeleton variant="text" lines={3} />
 */

const shimmer = `
  @keyframes shimmer {
    0%   { background-position: -400px 0; }
    100% { background-position: 400px 0; }
  }
`;

// Inject keyframes once
if (typeof document !== "undefined" && !document.getElementById("__skeleton-css")) {
  const s = document.createElement("style");
  s.id = "__skeleton-css";
  s.textContent = shimmer;
  document.head.appendChild(s);
}

const BASE = {
  background: "linear-gradient(90deg, #1e2637 25%, #2a3349 50%, #1e2637 75%)",
  backgroundSize: "800px 100%",
  animation: "shimmer 1.4s infinite linear",
  borderRadius: 4,
};

export default function Skeleton({
  variant = "rect",
  width = "100%",
  height = 16,
  size,
  lines = 1,
  gap = 10,
  style = {},
}) {
  if (variant === "circle") {
    const dim = size || height;
    return <div style={{ ...BASE, width: dim, height: dim, borderRadius: "50%", flexShrink: 0, ...style }} />;
  }

  if (variant === "text") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap, ...style }}>
        {Array.from({ length: lines }, (_, i) => (
          <div key={i} style={{ ...BASE, width: i === lines - 1 && lines > 1 ? "65%" : width, height }} />
        ))}
      </div>
    );
  }

  return <div style={{ ...BASE, width, height, ...style }} />;
}

export function SkeletonCard({ rows = 3, style = {} }) {
  return (
    <div style={{ background: "#111827", border: "1px solid #1e293b", borderRadius: 10, padding: "20px 24px", ...style }}>
      <Skeleton height={18} width="55%" style={{ marginBottom: 16 }} />
      <Skeleton variant="text" lines={rows} height={14} />
    </div>
  );
}
