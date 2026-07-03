import { useState } from "react";
import { useScreenerTypes, useScreeners, useCreateScreener, useDeleteScreener, useRunScreener } from "../hooks/useScreeners";

const S = {
  page: { padding: 24, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" },
  title: { fontSize: 22, fontWeight: 700, marginBottom: 20 },
  grid: { display: "grid", gridTemplateColumns: "320px 1fr", gap: 16 },
  card: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20, marginBottom: 16 },
  cardTitle: { fontSize: 13, color: "#8b949e", fontWeight: 600, marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.05em" },
  input: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "8px 12px", color: "#e6edf3", fontSize: 13, width: "100%", outline: "none", marginBottom: 8, boxSizing: "border-box" },
  select: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "8px 12px", color: "#e6edf3", fontSize: 13, width: "100%", outline: "none", marginBottom: 8, boxSizing: "border-box" },
  btn: (color = "#238636") => ({ background: color, border: "none", borderRadius: 6, padding: "8px 14px", color: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 600, marginRight: 8 }),
  ruleRow: { display: "flex", gap: 6, marginBottom: 6, alignItems: "center" },
  table: { width: "100%", borderCollapse: "collapse" },
  th: { padding: "8px 12px", textAlign: "left", fontSize: 12, color: "#8b949e", fontWeight: 600, borderBottom: "1px solid #30363d" },
  td: { padding: "10px 12px", fontSize: 13, borderBottom: "1px solid #21262d" },
  badge: (color) => ({ background: color + "22", color, borderRadius: 4, padding: "2px 8px", fontSize: 11, fontWeight: 600 }),
};

const FIELDS = ["pe", "pb", "ps", "roe", "revenue_growth", "ebitda_margin", "dividend_yield", "beta", "market_cap", "momentum_12m"];
const OPERATORS = ["gt", "gte", "lt", "lte", "eq", "neq"];

function RuleBuilder({ rules, setRules }) {
  const addRule = () => setRules((r) => [...r, { field: "pe", operator: "lt", value: 25 }]);
  const removeRule = (i) => setRules((r) => r.filter((_, j) => j !== i));
  const updateRule = (i, key, val) => setRules((r) => r.map((rule, j) => j === i ? { ...rule, [key]: val } : rule));

  return (
    <div>
      {rules.map((rule, i) => (
        <div key={i} style={S.ruleRow}>
          <select style={{ ...S.select, marginBottom: 0, flex: 2 }} value={rule.field} onChange={(e) => updateRule(i, "field", e.target.value)}>
            {FIELDS.map((f) => <option key={f}>{f}</option>)}
          </select>
          <select style={{ ...S.select, marginBottom: 0, flex: 1 }} value={rule.operator} onChange={(e) => updateRule(i, "operator", e.target.value)}>
            {OPERATORS.map((o) => <option key={o}>{o}</option>)}
          </select>
          <input type="number" style={{ ...S.input, marginBottom: 0, flex: 1 }} value={rule.value} onChange={(e) => updateRule(i, "value", parseFloat(e.target.value))} />
          <button style={{ background: "#b91c1c", border: "none", borderRadius: 4, padding: "6px 10px", color: "#fff", cursor: "pointer", fontSize: 12 }} onClick={() => removeRule(i)}>✕</button>
        </div>
      ))}
      <button style={{ ...S.btn("#21262d"), border: "1px solid #30363d", marginTop: 4 }} onClick={addRule}>+ Add Rule</button>
    </div>
  );
}

