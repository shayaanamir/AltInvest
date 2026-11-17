import { useCallback, useEffect, useRef, useState } from "react";
import { IconSearch, IconX } from "../icons";
import { ErrorState } from "../../errors";
import { discoverApi, defaultFilters } from "../../services/discoverApi";
import { togglePick, MAX_PICKS } from "../../utils/onboardingPayload";
import AssetPickCard from "./AssetPickCard";
import StepHead from "./StepHead";

const PAGE_SIZE = 24;
const SORTS = [
  { key: "aai_score", label: "AAI score" },
  { key: "change_24h", label: "24h move" },
  { key: "market_cap", label: "Market cap" },
];
// answers.markets uses "nfts"; Discover calls the category "nft". `list` is the answers key that stores the picks.
const TABS = {
  crypto: { label: "Crypto", category: "crypto", list: "assets", pick: (i) => i.symbol },
  nfts: { label: "NFTs", category: "nft", list: "nfts", pick: (i) => i.id },
};

function useDebounced(value, ms) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

export default function Step4Assets({ answers, setAnswer }) {
  const markets = answers.markets?.length ? answers.markets : ["crypto", "nfts"];
  const tabKeys = Object.keys(TABS).filter((k) => markets.includes(k));
  const [tab, setTab] = useState(tabKeys[0]);
  const [q, setQ] = useState("");
  const [sort, setSort] = useState("aai_score");
  // `key` names the search the rows belong to; while it differs from the current search, a load is in flight.
  const [state, setState] = useState({ key: null, cat: null, items: [], total: 0, error: null });
  const [more, setMore] = useState({ loading: false, error: null });
  const [reload, setReload] = useState(0);
  const query = useDebounced(q, 300);
  const requestId = useRef(0);

  const cfg = TABS[tab];
  const picked = answers.picked || {};               // { "crypto:BTC": { kind, id, symbol, name, color } } for the tray
  const selectedIds = answers[cfg.list] || [];

  const fetchPage = useCallback((offset) => {
    const id = ++requestId.current;                  // ignore answers that arrive after a newer request
    return discoverApi
      .getPage(cfg.category, { ...defaultFilters(), sort, order: "desc" }, { q: query, offset, limit: PAGE_SIZE })
      .then((page) => (id === requestId.current ? page : null));
  }, [cfg.category, sort, query]);

  const searchKey = `${cfg.category}|${sort}|${query}|${reload}`;

  useEffect(() => {
    let live = true;
    const done = { key: searchKey, cat: cfg.category };
    fetchPage(0)
      .then((page) => live && page && setState({ ...done, items: page.items, total: page.total, error: null }))
      .catch((error) => live && setState({ ...done, items: [], total: 0, error }));
    return () => { live = false; };
  }, [fetchPage, searchKey, cfg.category]);

  const loadMore = () => {
    setMore({ loading: true, error: null });
    fetchPage(items.length)
      .then((page) => {
        if (!page) return;
        setState((s) => ({ ...s, items: [...s.items, ...page.items], total: page.total }));
        setMore({ loading: false, error: null });
      })
      .catch((error) => setMore({ loading: false, error }));
  };

  const toggle = (item) => {
    const id = cfg.pick(item);
    const key = `${tab}:${id}`;
    if (!selectedIds.includes(id) && selectedIds.length >= MAX_PICKS) return;   // at the cap: ignore a new pick
    const next = togglePick(selectedIds, id, MAX_PICKS);
    setAnswer(cfg.list, next);
    const meta = { ...picked };
    if (next.includes(id)) meta[key] = { kind: tab, id, symbol: item.symbol, name: item.name };
    else delete meta[key];
    setAnswer("picked", meta);
  };

  const remove = (key) => {
    const { kind, id } = picked[key];
    setAnswer(TABS[kind].list, (answers[TABS[kind].list] || []).filter((x) => x !== id));
    const meta = { ...picked };
    delete meta[key];
    setAnswer("picked", meta);
  };

  const chips = Object.entries(picked).filter(([, p]) => (answers[TABS[p.kind].list] || []).includes(p.id));
  const loading = state.key !== searchKey;
  const items = state.cat === cfg.category ? state.items : [];   // never show the other market's rows
  const { total } = state;
  const error = state.key === searchKey ? state.error : null;
  const hasMore = items.length < total;

  return (
    <>
      <StepHead
        eyebrow="Follow"
        title="Pick what you want to follow"
        sub="Choose a few coins or collections. They're saved to a watchlist so your dashboard has something to show from day one."
      />

      <div className="ob-toolbar">
        {tabKeys.length > 1 && (
          <div className="sv2-segmented" role="tablist" aria-label="Market">
            {tabKeys.map((k) => (
              <button
                key={k} type="button" role="tab" aria-selected={tab === k}
                className={tab === k ? "active" : ""}
                onClick={() => { setTab(k); setQ(""); }}
              >
                {TABS[k].label}
                {(answers[TABS[k].list] || []).length > 0 && ` · ${(answers[TABS[k].list] || []).length}`}
              </button>
            ))}
          </div>
        )}
        <label className="ob-search">
          <IconSearch size={15} />
          <input
            type="text"
            autoComplete="off"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={tab === "nfts" ? "Search collections" : "Search coins"}
            aria-label={tab === "nfts" ? "Search collections" : "Search coins"}
            maxLength={64}
          />
          {q && (
            <button type="button" onClick={() => setQ("")} aria-label="Clear search"><IconX size={14} /></button>
          )}
        </label>
      </div>

      <div className="ob-sortrow" role="group" aria-label="Sort by">
        <span className="ob-sortlabel">Sort by</span>
        {SORTS.map((s) => (
          <button
            key={s.key} type="button"
            className={`sv2-chip ${sort === s.key ? "active" : ""}`}
            aria-pressed={sort === s.key}
            onClick={() => setSort(s.key)}
          >
            {s.label}
          </button>
        ))}
      </div>

      {error && items.length === 0 ? (
        <ErrorState error={error} onRetry={() => setReload((n) => n + 1)} variant="inline" title="Couldn't load the list" />
      ) : loading && items.length === 0 ? (
        <div className="ob-state" role="status"><span className="sv2-spinner" /> Loading…</div>
      ) : items.length === 0 ? (
        <div className="sv2-empty-state">
          <div className="sv2-empty-title">{query ? `Nothing matches "${query}"` : "Nothing to show yet"}</div>
          <div>{query ? "Try a different name or symbol." : "You can add assets any time from Discover."}</div>
        </div>
      ) : (
        <>
          <div className="ob-asset-grid">
            {items.map((item) => (
              <AssetPickCard key={`${item.type}:${item.id}`} item={item} selected={selectedIds.includes(cfg.pick(item))} onToggle={toggle} />
            ))}
          </div>
          {more.error && <ErrorState error={more.error} onRetry={loadMore} variant="inline" title="Couldn't load more" />}
          {hasMore && (
            <div className="ob-more">
              <button type="button" className="ob-btn ob-btn-outline" onClick={loadMore} disabled={more.loading}>
                {more.loading ? "Loading…" : `Show more (${total - items.length})`}
              </button>
            </div>
          )}
        </>
      )}

      <div className="sv2-card ob-tray">
        <div className="ob-tray-head">
          <span className="ob-tray-title">{chips.length ? `${chips.length} selected` : "Nothing selected yet"}</span>
          <span className="ob-tray-hint">
            {chips.length
              ? "Saved as “My Watchlist” when you finish."
              : "That's fine. You can add assets any time from Discover."}
          </span>
        </div>
        {chips.length > 0 && (
          <div className="ob-chips">
            {chips.map(([key, p]) => (
              <span className="ob-chip" key={key}>
                {p.symbol}
                <button type="button" className="ob-chip-x" onClick={() => remove(key)} aria-label={`Remove ${p.name}`}>
                  <IconX size={12} />
                </button>
              </span>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
