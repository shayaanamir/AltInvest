import { useState, useEffect, useMemo } from "react";
import { sentimentApi, WATCHLIST } from "../../services/sentimentApi";
import { IconStar, IconArrowUpRight, IconArrowDownRight, IconArrowRight, IconListView, IconGrid2 } from "../icons";

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
  const [watchlistOnly, setWatchlistOnly] = useState(false);
  const [view, setView] = useState("list"); // "list" | "grid"
  const [favorites, setFavorites] = useState([]);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  // "all" (Everything) fetches the combined feed; "tokenized" is disabled/unreachable
  const apiScope = tab === "all" ? "all" : tab === "tokenized" ? "crypto" : tab;

  useEffect(() => {
    setLoading(true);
    sentimentApi.getAssetList(apiScope).then((r) => {
      setRows(r);
      setLoading(false);
    }).catch(console.error);
  }, [apiScope]);

  const filtered = useMemo(() => {
    let r = rows;
    if (watchlistOnly) r = r.filter((x) => WATCHLIST.includes(x.assetId));
    return r;
  }, [rows, watchlistOnly]);

  const toggleFavorite = (id) =>
    setFavorites((f) => (f.includes(id) ? f.filter((x) => x !== id) : [...f, id]));

  return (
    <div className="sv2-card sv2-card-pad">
      <div className="sv2-flex-between" style={{ alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
        <div>
          <div className="sv2-card-title">What stands out</div>
          <div className="sv2-card-sub">Sorted by how positive the read is right now.</div>
        </div>
        <div className="sv2-flex sv2-gap-16" style={{ alignItems: "center" }}>
          <label className="sv2-checkbox-row">
            <input type="checkbox" checked={watchlistOnly} onChange={(e) => setWatchlistOnly(e.target.checked)} />
            Only my watchlist
          </label>
          <div className="sv2-icon-toggle">
            <button className={view === "list" ? "active" : ""} onClick={() => setView("list")} title="List view">
              <IconListView />
            </button>
            <button className={view === "grid" ? "active" : ""} onClick={() => setView("grid")} title="Grid view">
              <IconGrid2 />
            </button>
          </div>
        </div>
      </div>

      <div className="sv2-mt-16">
        <div className="sv2-category-tabs" style={{ display: "flex", width: "100%" }}>
          {CATEGORY_TABS.map((c) => (
            <button
              key={c.key}
              style={{ flex: 1, textAlign: "center" }}
              className={`${tab === c.key ? "active" : ""} ${c.disabled ? "disabled" : ""}`}
              disabled={c.disabled}
              onClick={() => !c.disabled && setTab(c.key)}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>

      <div className={`sv2-mt-16 ${view === "grid" ? "sv2-asset-grid" : "sv2-flex-col"}`}>
        {loading ? (
          <div className="sv2-muted sv2-small" style={{ padding: "24px 0" }}>Loading assets…</div>
        ) : filtered.length === 0 ? (
          <div className="sv2-muted sv2-small" style={{ padding: "24px 0" }}>No assets match this filter yet.</div>
        ) : view === "list" ? (
          filtered.map((row) => {
            const covered = row.score != null;
            const positive = row.changePct >= 0;
            return (
              <div
                key={row.assetId}
                className={`sv2-asset-row ${covered ? "" : "not-covered"}`}
                onClick={() => covered && onSelectAsset(row.assetId)}
              >
                <div className="sv2-asset-name-col">
                  <div className="sv2-asset-name">
                    {row.name}
                    {row.held && <span className="sv2-tag-held">Held</span>}
                  </div>
                  <div className="sv2-asset-sub">{row.subcategory}</div>
                </div>

                <div className="sv2-asset-score-col">
                  <span className="sv2-score-num" style={{ color: covered ? barColor(row.score, colors) : colors.textMute }}>
                    {covered ? row.score : ""}
                  </span>
                  <div className="sv2-bar-track">
                    <div className="sv2-bar-fill" style={{ width: `${row.score ?? 0}%`, background: barColor(row.score, colors) }} />
                  </div>
                  <span className="sv2-bar-label">{row.readLabel}</span>
                </div>

                <div className="sv2-asset-change-col">
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
        ) : (
          filtered.map((row) => {
            const covered = row.score != null;
            const positive = row.changePct >= 0;
            return (
              <div
                key={row.assetId}
                className={`sv2-asset-card ${covered ? "" : "not-covered"}`}
                onClick={() => covered && onSelectAsset(row.assetId)}
              >
                <div className="sv2-flex-between" style={{ alignItems: "flex-start" }}>
                  <div>
                    <div className="sv2-asset-name">
                      {row.name}
                      {row.held && <span className="sv2-tag-held">Held</span>}
                    </div>
                    <div className="sv2-asset-sub">{row.subcategory}</div>
                  </div>
                  <button
                    className={`sv2-star-btn ${favorites.includes(row.assetId) ? "active" : ""}`}
                    onClick={(e) => { e.stopPropagation(); toggleFavorite(row.assetId); }}
                  >
                    <IconStar filled={favorites.includes(row.assetId)} />
                  </button>
                </div>

                <div className="sv2-flex sv2-gap-10 sv2-mt-12" style={{ alignItems: "center" }}>
                  <span className="sv2-score-num" style={{ color: covered ? barColor(row.score, colors) : colors.textMute }}>
                    {covered ? row.score : ""}
                  </span>
                  <div className="sv2-bar-track">
                    <div className="sv2-bar-fill" style={{ width: `${row.score ?? 0}%`, background: barColor(row.score, colors) }} />
                  </div>
                </div>

                <div className="sv2-flex-between sv2-mt-8">
                  <span className="sv2-bar-label">{row.readLabel}</span>
                  <span className={`sv2-change ${row.changePct > 0 ? "positive" : row.changePct < 0 ? "negative" : ""}`}>
                    {covered ? (row.changePct >= 0 ? "+" : "") + row.changePct.toFixed(2) + "%" : "—"}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}