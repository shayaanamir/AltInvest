import { useEffect, useState } from "react";
import { useAsync } from "../../hooks/useAsync";
import { watchlistApi } from "../../services/watchlistApi";
import { ErrorState, useToast } from "../../errors";
import "../portfolio/addHoldingModal.css";

/**
 * Choose which of the user's watchlists an asset is on.
 *   item: { type: "crypto" | "nft", id: symbol-or-slug, name }
 * Ticking a list adds the asset to it, unticking removes it; each change is saved straight away.
 * A new list can be created inline. Nothing is assumed: if the user has no lists, they make one here.
 */
export default function WatchlistPickerModal({ item, onClose }) {
  const toast = useToast();
  const { data: lists, loading, error, refetch, setData } = useAsync(() => watchlistApi.getInitialListsAsync(), []);
  const [busyId, setBusyId] = useState(null);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const has = (list) => list.items.some((i) => i.id === item.id);

  const toggle = async (list) => {
    setBusyId(list.id);
    try {
      if (has(list)) {
        await watchlistApi.removeItem(list.id, item.id);
        setData((prev) => prev.map((l) => (l.id === list.id ? { ...l, items: l.items.filter((i) => i.id !== item.id) } : l)));
      } else {
        await watchlistApi.addItem(list.id, item.type, item.id);
        setData((prev) => prev.map((l) => (l.id === list.id ? { ...l, items: [...l.items, { id: item.id }] } : l)));
      }
    } catch (e) {
      toast.error(e, { title: has(list) ? `Couldn't remove ${item.name} from ${list.name}` : `Couldn't add ${item.name} to ${list.name}` });
    } finally {
      setBusyId(null);
    }
  };

  const createList = async (e) => {
    e.preventDefault();
    const name = newName.trim();
    if (!name) return;
    setCreating(true);
    try {
      const { id } = await watchlistApi.createList(name);
      try {
        await watchlistApi.addItem(id, item.type, item.id);
      } catch (err) {
        toast.error(err, { title: `"${name}" was created but ${item.name} wasn't added` });
      }
      setNewName("");
      refetch();
    } catch (err) {
      toast.error(err, { title: "Couldn't create the watchlist" });
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="ahm-overlay" onClick={onClose}>
      <div className="ahm" role="dialog" aria-modal="true" aria-label={`Watchlists for ${item.name}`} onClick={(e) => e.stopPropagation()}>
        <div className="ahm-head">
          <h2>Watchlists</h2>
          <button type="button" className="ahm-close" aria-label="Close" onClick={onClose}>×</button>
        </div>
        <p className="ahm-desc">Choose the lists that should include <strong>{item.name}</strong>.</p>

        <div className="ahm-list" style={{ maxHeight: 220 }}>
          {error ? (
            <ErrorState error={error} onRetry={refetch} title="Couldn't load your watchlists" />
          ) : loading && !lists ? (
            <div className="ahm-empty">Loading…</div>
          ) : !lists || lists.length === 0 ? (
            <div className="ahm-empty">You don't have a watchlist yet. Create one below.</div>
          ) : (
            lists.map((l) => (
              <label key={l.id} className="ahm-item" style={{ cursor: busyId === l.id ? "wait" : "pointer" }}>
                <input type="checkbox" checked={has(l)} disabled={busyId === l.id} onChange={() => toggle(l)} />
                <span className="ahm-item-main">
                  <span className="ahm-item-name">{l.name}</span>
                  <span className="ahm-item-sub">{l.items.length} item{l.items.length === 1 ? "" : "s"}</span>
                </span>
              </label>
            ))
          )}
        </div>

        <form onSubmit={createList}>
          <label className="ahm-label">New watchlist</label>
          <div style={{ display: "flex", gap: 8 }}>
            <input className="ahm-input" placeholder={`e.g. Considering`} value={newName} onChange={(e) => setNewName(e.target.value)} />
            <button type="submit" className="ahm-submit" disabled={creating || !newName.trim()}>{creating ? "…" : "Create"}</button>
          </div>
        </form>

        <div className="ahm-footer">
          <button type="button" className="ahm-submit" onClick={onClose}>Done</button>
        </div>
      </div>
    </div>
  );
}
