import { useState, useEffect, useMemo } from "react";
import { sentimentApi, WATCHLIST } from "../../services/sentimentApi";
import { IconStar, IconArrowUpRight, IconArrowDownRight, IconArrowRight, IconListView, IconGrid2, IconGrid3 } from "./icons";

const CATEGORY_TABS = [
  { key: "crypto", label: "Crypto" },
  { key: "nft", label: "NFTs" },
  { key: "all", label: "Everything" },
  { key: "tokenized", label: "Tokenized soon", disabled: true },
];

const SUBCATEGORIES = ["All", "Layer 1", "Layer 2", "DeFi", "Infrastructure", "Stablecoin-adjacent", "Meme/Community"];

function barColor(score, colors) {
  if (score == null) return colors.border;
  if (score >= 58) return colors.green;
  if (score >= 45) return colors.accent;
  return colors.red;
}

export default function AssetSentimentList({ colors, onSelectAsset }) {
  const [tab, setTab] = useState("crypto");
  const [subcat, setSubcat] = useState("All");
  const [watchlistOnly, setWatchlistOnly] = useState(false);
  const [view, setView] = useState("list");
  const [favorites, setFavorites] = useState([]);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    sentimentApi.getAssetList(tab === "tokenized" ? "crypto" : tab).then((r) => {
      setRows(r);
      setLoading(false);
    }).catch(console.error);
  }, [tab]);

  const filtered = useMemo(() => {
    let r = rows;
    if (subcat !== "All") r = r.filter((x) => x.subcategory === subcat);
    if (watchlistOnly) r = r.filter((x) => WATCHLIST.includes(x.assetId));
    return r;
  }, [rows, subcat, watchlistOnly]);

  const toggleFavorite = (id) => setFavorites((f) => (f.includes(id) ? f.filter((x) => x !== id) : [...f, id]));

  const gridCols = view === "list" ? "1fr" : view === "grid2" ? "1fr 1fr" : "1fr 1fr 1fr";

  return (
    <div className="sv2-card sv2-card-pad">
      <div className="sv2-flex-between" style={{ alignItems: "flex-start" }}>
        <div>
          <div className="sv2-card-title">What stands out</div>
          <div className="sv2-card-sub">Sorted by how positive the read is right now.</div>
        </div>
        <div className="sv2-icon-toggle">
          <button className={view === "list" ? "active" : ""} onClick={() => setView("list")} title="List view"><IconListView /></button>
          <button className={view === "grid2" ? "active" : ""} onClick={() => setView("grid2")} title="Compact view"><IconGrid2 /></button>
          <button className={view === "grid3" ? "active" : ""} onClick={() => setView("grid3")} title="Dense view"><IconGrid3 /></button>
        </div>
      </div>

      <div className="sv2-flex-between sv2-mt-16" style={{ flexWrap: "wrap", gap: 10 }}>
        <div className="sv2-chip-row">
          {CATEGORY_TABS.map((c) => (
            <button
              key={c.key}
              className={`sv2-chip ${tab === c.key ? "active" : ""} ${c.disabled ? "disabled" : ""}`}
              disabled={c.disabled}
              onClick={() => !c.disabled && setTab(c.key)}
            >
              {c.label}
            </button>
          ))}
        </div>
        <label className="sv2-checkbox-row">
          <input type="checkbox" checked={watchlistOnly} onChange={(e) => setWatchlistOnly(e.target.checked)} />
          Only my watchlist
        </label>
      </div>

      <div className="sv2-chip-row sv2-mt-12">
        {SUBCATEGORIES.map((c) => (
          <button key={c} className={`sv2-chip ${subcat === c ? "active" : ""}`} onClick={() => setSubcat(c)}>
            {c}
          </button>
        ))}
      </div>

      <div className="sv2-mt-16" style={{ display: "grid", gridTemplateColumns: gridCols, gap: 8 }}>
        {loading ? (
          <div className="sv2-muted sv2-small" style={{ padding: "24px 0" }}>Loading assets…</div>
        ) : filtered.length === 0 ? (
          <div className="sv2-muted sv2-small" style={{ padding: "24px 0" }}>No assets match this filter yet.</div>
        ) : (
          filtered.map((row) => {
            const covered = row.score != null;
            const positive = row.changePct >= 0;
            return (
              <div
                key={row.assetId}
                className={`sv2-asset-row ${covered ? "" : "not-covered"}`}
                onClick={() => covered && onSelectAsset(row.assetId)}
              >
                <div>
                  <div className="sv2-asset-name">
                    {row.name}
                    {row.held && <span className="sv2-tag-held">Held</span>}
                  </div>
                  <div className="sv2-asset-sub">{row.subcategory}</div>
                </div>

                <div className="sv2-flex sv2-gap-10" style={{ alignItems: "center" }}>
                  <span className="sv2-score-num" style={{ color: covered ? barColor(row.score, colors) : colors.textMute }}>
                    {covered ? row.score : ""}
                  </span>
                  <div className="sv2-bar-track">
                    <div className="sv2-bar-fill" style={{ width: `${row.score ?? 0}%`, background: barColor(row.score, colors) }} />
                  </div>
                  <span className="sv2-bar-label">{row.readLabel}</span>
                </div>

                <div className="sv2-flex sv2-gap-10" style={{ justifySelf: "end", alignItems: "center" }}>
                  {covered ? positive ? <IconArrowUpRight /> : <IconArrowDownRight /> : <IconArrowRight />}
                  <span className={`sv2-change ${row.changePct > 0 ? "positive" : row.changePct < 0 ? "negative" : ""}`}>
                    {row.changePct >= 0 ? "+" : ""}{row.changePct.toFixed(2)}%
                  </span>
                  <button
                    className={`sv2-star-btn ${favorites.includes(row.assetId) ? "active" : ""}`}
                    onClick={(e) => { e.stopPropagation(); toggleFavorite(row.assetId); }}
                  >
                    <IconStar filled={favorites.includes(row.assetId)} />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}