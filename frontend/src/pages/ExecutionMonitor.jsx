import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";

const API = "";
const card = { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20, marginBottom: 20 };
const STATUS_COLORS = { filled: "#3fb950", open: "#58a6ff", cancelled: "#8b949e", rejected: "#f85149", pending: "#d29922" };

export default function ExecutionMonitor() {
  const qc = useQueryClient();
  const [form, setForm] = useState({ ticker: "AAPL", side: "buy", order_type: "market", quantity: "100", market_price: "175", limit_price: "" });

  const { data: orders } = useQuery({
    queryKey: ["exec-orders"],
    queryFn: () => axios.get(`${API}/execution/enhanced/orders`).then(r => r.data),
    refetchInterval: 5000,
  });

  const { data: latency } = useQuery({
    queryKey: ["exec-latency"],
    queryFn: () => axios.get(`${API}/execution/enhanced/latency`).then(r => r.data),
    refetchInterval: 10000,
  });

  const submit = useMutation({
    mutationFn: () => axios.post(`${API}/execution/enhanced/orders`, {
      ticker: form.ticker,
      side: form.side,
      order_type: form.order_type,
      quantity: +form.quantity,
      market_price: +form.market_price,
      limit_price: form.limit_price ? +form.limit_price : undefined,
    }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["exec-orders"] }),
  });

  const cancel = useMutation({
    mutationFn: (id) => axios.delete(`${API}/execution/enhanced/orders/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["exec-orders"] }),
  });

  const f = (label, key, opts = {}) => (
    <div style={{ flex: "1 1 120px" }}>
      <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>{label}</div>
      {opts.options ? (
        <select style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "7px 10px", fontSize: 13, width: "100%" }}
          value={form[key]} onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}>
          {opts.options.map(o => <option key={o} value={o}>{o}</option>)}
        </select>
      ) : (
        <input style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#e6edf3", padding: "7px 10px", fontSize: 13, width: "100%", boxSizing: "border-box" }}
          value={form[key]} onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))} />
      )}
    </div>
  );

  return (
    <div style={{ padding: 28, background: "#0d1117", minHeight: "100vh", color: "#e6edf3" }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Execution Monitor</h1>
        <p style={{ color: "#8b949e", margin: "4px 0 0", fontSize: 13 }}>Smart order routing with bracket, OCO, and trailing stop support</p>
      </div>

      {/* Latency */}
      {latency?.avg_ms && (
        <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
          {[["Avg", latency.avg_ms], ["P50", latency.p50_ms], ["P95", latency.p95_ms], ["P99", latency.p99_ms], ["Fills", latency.total_fills]].map(([k, v]) => (
            <div key={k} style={{ ...card, margin: 0, flex: "1" }}>
              <div style={{ fontSize: 11, color: "#8b949e" }}>{k} Latency</div>
              <div style={{ fontSize: 20, fontWeight: 700 }}>{typeof v === "number" ? `${v.toFixed(2)}ms` : v}</div>
            </div>
          ))}
        </div>
      )}

      {/* Order form */}
      <div style={card}>
        <div style={{ fontWeight: 600, marginBottom: 16, fontSize: 14 }}>Submit Order</div>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 14 }}>
          {f("Ticker", "ticker")}
          {f("Side", "side", { options: ["buy", "sell"] })}
          {f("Type", "order_type", { options: ["market", "limit", "stop", "bracket", "trailing_stop", "vwap", "twap", "iceberg"] })}
          {f("Quantity", "quantity")}
          {f("Market Price", "market_price")}
          {f("Limit Price", "limit_price")}
        </div>
        <button
          onClick={() => submit.mutate()}
          disabled={submit.isPending}
          style={{ background: "#238636", border: "none", borderRadius: 6, color: "#fff", padding: "10px 20px", cursor: "pointer", fontSize: 13, fontWeight: 600 }}
        >
          {submit.isPending ? "Submitting…" : "Submit Order"}
        </button>
        {submit.data && <div style={{ marginTop: 10, fontSize: 13, color: "#3fb950" }}>Order {submit.data.order_id?.slice(0, 8)}… → {submit.data.status}</div>}
      </div>

      {/* Order book */}
      <div style={card}>
        <div style={{ fontWeight: 600, marginBottom: 16, fontSize: 14 }}>Orders ({orders?.orders?.length ?? 0})</div>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead><tr style={{ borderBottom: "1px solid #30363d" }}>
            {["ID","Ticker","Side","Type","Qty","Fill Price","Status","Actions"].map(h => (
              <th key={h} style={{ textAlign: "left", padding: "6px 10px", color: "#8b949e", fontWeight: 500 }}>{h}</th>
            ))}
          </tr></thead>
          <tbody>
            {(orders?.orders ?? []).slice(0, 20).map(o => (
              <tr key={o.id} style={{ borderBottom: "1px solid #21262d" }}>
                <td style={{ padding: "8px 10px", color: "#8b949e" }}>{o.id?.slice(0, 8)}…</td>
                <td style={{ padding: "8px 10px", fontWeight: 600 }}>{o.ticker}</td>
                <td style={{ padding: "8px 10px", color: o.side === "buy" ? "#3fb950" : "#f85149" }}>{o.side}</td>
                <td style={{ padding: "8px 10px" }}>{o.order_type}</td>
                <td style={{ padding: "8px 10px" }}>{o.quantity}</td>
                <td style={{ padding: "8px 10px" }}>{o.avg_fill_price ? `$${o.avg_fill_price}` : "—"}</td>
                <td style={{ padding: "8px 10px" }}>
                  <span style={{ background: STATUS_COLORS[o.status] + "22", color: STATUS_COLORS[o.status], padding: "2px 8px", borderRadius: 12, fontSize: 11 }}>{o.status}</span>
                </td>
                <td style={{ padding: "8px 10px" }}>
                  {o.status === "open" && (
                    <button onClick={() => cancel.mutate(o.id)} style={{ background: "#4d1f1f", border: "1px solid #f85149", borderRadius: 4, color: "#f85149", padding: "2px 8px", cursor: "pointer", fontSize: 11 }}>Cancel</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
