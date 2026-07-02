/**
 * MonthlyReturnsHeatmap
 *
 * Renders a year × month calendar grid where each cell is colour-coded
 * by monthly return magnitude (green = positive, red = negative).
 * Data format: { "2023": { "1": 3.2, "2": -1.5, ... }, ... }
 */

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function cellColor(ret) {
  if (ret === null || ret === undefined) return { bg: "#0d1117", color: "#334155" };
  const abs = Math.min(Math.abs(ret), 12); // cap at ±12% for colour scale
  const intensity = Math.round((abs / 12) * 200);
  if (ret >= 0) {
    return { bg: `rgba(34,197,94,${0.12 + (abs / 12) * 0.55})`, color: "#86efac" };
  }
  return { bg: `rgba(239,68,68,${0.12 + (abs / 12) * 0.55})`, color: "#fca5a5" };
}

function fmt(val) {
  if (val === null || val === undefined) return "—";
  return (val > 0 ? "+" : "") + val.toFixed(1) + "%";
}

export default function MonthlyReturnsHeatmap({ monthlyReturns = {} }) {
  const years = Object.keys(monthlyReturns).sort();

  if (!years.length) {
    return <div style={styles.empty}>No monthly return data available.</div>;
  }

  return (
    <div style={styles.root}>
      <div style={styles.grid}>
        {/* Header row */}
        <div style={styles.yearCell} />
        {MONTHS.map((m) => (
          <div key={m} style={styles.headerCell}>
            {m}
          </div>
        ))}

        {/* Data rows */}
        {years.map((year) => {
          const yearData = monthlyReturns[year] || {};
          // Annual return = sum of monthly returns (approximate)
          const annualSum = Object.values(yearData).reduce((a, b) => a + b, 0);

          return (
            <>
              <div key={year + "_label"} style={styles.yearCell}>
                {year}
              </div>
              {MONTHS.map((_, monthIdx) => {
                const val = yearData[String(monthIdx + 1)];
                const { bg, color } = cellColor(val ?? null);
                return (
                  <div
                    key={`${year}_${monthIdx}`}
                    style={{ ...styles.cell, background: bg, color }}
                    title={val !== undefined ? `${MONTHS[monthIdx]} ${year}: ${fmt(val)}` : "No data"}
                  >
                    {fmt(val ?? null)}
                  </div>
                );
              })}
              <div
                key={year + "_sum"}
                style={{
                  ...styles.cell,
                  ...cellColor(annualSum),
                  fontWeight: 700,
                  marginLeft: 4,
                }}
                title={`${year} Total: ${fmt(annualSum)}`}
              >
                {fmt(annualSum)}
              </div>
            </>
          );
        })}
      </div>

      <div style={styles.legend}>
        <span style={{ color: "#86efac" }}>■ Positive</span>
        <span style={{ color: "#fca5a5", marginLeft: 16 }}>■ Negative</span>
        <span style={{ color: "#334155", marginLeft: 16 }}>— No data</span>
      </div>
    </div>
  );
}

const styles = {
  root: { overflowX: "auto" },
  grid: {
    display: "grid",
    gridTemplateColumns: "52px repeat(12, minmax(44px, 1fr)) 56px",
    gap: 3,
    minWidth: 720,
  },
  yearCell: {
    display: "flex",
    alignItems: "center",
    fontSize: 12,
    fontWeight: 700,
    color: "#475569",
    paddingRight: 6,
    justifyContent: "flex-end",
  },
  headerCell: {
    textAlign: "center",
    fontSize: 10,
    fontWeight: 600,
    color: "#475569",
    letterSpacing: "0.05em",
    padding: "4px 0",
  },
  cell: {
    textAlign: "center",
    fontSize: 10,
    fontWeight: 500,
    padding: "5px 2px",
    borderRadius: 4,
    letterSpacing: "0.02em",
    cursor: "default",
    transition: "opacity 0.15s",
  },
  legend: {
    display: "flex",
    gap: 4,
    marginTop: 10,
    fontSize: 11,
    color: "#475569",
  },
  empty: { color: "#475569", fontSize: 13, padding: "12px 0" },
};
