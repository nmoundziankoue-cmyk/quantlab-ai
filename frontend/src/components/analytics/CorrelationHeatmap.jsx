/**
 * CorrelationHeatmap — SVG-based matrix heatmap.
 */
function colorForCorr(v) {
  if (v == null) return "#1e2230";
  const clamped = Math.max(-1, Math.min(1, v));
  if (clamped >= 0) {
    // White (0) → deep blue (1)
    const t = clamped;
    const r = Math.round(37 * (1 - t));
    const g = Math.round(99 * (1 - t));
    const b = Math.round(235 * (1 - t) + 235 * t);
    return `rgb(${r},${g},${b})`;
  } else {
    // White (0) → deep red (-1)
    const t = -clamped;
    const r = Math.round(220 * t + 255 * (1 - t));
    const g = Math.round(38 * t + 255 * (1 - t));
    const b = Math.round(38 * t + 255 * (1 - t));
    return `rgb(${r},${g},${b})`;
  }
}

export default function CorrelationHeatmap({ tickers, matrix }) {
  if (!tickers || !matrix) return null;

  const n = tickers.length;
  const cellSize = Math.min(48, Math.floor(560 / n));
  const labelWidth = 52;
  const totalW = labelWidth + n * cellSize;
  const totalH = labelWidth + n * cellSize;

  return (
    <div style={{ overflowX: "auto" }}>
      <svg width={totalW} height={totalH}>
        {/* Column labels */}
        {tickers.map((t, j) => (
          <text
            key={`col-${j}`}
            x={labelWidth + j * cellSize + cellSize / 2}
            y={labelWidth - 4}
            textAnchor="middle"
            fill="#94a3b8"
            fontSize={Math.min(11, cellSize * 0.28)}
            fontWeight={600}
          >
            {t.length > 5 ? t.slice(0, 5) : t}
          </text>
        ))}

        {/* Row labels + cells */}
        {matrix.map((row, i) => (
          <g key={`row-${i}`}>
            <text
              x={labelWidth - 6}
              y={labelWidth + i * cellSize + cellSize / 2 + 4}
              textAnchor="end"
              fill="#94a3b8"
              fontSize={Math.min(11, cellSize * 0.28)}
              fontWeight={600}
            >
              {tickers[i].length > 5 ? tickers[i].slice(0, 5) : tickers[i]}
            </text>
            {row.map((val, j) => (
              <g key={`cell-${i}-${j}`}>
                <rect
                  x={labelWidth + j * cellSize}
                  y={labelWidth + i * cellSize}
                  width={cellSize - 1}
                  height={cellSize - 1}
                  fill={colorForCorr(val)}
                  opacity={i === j ? 1.0 : 0.85}
                />
                {cellSize >= 32 && (
                  <text
                    x={labelWidth + j * cellSize + cellSize / 2}
                    y={labelWidth + i * cellSize + cellSize / 2 + 4}
                    textAnchor="middle"
                    fill={Math.abs(val) > 0.5 ? "#fff" : "#1e2230"}
                    fontSize={Math.min(10, cellSize * 0.22)}
                    fontWeight={600}
                  >
                    {val != null ? val.toFixed(2) : ""}
                  </text>
                )}
              </g>
            ))}
          </g>
        ))}
      </svg>

      {/* Legend */}
      <div style={styles.legend}>
        <span style={{ ...styles.legendLabel, color: "#dc2626" }}>-1.0</span>
        <svg width={120} height={12}>
          <defs>
            <linearGradient id="corrGrad" x1="0" x2="1" y1="0" y2="0">
              <stop offset="0%" stopColor="rgb(220,38,38)" />
              <stop offset="50%" stopColor="rgb(255,255,255)" />
              <stop offset="100%" stopColor="rgb(37,99,235)" />
            </linearGradient>
          </defs>
          <rect width={120} height={12} fill="url(#corrGrad)" rx={2} />
        </svg>
        <span style={{ ...styles.legendLabel, color: "#2563eb" }}>+1.0</span>
      </div>
    </div>
  );
}

const styles = {
  legend: { display: "flex", alignItems: "center", gap: 8, marginTop: 10 },
  legendLabel: { fontSize: 10, fontWeight: 700 },
};
