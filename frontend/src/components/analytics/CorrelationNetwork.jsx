/**
 * CorrelationNetwork — 2D force-directed MST graph using SVG.
 *
 * Implements a simple force-directed layout (Fruchterman-Reingold style)
 * entirely in JavaScript. No Three.js dependency — keeps the bundle small.
 */
import { useEffect, useRef, useState } from "react";

const WIDTH = 500;
const HEIGHT = 380;
const PADDING = 40;
const ITERATIONS = 200;

function runForceLayout(nodes, edges) {
  const n = nodes.length;
  let pos = nodes.map((_, i) => ({
    x: PADDING + Math.random() * (WIDTH - 2 * PADDING),
    y: PADDING + Math.random() * (HEIGHT - 2 * PADDING),
  }));

  const k = Math.sqrt((WIDTH * HEIGHT) / (n + 1));
  const repulsionK2 = k * k;
  const attractionK = 1 / k;

  for (let iter = 0; iter < ITERATIONS; iter++) {
    const temp = Math.max(1, (ITERATIONS - iter) / ITERATIONS) * 30;
    const disp = Array.from({ length: n }, () => ({ dx: 0, dy: 0 }));

    // Repulsion
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const dx = pos[i].x - pos[j].x;
        const dy = pos[i].y - pos[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
        const f = repulsionK2 / dist;
        disp[i].dx += (dx / dist) * f;
        disp[i].dy += (dy / dist) * f;
        disp[j].dx -= (dx / dist) * f;
        disp[j].dy -= (dy / dist) * f;
      }
    }

    // Attraction along MST edges
    edges.forEach(({ si, ti }) => {
      const dx = pos[si].x - pos[ti].x;
      const dy = pos[si].y - pos[ti].y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
      const f = dist * attractionK;
      disp[si].dx -= (dx / dist) * f;
      disp[si].dy -= (dy / dist) * f;
      disp[ti].dx += (dx / dist) * f;
      disp[ti].dy += (dy / dist) * f;
    });

    // Apply + clamp
    for (let i = 0; i < n; i++) {
      const mag = Math.sqrt(disp[i].dx ** 2 + disp[i].dy ** 2) || 0.01;
      const scale = Math.min(mag, temp) / mag;
      pos[i].x = Math.max(PADDING, Math.min(WIDTH - PADDING, pos[i].x + disp[i].dx * scale));
      pos[i].y = Math.max(PADDING, Math.min(HEIGHT - PADDING, pos[i].y + disp[i].dy * scale));
    }
  }
  return pos;
}

export default function CorrelationNetwork({ mstData }) {
  const [positions, setPositions] = useState(null);

  useEffect(() => {
    if (!mstData || !mstData.nodes || mstData.nodes.length === 0) return;

    const nodeIndex = {};
    mstData.nodes.forEach((n, i) => { nodeIndex[n.id] = i; });

    const edgesIndexed = mstData.edges.map((e) => ({
      ...e,
      si: nodeIndex[e.source],
      ti: nodeIndex[e.target],
    }));

    const pos = runForceLayout(mstData.nodes, edgesIndexed);
    setPositions({ pos, edgesIndexed, nodeIndex });
  }, [mstData]);

  if (!mstData || !mstData.nodes || mstData.nodes.length === 0) {
    return <div style={styles.empty}>No MST data available.</div>;
  }

  if (!positions) {
    return <div style={styles.empty}>Computing layout…</div>;
  }

  const { pos, edgesIndexed } = positions;
  const maxDeg = Math.max(...mstData.nodes.map((n) => n.degree), 1);

  function corrColor(corr) {
    if (corr >= 0.7) return "#f87171";
    if (corr >= 0.3) return "#f97316";
    if (corr >= 0) return "#94a3b8";
    return "#4ade80";
  }

  return (
    <div>
      <div style={styles.title}>Minimum Spanning Tree — Correlation Network</div>
      <svg width={WIDTH} height={HEIGHT} style={{ display: "block" }}>
        {/* Edges */}
        {edgesIndexed.map((e, i) => {
          const x1 = pos[e.si].x;
          const y1 = pos[e.si].y;
          const x2 = pos[e.ti].x;
          const y2 = pos[e.ti].y;
          return (
            <line
              key={i}
              x1={x1} y1={y1} x2={x2} y2={y2}
              stroke={corrColor(e.correlation)}
              strokeWidth={Math.max(0.5, 2.5 - e.distance * 3)}
              strokeOpacity={0.7}
            />
          );
        })}

        {/* Nodes */}
        {mstData.nodes.map((node, i) => {
          const r = 10 + (node.degree / maxDeg) * 8;
          return (
            <g key={node.id}>
              <circle
                cx={pos[i].x}
                cy={pos[i].y}
                r={r}
                fill="#1e3a5f"
                stroke="#2563eb"
                strokeWidth={1.5}
              />
              <text
                x={pos[i].x}
                y={pos[i].y + 4}
                textAnchor="middle"
                fill="#e2e8f0"
                fontSize={10}
                fontWeight={700}
              >
                {node.id.length > 4 ? node.id.slice(0, 4) : node.id}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div style={styles.legend}>
        {[
          { label: "High corr (≥0.7)", color: "#f87171" },
          { label: "Moderate", color: "#f97316" },
          { label: "Low", color: "#94a3b8" },
          { label: "Negative", color: "#4ade80" },
        ].map((l) => (
          <div key={l.label} style={styles.legendItem}>
            <div style={{ width: 12, height: 3, background: l.color, borderRadius: 2 }} />
            <span style={styles.legendLabel}>{l.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles = {
  title: { fontSize: 11, fontWeight: 700, color: "#475569", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 10 },
  empty: { color: "#334155", fontSize: 13, padding: "12px 0" },
  legend: { display: "flex", gap: 16, flexWrap: "wrap", marginTop: 8 },
  legendItem: { display: "flex", alignItems: "center", gap: 5 },
  legendLabel: { fontSize: 10, color: "#64748b" },
};
