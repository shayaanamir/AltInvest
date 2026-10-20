import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { discoverApi, defaultFilters } from "../services/discoverApi";
import discoverConfig from "../content/discover.json";
import DiscoverFilters from "../components/discover/DiscoverFilters";
import DiscoverAssetCard from "../components/discover/DiscoverAssetCard";
import "../styles/discover.css";
import { ErrorState } from "../errors";
import { onWatchlistsChanged } from "../services/holdingsEvents";
import { IconSearch, IconX } from "../components/icons";

const SEARCH_DEBOUNCE_MS = 250;
const PAGE_SIZE = discoverConfig.pageSize;

export default function DiscoverPage() {
  const navigate = useNavigate();
  const config = discoverConfig;
  const [searchParams, setSearchParams] = useSearchParams();
  // The search text lives in the URL (?q=), so search-result links and the back button keep it.
  const urlQuery = searchParams.get("q") || "";
  const [queryInput, setQueryInput] = useState(urlQuery);
  const [page, setPage] = useState(0);
  // ?category=nft opens on that tab (used by notification and search links).
  const [category, setCategory] = useState(() => (searchParams.get("category") === "nft" ? "nft" : "crypto"));
  const [showFilters, setShowFilters] = useState(true);
  const [filters, setFilters] = useState(defaultFilters);
  const [options, setOptions] = useState(null); // sort keys + subcategories/signals from the backend
  const [result, setResult] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reloadTick, setReloadTick] = useState(0);
  const [compareIds, setCompareIds] = useState([]);

  useEffect(() => onWatchlistsChanged(() => setReloadTick((t) => t + 1)), []);

  // When the URL's query changes (typing settled, or a top-bar search link), go back to page 1,
  // and if the change came from outside, put it in the box.
  const [seenQuery, setSeenQuery] = useState(urlQuery);
  if (urlQuery !== seenQuery) {
    setSeenQuery(urlQuery);
    setPage(0);
    if (urlQuery !== queryInput.trim()) setQueryInput(urlQuery);
  }

  // Typing updates ?q= after a short pause.
  useEffect(() => {
    if (queryInput === urlQuery) return undefined;
    const t = setTimeout(() => {
      setSearchParams((p) => {
        if (queryInput.trim()) p.set("q", queryInput.trim());
        else p.delete("q");
        return p;
      }, { replace: true });
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queryInput]);

  // The filter vocabulary for this category (subcategories differ between crypto and NFTs).
  useEffect(() => {
    let cancelled = false;
    discoverApi.getOptions(category).then((o) => !cancelled && setOptions(o)).catch(() => !cancelled && setOptions(null));
    return () => {
      cancelled = true;
    };
  }, [category]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    discoverApi.getPage(category, filters, { q: urlQuery, offset: page * PAGE_SIZE, limit: PAGE_SIZE })
      .then((res) => !cancelled && setResult(res))
      .catch((e) => { if (!cancelled) { setResult({ items: [], total: 0 }); setError(e); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [category, filters, urlQuery, page, reloadTick]);

  // Any change to what's being asked for starts again at page 1.
  const changeFilters = (next) => {
    setFilters(next);
    setPage(0);
  };

  const switchCategory = (next) => {
    setCategory(next);
    setPage(0);
    // Subcategories and signals are per category; the sliders and sort carry over.
    setFilters((f) => ({ ...f, subcategories: [], signals: [], verifiedOnly: false }));
    setSearchParams((p) => { p.set("category", next); return p; }, { replace: true });
  };

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

  const activeTabConfig = config.categoryTabs.find((t) => t.key === category);
  const { items, total } = result;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const first = total ? page * PAGE_SIZE + 1 : 0;
  const last = Math.min(total, (page + 1) * PAGE_SIZE);
  const noun = category === "nft" ? "collection" : "asset";

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

        <div className="disc-tabs">
          {config.categoryTabs.map((tab) => (
            <button
              key={tab.key}
              className={category === tab.key ? "active" : ""}
              disabled={tab.disabled}
              title={tab.disabled ? tab.disabledReason : undefined}
              onClick={() => !tab.disabled && tab.key !== category && switchCategory(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTabConfig?.disabled ? (
          <div className="disc-comingsoon">
            <h3>{activeTabConfig.label} coverage is on the way</h3>
            <p>{activeTabConfig.disabledReason}</p>
          </div>
        ) : (
          <div className={`disc-layout ${showFilters ? "" : "no-filters"}`}>
            {showFilters && (
              <DiscoverFilters
                config={config}
                options={options}
                category={category}
                filters={filters}
                onChange={changeFilters}
                onReset={() => changeFilters(defaultFilters())}
              />
            )}

            <div>
              <div className="disc-search">
                <IconSearch size={14} />
                <input
                  type="search"
                  placeholder={`Search ${noun}s by name or symbol`}
                  aria-label={`Search ${noun}s`}
                  maxLength={64}
                  value={queryInput}
                  onChange={(e) => setQueryInput(e.target.value)}
                />
                {queryInput && (
                  <button type="button" aria-label="Clear search" onClick={() => setQueryInput("")}>
                    <IconX size={12} />
                  </button>
                )}
              </div>

              <div className="disc-count" aria-live="polite">
                {loading
                  ? "Loading…"
                  : total === 0
                    ? `No ${noun}s match`
                    : `${total} ${noun}${total === 1 ? "" : "s"} match${total === 1 ? "es" : ""}${pages > 1 ? ` · showing ${first}–${last}` : ""}`}
              </div>

              {error ? (
                <ErrorState error={error} onRetry={() => setReloadTick((t) => t + 1)} variant="panel" title="Couldn't load the market universe" />
              ) : !loading && items.length === 0 ? (
                <div className="disc-empty">
                  <h3>{config.emptyState.title}</h3>
                  <p>{config.emptyState.subtitle}</p>
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

              {pages > 1 && !error && (
                <div className="disc-pager">
                  <button type="button" disabled={page === 0 || loading} onClick={() => setPage((p) => p - 1)}>← Previous</button>
                  <span>Page {page + 1} of {pages}</span>
                  <button type="button" disabled={page >= pages - 1 || loading} onClick={() => setPage((p) => p + 1)}>Next →</button>
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
