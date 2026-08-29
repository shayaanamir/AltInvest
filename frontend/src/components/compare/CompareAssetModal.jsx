import { useState } from "react";
import { useAsync } from "../../hooks/useAsync";
import { compareApi } from "../../services/compareApi";
import { formatAssetPrice } from "../../utils/formatters";
import AssetAvatar from "../shared/AssetAvatar";
import { IconX, IconCheck, IconSearch } from "../icons";

export default function CompareAssetModal({ initialSelection, initialSelected, onConfirm, onClose }) {
  const [selected, setSelected] = useState(() => initialSelection || initialSelected || []);
  const [search, setSearch] = useState("");
  const [tab, setTab] = useState("all");

  const { data: universeRaw, loading } = useAsync(() => compareApi.getAssetUniverse(), []);
  const universe = universeRaw || [];

  const filtered = universe.filter((a) => {
    if (tab !== "all" && a.category !== tab) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      return a.name.toLowerCase().includes(q) || a.symbol.toLowerCase().includes(q);
    }
    return true;
  });

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