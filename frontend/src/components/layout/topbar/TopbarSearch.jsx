import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { topbarApi } from "../../../services/topbarApi";
import { useDisclosure } from "../../../hooks/useDisclosure";
import SearchResultGroup from "./SearchResultGroup";
import { IconSearch, IconX } from "../../icons";

const EMPTY_RESULTS = { assets: [], collections: [] };

export default function TopbarSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(EMPTY_RESULTS);
  const [recent, setRecent] = useState([]); // the user's recent searches, shown before typing
  const { isOpen, open, close, ref } = useDisclosure();
  const inputRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    const trimmed = query.trim();
    if (!trimmed) {
      setResults(EMPTY_RESULTS);
      return;
    }
    let cancelled = false;
    topbarApi.search(trimmed).then((res) => {
      if (!cancelled) setResults(res);
    });
    return () => {
      cancelled = true;
    };
  }, [query]);

  // Recent searches load each time the panel opens. They're a convenience: a failure just hides them.
  useEffect(() => {
    if (!isOpen) return;
    let cancelled = false;
    topbarApi.getRecentSearches().then((list) => !cancelled && setRecent(list)).catch(() => !cancelled && setRecent([]));
    return () => {
      cancelled = true;
    };
  }, [isOpen]);

  const clearRecent = () => {
    setRecent([]);
    topbarApi.clearRecentSearches().catch(() => {});
  };

  // "/" focuses search from anywhere, unless the person is already typing
  useEffect(() => {
    function handleShortcut(event) {
      const isTyping = ["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName);
      if (event.key === "/" && !isTyping) {
        event.preventDefault();
        inputRef.current?.focus();
      }
    }
    document.addEventListener("keydown", handleShortcut);
    return () => document.removeEventListener("keydown", handleShortcut);
  }, []);

  const handleSelect = (item) => {
    if (query.trim()) topbarApi.recordSearch(query.trim()).catch(() => {}); // remembered for next time
    close();
    setQuery("");
    if (item.kind === "asset") {
      navigate(`/asset-detail?symbol=${item.symbol}`);
    } else {
      navigate("/discover");
    }
  };

  const handleClear = () => {
    setQuery("");
    inputRef.current?.focus();
  };

  const hasQuery = query.trim().length > 0;
  const hasResults = results.assets.length > 0 || results.collections.length > 0;

  return (
    <div className="tb-search" ref={ref}>
      <div className={`tb-search-box ${isOpen ? "tb-search-box-active" : ""}`}>
        <IconSearch size={14} />
        <input
          ref={inputRef}
          type="text"
          className="tb-search-input"
          placeholder="Search assets, collections, insights…"
          aria-label="Search assets, collections, and insights"
          value={query}
          onFocus={open}
          onChange={(e) => setQuery(e.target.value)}
        />
        {hasQuery ? (
          <button type="button" className="tb-search-clear" onClick={handleClear} aria-label="Clear search">
            <IconX size={12} />
          </button>
        ) : (
          <kbd className="tb-search-kbd">/</kbd>
        )}
      </div>

      {isOpen && (
        <>
          <div className="tb-search-backdrop" onClick={close} />
          <div className="tb-search-panel">
            {!hasQuery && recent.length > 0 ? (
              <div className="tb-search-group">
                <div className="tb-search-group-title tb-search-recent-head">
                  <span>Recent searches</span>
                  <button type="button" className="tb-search-recent-clear" onClick={clearRecent}>Clear</button>
                </div>
                {recent.map((q) => (
                  <button key={q} type="button" className="tb-search-item" onClick={() => { setQuery(q); inputRef.current?.focus(); }}>
                    <span className="tb-search-item-name">{q}</span>
                  </button>
                ))}
              </div>
            ) : !hasQuery ? (
              <div className="tb-search-empty">
                Start typing to search assets, NFT collections, and tokenized assets.
              </div>
            ) : !hasResults ? (
              <div className="tb-search-empty">No results for &quot;{query}&quot;</div>
            ) : (
              <>
                <SearchResultGroup title="Assets" items={results.assets} priceKey="price" onSelect={handleSelect} />
                <SearchResultGroup
                  title="NFT collections & tokenized"
                  items={results.collections}
                  priceKey="floorUsd"
                  onSelect={handleSelect}
                />
              </>
            )}
            <div className="tb-search-footer">
              <span>↑↓ to navigate · Enter to open</span>
              <span>Esc to close</span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}