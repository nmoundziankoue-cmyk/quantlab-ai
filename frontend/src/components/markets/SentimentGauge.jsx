/**
 * SVG arc gauge that maps a sentiment score [-1, 1] to a coloured needle.
 * No external library needed — pure SVG.
 */
export default function SentimentGauge({ score = 0, label = "neutral", signal = "Hold", size = 160 }) {
  const cx = size / 2;
  const cy = size * 0.6;
  const r = size * 0.38;
  const strokeW = size * 0.07;

  // Arc from 180° (left, bearish) to 0° (right, bullish)
  // score=-1 → angle=180°, score=0 → angle=90°, score=+1 → angle=0°
  const angleDeg = 180 - ((score + 1) / 2) * 180;
  const angleRad = (angleDeg * Math.PI) / 180;
  const needleX = cx + r * Math.cos(angleRad);
  const needleY = cy - r * Math.sin(angleRad);

  const gaugeColor =
    score > 0.15 ? "#4ade80" : score < -0.15 ? "#f87171" : "#f59e0b";

  // Arc segments: red → amber → green
  const segments = [
    { start: 180, end: 120, color: "#f87171" },  // bearish
    { start: 120, end: 60, color: "#f59e0b" },   // neutral
    { start: 60, end: 0, color: "#4ade80" },     // bullish
  ];

  function arcPath(startDeg, endDeg, radius) {
    const s = ((180 - startDeg) * Math.PI) / 180;
    const e = ((180 - endDeg) * Math.PI) / 180;
    const x1 = cx + radius * Math.cos(s);
    const y1 = cy - radius * Math.sin(s);
    const x2 = cx + radius * Math.cos(e);
    const y2 = cy - radius * Math.sin(e);
    return `M ${x1} ${y1} A ${radius} ${radius} 0 0 1 ${x2} ${y2}`;
  }

  return (
    <div style={styles.wrapper}>
      <svg width={size} height={size * 0.65} viewBox={`0 0 ${size} ${size * 0.65}`}>
        {/* Track arcs */}
        {segments.map((seg, i) => (
          <path
            key={i}
            d={arcPath(seg.start, seg.end, r)}
            fill="none"
            stroke={seg.color}
            strokeWidth={strokeW}
            strokeLinecap="round"
            opacity={0.25}
          />
        ))}

        {/* Active needle arc (from start to current angle) */}
        {score !== 0 && (
          <path
            d={arcPath(
              180,
              score >= 0 ? 90 - (score * 90) : 90 + Math.abs(score) * 90,
              r
            )}
            fill="none"
            stroke={gaugeColor}
            strokeWidth={strokeW * 0.7}
            strokeLinecap="round"
            opacity={0.9}
          />
        )}

        {/* Needle */}
        <line
          x1={cx}
          y1={cy}
          x2={needleX}
          y2={needleY}
          stroke="#e2e8f0"
          strokeWidth={2}
          strokeLinecap="round"
        />
        <circle cx={cx} cy={cy} r={strokeW * 0.4} fill="#e2e8f0" />
      </svg>

      <div style={{ ...styles.signal, color: gaugeColor }}>{signal}</div>
      <div style={styles.label}>{label}</div>
      <div style={styles.score}>
        Score: {score >= 0 ? "+" : ""}{score.toFixed(2)}
      </div>
    </div>
  );
}

const styles = {
  wrapper: { textAlign: "center" },
  signal: { fontSize: 18, fontWeight: 700, marginTop: 4 },
  label: { fontSize: 12, color: "#64748b", marginTop: 2, textTransform: "capitalize" },
  score: { fontSize: 11, color: "#334155", marginTop: 2 },
};
