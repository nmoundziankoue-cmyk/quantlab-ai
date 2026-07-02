import { useState, useEffect } from "react";

const S = {
  wrap: { padding: 24, fontFamily: "monospace" },
  hdr: { fontSize: 18, fontWeight: 700, color: "#f0f6fc", marginBottom: 20 },
  section: { background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: 18, marginBottom: 14 },
  sHdr: { fontSize: 13, fontWeight: 700, color: "#48dbfb", marginBottom: 12 },
  row2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 },
  input: { background: "#161b22", border: "1px solid #30363d", borderRadius: 6, padding: "6px 10px", color: "#f0f6fc", fontSize: 12, width: "100%", boxSizing: "border-box", marginBottom: 6 },
  btn: (c="#48dbfb") => ({ background: c + "22", border: `1px solid ${c}55`, borderRadius: 6, padding: "6px 14px", color: c, fontSize: 12, cursor: "pointer", fontFamily: "monospace", marginRight: 6, marginTop: 4 }),
  table: { width: "100%", borderCollapse: "collapse", fontSize: 11 },
  th: { color: "#8b949e", textAlign: "left", padding: "4px 8px", borderBottom: "1px solid #21262d" },
  td: { padding: "5px 8px", color: "#c9d1d9", borderBottom: "1px solid #161b22" },
  listCard: (selected) => ({ background: selected ? "#1c2128" : "#0d1117", border: `1px solid ${selected ? "#48dbfb" : "#21262d"}`, borderRadius: 8, padding: "10px 14px", cursor: "pointer", marginBottom: 8 }),
};