export default function Screeners() {
  const { data: types = {} } = useScreenerTypes();
  const { data: screeners = [] } = useScreeners();
  const createScreener = useCreateScreener();
  const deleteScreener = useDeleteScreener();
  const runScreener = useRunScreener();

  const [rules, setRules] = useState([{ field: "pe", operator: "lt", value: 25 }, { field: "roe", operator: "gt", value: 0.15 }]);
  const [screenerType, setScreenerType] = useState("fundamental");
  const [screenerName, setScreenerName] = useState("");
  const [limit, setLimit] = useState(20);
  const [runResult, setRunResult] = useState(null);

  const handleRun = () => {
    runScreener.mutate({ payload: { rules, screener_type: screenerType, limit }, save: false }, { onSuccess: setRunResult });
  };

  const handleSave = () => {
    if (!screenerName.trim()) return;
    createScreener.mutate({ name: screenerName, screener_type: screenerType, rules }, { onSuccess: () => setScreenerName("") });
  };

  const typeList = Array.isArray(types) ? types : Object.keys(types);

  return (
    <div style={S.page}>
      <div style={S.title}>Equity Screener</div>
      <div style={S.grid}>
        <div>
          <div style={S.card}>
            <div style={S.cardTitle}>Screener Configuration</div>
            <select style={S.select} value={screenerType} onChange={(e) => setScreenerType(e.target.value)}>
              {typeList.map((t) => <option key={t}>{t}</option>)}
            </select>
            <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 8 }}>Rules</div>
            <RuleBuilder rules={rules} setRules={setRules} />
            <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 12 }}>
              <span style={{ fontSize: 12, color: "#8b949e" }}>Limit:</span>
              <input type="number" style={{ ...S.input, marginBottom: 0, width: 60 }} value={limit} onChange={(e) => setLimit(parseInt(e.target.value))} />
            </div>
            <div style={{ marginTop: 12 }}>
              <button style={S.btn()} onClick={handleRun} disabled={runScreener.isPending}>{runScreener.isPending ? "Running..." : "Run Screener"}</button>
            </div>
          </div>

          <div style={S.card}>
            <div style={S.cardTitle}>Save Screener</div>
            <input style={S.input} placeholder="Screener name" value={screenerName} onChange={(e) => setScreenerName(e.target.value)} />
            <button style={S.btn("#1f6feb")} onClick={handleSave}>Save</button>
          </div>

          {screeners.length > 0 && (
            <div style={S.card}>
              <div style={S.cardTitle}>Saved ({screeners.length})</div>
              {screeners.map((s) => (
                <div key={s.id} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #21262d", alignItems: "center" }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>{s.name}</div>
                    <div style={{ fontSize: 11, color: "#8b949e" }}>{s.screener_type} · {(s.rules || []).length} rules</div>
                  </div>
                  <button style={{ background: "#b91c1c", border: "none", borderRadius: 4, padding: "4px 8px", color: "#fff", cursor: "pointer", fontSize: 12 }} onClick={() => deleteScreener.mutate(s.id)}>Del</button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div>
          {runResult ? (
            <div style={S.card}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <div style={S.cardTitle}>{runResult.match_count} matches from {runResult.total_universe} universe</div>
                <span style={{ fontSize: 12, color: "#8b949e" }}>{runResult.screener_type}</span>
              </div>
              <table style={S.table}>
                <thead>
                  <tr>
                    <th style={S.th}>Rank</th>
                    <th style={S.th}>Ticker</th>
                    <th style={S.th}>Score</th>
                    {rules.map((r) => <th key={r.field} style={S.th}>{r.field}</th>)}
                    <th style={S.th}>Pass/Fail</th>
                  </tr>
                </thead>
                <tbody>
                  {(runResult.results ?? []).map((item) => (
                    <tr key={item.ticker}>
                      <td style={S.td}>{item.rank}</td>
                      <td style={{ ...S.td, fontWeight: 700, color: "#58a6ff" }}>{item.ticker}</td>
                      <td style={S.td}>{item.score.toFixed(1)}</td>
                      {rules.map((r) => <td key={r.field} style={S.td}>{item.field_values[r.field] != null ? item.field_values[r.field].toLocaleString() : "N/A"}</td>)}
                      <td style={S.td}>
                        <span style={S.badge("#3fb950")}>{item.pass_count}P</span>
                        {item.fail_count > 0 && <span style={S.badge("#f85149")}>{item.fail_count}F</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ ...S.card, textAlign: "center", padding: 60 }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>🔍</div>
              <div style={{ color: "#8b949e", fontSize: 14 }}>Configure rules and run the screener to find matching equities</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
