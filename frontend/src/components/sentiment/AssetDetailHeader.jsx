import { useState, useEffect, useMemo } from "react";
import { relativeTime } from "../../utils/dateTime";
import { formatAssetPrice } from "../../utils/formatters";
import { IconSearch, IconRefresh, IconStar, IconChevronDown } from "../icons";

export default function AssetDetailHeader({ detail, switchable, onBack, onSwitchAsset, onRefresh, refreshing, watching, onToggleWatching, watchDisabled }) {
  const [ago, setAgo] = useState(relativeTime(detail.lastUpdated));
  const [query, setQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);

  // Searches the assets this screen has sentiment for; choosing one switches the view to it.
  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    const unique = Array.from(new Map(switchable.map((s) => [s.id, s])).values());
    return unique
      .filter((s) => s.id !== detail.assetId && (s.name.toLowerCase().includes(q) || (s.symbol || "").toLowerCase().includes(q)))
      .slice(0, 6);
  }, [query, switchable, detail.assetId]);

  const choose = (id) => {
    setQuery("");
    setSearchOpen(false);
    onSwitchAsset(id);
  };

  useEffect(() => {
    setAgo(relativeTime(detail.lastUpdated));
    const id = setInterval(() => setAgo(relativeTime(detail.lastUpdated)), 5000);
    return () => clearInterval(id);
  }, [detail.lastUpdated]);

  return (
    <div className="sv2-flex-col sv2-gap-16">
      <div className="sv2-breadcrumb">
        <button onClick={onBack}>Sentiment Hub</button>
        <span>›</span>
        <span>{detail.name}</span>
      </div>

      <div className="sv2-flex-between" style={{ flexWrap: "wrap", gap: 12, alignItems: "flex-start" }}>
        <div>
          <h1 className="sv2-h1" style={{ marginTop: 0 }}>{detail.name}</h1>
          <p className="sv2-lead">What people are saying, and how strongly, for this one.</p>
        </div>
        <div className="sv2-flex sv2-gap-10" style={{ flexWrap: "wrap" }}>
          <div className="sv2-search-box" style={{ position: "relative" }}>
            <IconSearch />
            <input
              aria-label="Search assets with sentiment"
              placeholder="Search assets"
              value={query}
              onChange={(e) => { setQuery(e.target.value); setSearchOpen(true); }}
              onFocus={() => setSearchOpen(true)}
              onBlur={() => setTimeout(() => setSearchOpen(false), 120)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && matches[0]) choose(matches[0].id);
                if (e.key === "Escape") { setQuery(""); setSearchOpen(false); }
              }}
              style={{ background: "none", border: "none", outline: "none", color: "inherit", font: "inherit", width: 150 }}
            />
            {searchOpen && query.trim() && (
              <div className="tb-dropdown" style={{ position: "absolute", top: "100%", left: 0, right: 0, marginTop: 6, zIndex: 20 }}>
                {matches.length === 0 ? (
                  <div className="tb-dropdown-empty">No covered asset matches.</div>
                ) : (
                  matches.map((m) => (
                    <button key={m.id} type="button" className="tb-dropdown-footer-btn" style={{ textAlign: "left" }} onMouseDown={() => choose(m.id)}>
                      {m.name} <span className="sv2-mute2">{m.symbol}</span>
                    </button>
                  ))
                )}
              </div>
            )}
          </div>
          <span className="sv2-badge-pill">● Updated {ago}</span>
          <button className="sv2-refresh-btn" onClick={onRefresh} disabled={refreshing}>
            <IconRefresh /> {refreshing ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>

      <div className="sv2-flex-between sv2-card sv2-card-pad-sm" style={{ flexWrap: "wrap", gap: 12 }}>
        <div className="sv2-flex sv2-gap-12" style={{ alignItems: "center" }}>
          <button className="sv2-btn-outline" style={{ width: "auto", flex: "none" }} onClick={onBack}>← Overview</button>
          <span className="sv2-ticker-chip">{detail.symbol}</span>
          <div>
            <div className="sv2-bold" style={{ fontSize: 14 }}>{detail.name}</div>
            <div className="sv2-tiny sv2-mute2">{detail.category === "nft" ? "NFT" : "Crypto"} · {detail.subcategory}</div>
          </div>
          <span className="sv2-asset-price" style={{ marginLeft: 12 }}>
            {detail.price != null ? formatAssetPrice(detail.price) : "—"}
          </span>
          <span className={`sv2-small sv2-bold`} style={{ color: (detail.priceChangePct ?? 0) >= 0 ? "var(--sv2-green)" : "var(--sv2-red)" }}>
            {detail.priceChangePct != null
              ? `${detail.priceChangePct >= 0 ? "↗" : "↘"} ${Math.abs(Number(detail.priceChangePct)).toFixed(2)}% price, 24h`
              : "—"}
          </span>
        </div>

        <div className="sv2-flex sv2-gap-10" style={{ alignItems: "center" }}>
          <div style={{ position: "relative" }}>
            <select
              className="sv2-select"
              value={detail.assetId}
              onChange={(e) => onSwitchAsset(e.target.value)}
              style={{ paddingRight: 26 }}
            >
              {Array.from(new Map(switchable.map((s) => [s.id, s])).values()).map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
          <button className={`sv2-btn-outline ${watching ? "active" : ""}`} style={{ width: "auto" }} onClick={onToggleWatching} disabled={watchDisabled}>
            <IconStar size={13} filled={watching} /> Watching
          </button>
        </div>
      </div>
    </div>
  );
}