import { useCalendar } from "../../hooks/useMarket";

const IMP_COLORS = {
  high: "#f87171",
  medium: "#f59e0b",
  low: "#64748b",
};

const IMP_LABELS = { high: "HIGH", medium: "MED", low: "LOW" };

function fmtDate(iso) {
  try {
    const d = new Date(iso + "T00:00:00");
    return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
  } catch {
    return iso;
  }
}

function groupByDate(events) {
  const map = new Map();
  for (const ev of events) {
    if (!map.has(ev.date)) map.set(ev.date, []);
    map.get(ev.date).push(ev);
  }
  return map;
}

export default function EconomicCalendar({ daysAhead = 30 }) {
  const { data, isLoading } = useCalendar(daysAhead);

  if (isLoading) return <div style={styles.empty}>Loading calendar…</div>;
  if (!data || !data.events.length)
    return <div style={styles.empty}>No events in this window.</div>;

  const groups = groupByDate(data.events);

  return (
    <div style={styles.root}>
      <div style={styles.meta}>
        Next {daysAhead} days · {data.events.length} events
      </div>
      {[...groups.entries()].map(([date, events]) => (
        <div key={date} style={styles.dateGroup}>
          <div style={styles.dateHeader}>{fmtDate(date)}</div>
          {events.map((ev, i) => (
            <div key={i} style={styles.row}>
              <span style={styles.time}>{ev.time} ET</span>
              <span
                style={{
                  ...styles.impBadge,
                  background: IMP_COLORS[ev.importance] + "22",
                  color: IMP_COLORS[ev.importance],
                  border: `1px solid ${IMP_COLORS[ev.importance]}44`,
                }}
              >
                {IMP_LABELS[ev.importance]}
              </span>
              <span style={styles.event}>{ev.event}</span>
              {ev.forecast && (
                <span style={styles.meta2}>Forecast: {ev.forecast}</span>
              )}
              {ev.previous && (
                <span style={styles.meta2}>Prev: {ev.previous}</span>
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

const styles = {
  root: { fontSize: 13 },
  meta: { fontSize: 11, color: "#334155", marginBottom: 16, letterSpacing: "0.04em" },
  dateGroup: { marginBottom: 16 },
  dateHeader: {
    fontSize: 11,
    fontWeight: 700,
    color: "#475569",
    letterSpacing: "0.07em",
    textTransform: "uppercase",
    marginBottom: 8,
    paddingBottom: 4,
    borderBottom: "1px solid #111623",
  },
  row: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "7px 0",
    borderBottom: "1px solid #0d1117",
    flexWrap: "wrap",
  },
  time: { fontSize: 11, color: "#475569", minWidth: 60, flexShrink: 0 },
  impBadge: {
    fontSize: 10,
    fontWeight: 700,
    padding: "2px 6px",
    borderRadius: 4,
    letterSpacing: "0.05em",
    flexShrink: 0,
  },
  event: { color: "#cbd5e1", flex: 1 },
  meta2: { fontSize: 11, color: "#334155" },
  empty: { color: "#475569", fontSize: 13, padding: "12px 0" },
};
