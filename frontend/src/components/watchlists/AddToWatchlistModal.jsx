import { useMemo, useState } from "react";
import { formatAssetPrice } from "../../utils/formatters";
import { watchlistApi } from "../../services/watchlistApi";
import { useToast } from "../../errors";

/**
 * Adds assets to an existing watchlist. Each click adds straight away (POST /watchlists/{id}/items);
 * assets already on the list are marked and can't be added twice.
 *   list: { id, name, items: [{ id }] }   searchableItems: covered-universe rows
 */
export default function AddToWatchlistModal({ list, searchableItems, onClose }) {
  const toast = useToast();
  const [query, setQuery] = useState("");
  const [added, setAdded] = useState(() => new Set(list.items.map((i) => i.id)));
  const [pending, setPending] = useState(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return searchableItems;
    return searchableItems.filter((i) => i.name.toLowerCase().includes(q) || (i.symbol || "").toLowerCase().includes(q));
  }, [query, searchableItems]);

  const add = async (item) => {
    if (added.has(item.id) || pending) return;
    setPending(item.id);
    try {
      await watchlistApi.addItem(list.id, item.type === "nft" ? "nft" : "crypto", item.type === "nft" ? item.id : item.symbol);
      setAdded((prev) => new Set(prev).add(item.id));
    } catch (e) {
      toast.error(e, { title: `Couldn't add ${item.symbol || item.name}` });
    } finally {
      setPending(null);
    }
  };

  return (
    <div className="wl-modal-overlay" onClick={onClose}>
      <div className="wl-modal" role="dialog" aria-modal="true" aria-label={`Add to ${list.name}`} onClick={(e) => e.stopPropagation()}>
        <div className="wl-modal-head">
          <h2>Add to {list.name}</h2>
          <button className="wl-modal-close" onClick={onClose} aria-label="Close">×</button>
        </div>
        <p className="wl-modal-desc">Pick assets or collections to track. Each one is added as you click it.</p>

        <input
          className="wl-modal-input"
          style={{ marginBottom: 12 }}
          placeholder="Search assets and collections"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus
        />

        <div className="wl-modal-list">
          {filtered.length === 0 ? (
            <div className="wl-modal-item-sub" style={{ padding: 12 }}>No matches.</div>
          ) : (
            filtered.map((item) => {
              const onList = added.has(item.id);
              return (
                <button
                  key={item.id}
                  type="button"
                  className={`wl-modal-item ${onList ? "selected" : ""}`}
                  onClick={() => add(item)}
                  disabled={onList || pending === item.id}
                  style={{ width: "100%", textAlign: "left", border: "none", font: "inherit", color: "inherit" }}
                >
                  <div className="wl-modal-avatar" style={{ background: item.color }}>
                    {(item.symbol || item.name).slice(0, 3).toUpperCase()}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div className="wl-modal-item-name">{item.name}</div>
                    <div className="wl-modal-item-sub">{formatAssetPrice(item.price)} · {item.subcategory}</div>
                  </div>
                  <span className="wl-modal-item-sub">{onList ? "On this list" : pending === item.id ? "Adding…" : "Add"}</span>
                </button>
              );
            })
          )}
        </div>

        <div className="wl-modal-footer">
          <button className="wl-modal-create" onClick={onClose}>Done</button>
        </div>
      </div>
    </div>
  );
}
