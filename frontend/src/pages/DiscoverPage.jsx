import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { discoverApi } from "../services/discoverApi";
import DiscoverFilters from "../components/discover/DiscoverFilters";
import DiscoverAssetCard from "../components/discover/DiscoverAssetCard";
import "../styles/discover.css";
import { ErrorState } from "../errors";
import { onWatchlistsChanged } from "../services/holdingsEvents";

function defaultFilters(config) {
  const f = config.filters;
  return {
    minAai: f.aaiScoreRange.min,
    minSentiment: f.sentimentRange.min * 100,
    maxVolatility: f.volatilityRange.max,
    minMarketCap: f.marketCapRange.min,
    sortBy: config.sortOptions[0].key,
  };
}

export default function DiscoverPage() {
  const navigate = useNavigate();
  const [config, setConfig] = useState(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const nameQuery = searchParams.get("q") || ""; // set by search results (e.g. an NFT collection)
  // ?category=nft opens on that tab (used by notification links).
  const [category, setCategory] = useState(() => (searchParams.get("category") === "nft" ? "nft" : "crypto"));
  const [showFilters, setShowFilters] = useState(true);
  const [filters, setFilters] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reloadTick, setReloadTick] = useState(0);
  const [compareIds, setCompareIds] = useState([]);

  useEffect(() => onWatchlistsChanged(() => setReloadTick((t) => t + 1)), []);

  useEffect(() => {
    discoverApi.getConfig().then((cfg) => {
      setConfig(cfg);
      setFilters(defaultFilters(cfg));
    }).catch((e) => { console.error(e); setError(e); setLoading(false); });
  }, []);

  useEffect(() => {
    if (!filters) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    discoverApi.getItems(category, filters, nameQuery)
      .then((res) => {
        if (cancelled) return;
        setItems(res);
      })
      .catch((e) => { if (!cancelled) { console.error(e); setItems([]); setError(e); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [category, filters, reloadTick, nameQuery]);

  const toggleCompare = (item) => {
    setCompareIds((prev) => {
      if (prev.includes(item.id)) return prev.filter((id) => id !== item.id);
      if (prev.length >= 4) return prev;
      return [...prev, item.id];
    });
  };

  const handleCompareNow = () => {
    if (compareIds.length < 2) return;
    navigate(`/compare?ids=${compareIds.join(",")}`, { state: { ids: compareIds } });
  };

  const activeTabConfig = config?.categoryTabs.find((t) => t.key === category);

  return (
    <div className="sv2">
      <div className="sv2-page disc-page">
        <div className="disc-header">
          <div>
            <h1 className="disc-title">Discover</h1>
            <p className="disc-sub">The full covered universe — filter it down to what's actually worth investigating.</p>
          </div>
          <button className="disc-toggle-btn" onClick={() => setShowFilters((s) => !s)}>
            {showFilters ? "Hide filters" : "Show filters"}
          </button>
        </div>

      {config && (
        <div className="disc-tabs">
          {config.categoryTabs.map((tab) => (
            <button
              key={tab.key}
              className={category === tab.key ? "active" : ""}
              disabled={tab.disabled}
              title={tab.disabled ? tab.disabledReason : undefined}
              onClick={() => !tab.disabled && setCategory(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      )}

      {activeTabConfig?.disabled ? (
        <div className="disc-comingsoon">
          <h3>{activeTabConfig.label} coverage is on the way</h3>
          <p>{activeTabConfig.disabledReason}</p>
        </div>
      ) : (
        <div className={`disc-layout ${showFilters ? "" : "no-filters"}`}>
          {showFilters && filters && (
            <DiscoverFilters
              config={config}
              filters={filters}
              onChange={setFilters}
              onReset={() => setFilters(defaultFilters(config))}
            />
          )}

          <div>
            {nameQuery && (
              <div className="disc-query-chip">
                Showing matches for &ldquo;{nameQuery}&rdquo;
                <button type="button" aria-label="Clear search" onClick={() => setSearchParams((p) => { p.delete("q"); return p; })}>×</button>
              </div>
            )}
            <div className="disc-count">
              {loading ? "Loading…" : `${items.length} asset${items.length === 1 ? "" : "s"} match your filters`}
            </div>

            {error ? (
              <ErrorState error={error} onRetry={() => setReloadTick((t) => t + 1)} variant="panel" title="Couldn't load the market universe" />
            ) : !loading && items.length === 0 ? (
              <div className="disc-empty">
                <h3>{config?.emptyState?.title}</h3>
                <p>{config?.emptyState?.subtitle}</p>
              </div>
            ) : (
              <div className="disc-grid">
                {items.map((item) => (
                  <DiscoverAssetCard
                    key={item.id}
                    item={item}
                    isComparing={compareIds.includes(item.id)}
                    onToggleCompare={toggleCompare}
                  />
                ))}
              </div>
            )}

            {compareIds.length > 0 && (
              <div className="disc-compare-bar">
                <div className="disc-compare-bar-info">
                  <span className="disc-compare-bar-count">{compareIds.length} asset{compareIds.length > 1 ? "s" : ""} selected</span>
                  <span className="disc-compare-bar-sub">(Pick 2 to 4 assets to compare)</span>
                </div>
                <div className="disc-compare-bar-actions">
                  <button type="button" className="disc-compare-clear-btn" onClick={() => setCompareIds([])}>
                    Clear
                  </button>
                  <button
                    type="button"
                    className="disc-compare-submit-btn"
                    disabled={compareIds.length < 2}
                    onClick={handleCompareNow}
                  >
                    {compareIds.length >= 2 ? "Compare Now →" : `Select ${2 - compareIds.length} more`}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  </div>
  );
}