export default function M18Watchlists() {
  const [lists, setLists] = useState([]);
  const [selected, setSelected] = useState(null);
  const [stats, setStats] = useState(null);
  const [listForm, setListForm] = useState({ name: "Tech Momentum", description: "High-conviction tech names", category: "EQUITY_LONG" });
  const [itemForm, setItemForm] = useState({ ticker: "NVDA", notes: "AI beneficiary", sector: "Technology", conviction: "8", target_price: "700", stop_loss: "550" });
  const [priceForm, setPriceForm] = useState({ ticker: "NVDA", price: "650" });
  const [priceAlerts, setPriceAlerts] = useState([]);

  const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  const refresh = () => {
    fetch("/m18/watchlists").then(r => r.json()).then(setLists).catch(() => {});
    fetch("/m18/watchlists/stats/summary").then(r => r.json()).then(setStats).catch(() => {});
  };
  useEffect(() => { refresh(); }, []);

  const loadList = async (id) => {
    const r = await fetch(`/m18/watchlists/${id}`);
    if (r.ok) setSelected(await r.json());
  };

  const createList = async () => {
    const r = await post("/m18/watchlists", listForm);
    if (r.ok) { refresh(); }
  };

  const addItem = async () => {
    if (!selected) return;
    await post(`/m18/watchlists/${selected.list_id}/items`, {
      ...itemForm, conviction: parseInt(itemForm.conviction),
      target_price: parseFloat(itemForm.target_price), stop_loss: parseFloat(itemForm.stop_loss),
    });
    loadList(selected.list_id);
  };

  const removeItem = async (ticker) => {
    if (!selected) return;
    await fetch(`/m18/watchlists/${selected.list_id}/items/${ticker}`, { method: "DELETE" });
    loadList(selected.list_id);
  };

  const updatePrice = async () => {
    if (!selected) return;
    const r = await post(`/m18/watchlists/${selected.list_id}/prices`, {
      ticker: priceForm.ticker.toUpperCase(), price: parseFloat(priceForm.price),
    });
    if (r.ok) { setPriceAlerts(await r.json()); loadList(selected.list_id); }
  };

  const deleteList = async (id) => {
    await fetch(`/m18/watchlists/${id}`, { method: "DELETE" });
    if (selected?.list_id === id) setSelected(null);
    refresh();
  };

  return (
    <div style={S.wrap}>
      <div style={S.hdr}>Watchlist System</div>

      {stats && (
        <div style={{ display: "flex", gap: 14, marginBottom: 16 }}>
          {[["Lists", stats.total_lists], ["Items", stats.total_items], ["Shared", stats.shared_lists], ["Alerts Fired", stats.total_alerts_fired]].map(([l, v]) => (
            <div key={l} style={{ background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "10px 16px" }}>
              <div style={{ fontSize: 10, color: "#8b949e" }}>{l}</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: "#f0f6fc" }}>{v}</div>
            </div>
          ))}
        </div>
      )}

      <div style={S.row2}>
        <div>
          <div style={S.section}>
            <div style={S.sHdr}>Create Watchlist</div>
            {[["name","Name"], ["description","Description"], ["category","Category"]].map(([f, l]) => (
              <div key={f}>
                <div style={{ fontSize: 10, color: "#8b949e", marginBottom: 2 }}>{l}</div>
                <input style={S.input} value={listForm[f]} onChange={e => setListForm(p => ({ ...p, [f]: e.target.value }))} />
              </div>
            ))}
            <button style={S.btn()} onClick={createList}>Create</button>
          </div>
          <div style={S.section}>
            <div style={S.sHdr}>My Watchlists ({lists.length})</div>
            {lists.map(wl => (
              <div key={wl.list_id} style={S.listCard(selected?.list_id === wl.list_id)} onClick={() => loadList(wl.list_id)}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ fontSize: 12, fontWeight: 700, color: "#f0f6fc" }}>{wl.name}</span>
                  <button onClick={e => { e.stopPropagation(); deleteList(wl.list_id); }} style={{ background: "none", border: "none", color: "#ff7b72", cursor: "pointer", fontSize: 11 }}>✕</button>
                </div>
                <div style={{ fontSize: 10, color: "#8b949e" }}>{wl.category} · {wl.item_count} items</div>
              </div>
            ))}
          </div>
        </div>

        <div>
          {selected && (
            <>
              <div style={S.section}>
                <div style={S.sHdr}>{selected.name} — Items</div>
                <table style={S.table}>
                  <thead><tr>{["Ticker","Sector","Conv","Target","Last Price",""].map(h => <th key={h} style={S.th}>{h}</th>)}</tr></thead>
                  <tbody>
                    {(selected.items || []).map(item => (
                      <tr key={item.item_id}>
                        <td style={{ ...S.td, color: "#58a6ff" }}>{item.ticker}</td>
                        <td style={S.td}>{item.sector}</td>
                        <td style={{ ...S.td, color: "#48dbfb" }}>{item.conviction}/10</td>
                        <td style={{ ...S.td, color: "#3fb950" }}>${item.target_price?.toFixed(2)}</td>
                        <td style={S.td}>{item.last_price > 0 ? `$${item.last_price?.toFixed(2)}` : "—"}</td>
                        <td style={S.td}><button onClick={() => removeItem(item.ticker)} style={{ background: "none", border: "none", color: "#ff7b72", cursor: "pointer", fontSize: 11 }}>✕</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div style={S.section}>
                <div style={S.sHdr}>Add Item to {selected.name}</div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                  {Object.keys(itemForm).map(f => (
                    <div key={f}>
                      <div style={{ fontSize: 10, color: "#8b949e", marginBottom: 2 }}>{f}</div>
                      <input style={{ ...S.input, marginBottom: 0 }} value={itemForm[f]} onChange={e => setItemForm(p => ({ ...p, [f]: e.target.value }))} />
                    </div>
                  ))}
                </div>
                <button style={S.btn()} onClick={addItem}>Add Item</button>
              </div>

              <div style={S.section}>
                <div style={S.sHdr}>Update Price</div>
                <div style={{ display: "flex", gap: 8 }}>
                  <input style={{ ...S.input, width: 100, marginBottom: 0 }} value={priceForm.ticker} onChange={e => setPriceForm(p => ({ ...p, ticker: e.target.value.toUpperCase() }))} placeholder="Ticker" />
                  <input style={{ ...S.input, width: 100, marginBottom: 0 }} value={priceForm.price} onChange={e => setPriceForm(p => ({ ...p, price: e.target.value }))} placeholder="Price" />
                  <button style={S.btn()} onClick={updatePrice}>Update</button>
                </div>
                {priceAlerts.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    {priceAlerts.map(a => <div key={a.alert_id} style={{ fontSize: 11, color: "#ffa657", marginBottom: 2 }}>⚡ {a.message}</div>)}
                  </div>
                )}
              </div>
            </>
          )}
          {!selected && <div style={{ ...S.section, color: "#8b949e", fontSize: 12 }}>Select a watchlist to view and manage items.</div>}
        </div>
      </div>
    </div>
  );
}
