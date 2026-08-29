import { useState, useMemo } from "react";
import { formatAssetPrice } from "../../utils/formatters";

export default function CreateWatchlistModal({ searchableItems, onCancel, onCreate }) {
  const [name, setName] = useState("");
  const [query, setQuery] = useState("");
  const [selectedIds, setSelectedIds] = useState([]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return searchableItems;
    return searchableItems.filter(
      (i) => i.name.toLowerCase().includes(q) || i.symbol.toLowerCase().includes(q)
    );
  }, [query, searchableItems]);

  const toggleSelect = (id) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const handleCreate = () => {
    if (!name.trim()) return;
    const chosen = searchableItems.filter((i) => selectedIds.includes(i.id));
    onCreate(name.trim(), chosen);
  };

  return (
    <div className="wl-modal-overlay" onClick={onCancel}>
      <div className="wl-modal" onClick={(e) => e.stopPropagation()}>
        <div className="wl-modal-head">
          <h2>Create a watchlist</h2>
          <button className="wl-modal-close" onClick={onCancel}>×</button>
        </div>
        <p className="wl-modal-desc">Watchlists track assets you don't own yet. Their context follows you across every screen.</p>

        <label className="wl-modal-label">List name</label>
        <input
          className="wl-modal-input"
          placeholder="e.g. Considering"
          value={name}
          onChange={(e) => setName(e.target.value)}
          autoFocus
        />

        <label className="wl-modal-label">Starter assets (optional)</label>
        <input
          className="wl-modal-input"
          style={{ marginBottom: 12 }}
          placeholder="Search assets and collections"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />

        <div className="wl-modal-list">
          {filtered.map((item) => (
            <div
              key={item.id}
              className={`wl-modal-item ${selectedIds.includes(item.id) ? "selected" : ""}`}
              onClick={() => toggleSelect(item.id)}
            >
              <div
                style={{
                  width: 30, height: 30, borderRadius: "50%", background: item.color,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 9.5, fontWeight: 800, color: "#fff", flexShrink: 0,
                }}
              >
                {item.symbol.slice(0, 3).toUpperCase()}
              </div>
              <div>
                <div className="wl-modal-item-name">{item.name}</div>
                <div className="wl-modal-item-sub">
                  {formatAssetPrice(item.price)} · {item.subcategory}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="wl-modal-footer">
          <button className="wl-modal-cancel" onClick={onCancel}>Cancel</button>
          <button className="wl-modal-create" disabled={!name.trim()} onClick={handleCreate}>Create watchlist</button>
        </div>
      </div>
    </div>
  );
}