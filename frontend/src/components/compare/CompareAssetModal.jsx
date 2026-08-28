import { useState, useEffect } from "react";
import { compareApi } from "../../services/compareApi";
import { formatAssetPrice } from "../../utils/formatters";
import { IconX, IconCheck, IconSearch } from "./icons";

export default function CompareAssetModal({ initialSelected = [], onClose, onConfirm }) {
  const [query, setQuery] = useState("");
  const [universe, setUniverse] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(initialSelected);

  useEffect(() => {
    compareApi.getUniverse().then((u) => {
      setUniverse(u);
      setLoading(false);
    });
  }, []);

  const filtered = query.trim()
    ? universe.filter(
        (a) =>
          a.name.toLowerCase().includes(query.toLowerCase()) ||
          a.symbol.toLowerCase().includes(query.toLowerCase())
      )
    : universe;

  const toggle = (id) => {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 4) return prev;
      return [...prev, id];
    });
  };

  const selectedAssets = selected.map((id) => universe.find((a) => a.id === id)).filter(Boolean);

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
                      × remove
                    </button>
                  </>
                ) : (
                  <span className="cmp-slot-placeholder">Slot {i + 1}</span>
                )}
              </div>
            );
          })}
        </div>

        <div className="cmp-search-box">
          <IconSearch />
          <input
            type="text"
            placeholder="Search assets and collections"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>

        <div className="cmp-asset-list">
          {loading ? (
            <div className="sv2-muted sv2-small" style={{ padding: "16px 0" }}>Loading…</div>
          ) : filtered.length === 0 ? (
            <div className="sv2-muted sv2-small" style={{ padding: "16px 0" }}>No matches.</div>
          ) : (
            filtered.map((a) => {
              const isSelected = selected.includes(a.id);
              return (
                <div
                  key={a.id}
                  className={`cmp-asset-row ${isSelected ? "selected" : ""}`}
                  onClick={() => toggle(a.id)}
                >
                  <div className="cmp-avatar" style={{ background: a.avatarColor }}>
                    {a.symbol.slice(0, 3)}
                  </div>
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

        <div className="cmp-modal-footer">
          <button className="cmp-cancel-btn" onClick={onClose}>
            Cancel
          </button>
          <button
            className="cmp-confirm-btn"
            disabled={selected.length < 2}
            onClick={() => onConfirm(selected)}
          >
            {selected.length >= 2 ? `Compare ${selected.length}` : "Compare"}
          </button>
        </div>
      </div>
    </div>
  );
}