import { useEffect, useState } from "react";
import { compareApi } from "../../services/compareApi";
import { describeError } from "../../errors";
import { formatAssetPrice } from "../../utils/formatters";
import AssetAvatar from "../shared/AssetAvatar";
import { IconX, IconCheck, IconSearch } from "../icons";

export default function CompareAssetModal({ initialSelection, initialSelected, onConfirm, onClose }) {
  const [selected, setSelected] = useState(() => initialSelection || initialSelected || []);
  const [search, setSearch] = useState("");
  const [tab, setTab] = useState("all");

  const [result, setResult] = useState(null); // { items, total } from GET /compare/candidates
  const [error, setError] = useState(null);
  const [known, setKnown] = useState({}); // id -> row, so picked slots keep their names whatever is listed

  // The server searches and ranks; typing waits a moment before asking.
  useEffect(() => {
    let cancelled = false;
    const t = setTimeout(() => {
      compareApi.searchCandidates({ q: search, category: tab, selected })
        .then((res) => {
          if (cancelled) return;
          setResult(res);
          setError(null);
          setKnown((prev) => ({ ...prev, ...Object.fromEntries(res.items.map((a) => [a.id, a])) }));
        })
        .catch((e) => !cancelled && setError(e));
    }, search ? 200 : 0);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
    // `selected` only marks rows; it doesn't change what's searched for.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, tab]);

  // Names for items picked before the dialog opened (e.g. from Discover) that aren't in the first page.
  useEffect(() => {
    const missing = selected.filter((id) => !known[id]);
    if (!missing.length) return;
    compareApi.searchCandidates({ limit: 100 })
      .then((res) => setKnown((prev) => ({ ...prev, ...Object.fromEntries(res.items.map((a) => [a.id, a])) })))
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loading = !result && !error;
  const filtered = result?.items || [];
  const maxSelectable = result?.maxSelectable ?? 4;

  const toggle = (id) => {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= maxSelectable) return prev;
      return [...prev, id];
    });
  };

  const selectedAssets = selected.map((id) => known[id] || { id, symbol: id, name: id });

  return (
    <div className="cmp-modal-overlay" onClick={onClose}>
      <div className="cmp-modal" onClick={(e) => e.stopPropagation()}>
        <div className="cmp-modal-head">
          <span className="cmp-modal-title">Compare assets</span>
          <button className="cmp-icon-btn" onClick={onClose}>
            <IconX />
          </button>
        </div>
        <p className="cmp-modal-desc">
          Pick 2 to 4 assets. Mixing crypto and NFTs is allowed — shared dimensions are
          normalised, and category-specific metrics stay separate.
        </p>

        <div className="cmp-slots">
          {[0, 1, 2, 3].map((i) => {
            const a = selectedAssets[i];
            return (
              <div key={i} className={`cmp-slot ${a ? "filled" : ""}`}>
                {a ? (
                  <>
                    <div className="cmp-slot-symbol">{a.symbol}</div>
                    <div className="cmp-slot-name">{a.name}</div>
                    <button className="cmp-slot-remove" onClick={() => toggle(a.id)}>
                      ×
                    </button>
                  </>
                ) : (
                  <span className="cmp-slot-empty">+ Slot {i + 1}</span>
                )}
              </div>
            );
          })}
        </div>

        <div className="cmp-search-row">
          <div className="cmp-search-box">
            <IconSearch />
            <input
              type="text"
              placeholder="Search by name or symbol…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className="sv2-segmented">
            <button className={tab === "all" ? "active" : ""} onClick={() => setTab("all")}>All</button>
            <button className={tab === "crypto" ? "active" : ""} onClick={() => setTab("crypto")}>Crypto</button>
            <button className={tab === "nft" ? "active" : ""} onClick={() => setTab("nft")}>NFTs</button>
          </div>
        </div>

        <div className="cmp-asset-list">
          {loading ? (
            <div className="sv2-muted sv2-small" style={{ padding: "16px 0" }}>Loading…</div>
          ) : error ? (
            <div className="sv2-muted sv2-small" style={{ padding: "16px 0" }}>Couldn't load assets. {describeError(error).message}</div>
          ) : filtered.length === 0 ? (
            <div className="sv2-muted sv2-small" style={{ padding: "16px 0" }}>{search.trim() ? `No matches for "${search.trim()}".` : "Nothing covered here yet."}</div>
          ) : (
            filtered.map((a) => {
              const isSelected = selected.includes(a.id);
              return (
                <div
                  key={a.id}
                  className={`cmp-asset-row ${isSelected ? "selected" : ""}`}
                  onClick={() => toggle(a.id)}
                >
                  <AssetAvatar symbol={a.symbol} color={a.avatarColor} size={36} />
                  <div className="cmp-asset-row-text">
                    <div className="cmp-asset-row-name">{a.name}</div>
                    <div className="cmp-asset-row-sub">
                      {a.priceLabel || formatAssetPrice(a.price)} · {a.subtitle}
                    </div>
                  </div>
                  {isSelected && (
                    <span className="cmp-check">
                      <IconCheck />
                    </span>
                  )}
                </div>
              );
            })
          )}
        </div>

        {result && result.total > filtered.length && (
          <div className="sv2-muted sv2-small" style={{ padding: "6px 2px 0" }}>
            Showing the top {filtered.length} of {result.total}. Search to narrow it down.
          </div>
        )}

        <div className="cmp-modal-footer">
          <button className="cmp-cancel-btn" onClick={onClose}>
            Cancel
          </button>
          <button
            className="cmp-confirm-btn"
            disabled={selected.length < 2}
            onClick={() => onConfirm(selected)}
          >
            Compare {selected.length}
          </button>
        </div>
      </div>
    </div>
  );
}