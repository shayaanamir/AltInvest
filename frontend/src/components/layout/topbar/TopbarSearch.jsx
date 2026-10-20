import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { topbarApi } from "../../../services/topbarApi";
import { useDisclosure } from "../../../hooks/useDisclosure";
import SearchResultItem from "./SearchResultItem";
import { IconSearch, IconX } from "../../icons";
import { describeError } from "../../../errors";

const DEBOUNCE_MS = 200;
const EMPTY = { assets: [], collections: [], insights: [] };

/** Where a picked result goes. NFT collections open Discover filtered to that collection (there's no NFT page). */
function hrefFor(item) {
  if (item.kind === "asset") return `/asset-detail?symbol=${encodeURIComponent(item.symbol)}`;
  if (item.kind === "collection") return `/discover?category=nft&q=${encodeURIComponent(item.name)}`;
  if (item.kind === "insight") {
    if (item.symbol) return `/asset-detail?symbol=${encodeURIComponent(item.symbol)}`;
    if (item.slug) return `/discover?category=nft&q=${encodeURIComponent(item.slug)}`;
    return "/dashboard";
  }
  return null;
}

export default function TopbarSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(EMPTY);
  const [status, setStatus] = useState("idle"); // idle | loading | done | error
  const [errorText, setErrorText] = useState("");
  const [recent, setRecent] = useState([]); // the user's recent searches, shown before typing
  const [active, setActive] = useState(-1); // keyboard-highlighted row
  const { isOpen, open, close, ref } = useDisclosure();
  const inputRef = useRef(null);
  const navigate = useNavigate();

  const trimmed = query.trim();
  const hasQuery = trimmed.length > 0;

  // Search after typing pauses, so each keystroke doesn't fire two requests. A newer search
  // cancels an older one's result.
  useEffect(() => {
    if (!hasQuery) return undefined;
    let cancelled = false;
    const timer = setTimeout(() => {
      setStatus("loading");
      topbarApi.search(trimmed)
        .then((res) => {
          if (cancelled) return;
          setResults(res);
          setStatus("done");
          setActive(-1);
        })
        .catch((e) => {
          if (cancelled) return;
          setResults(EMPTY);
          setErrorText(describeError(e).message);
          setStatus("error");
        });
    }, DEBOUNCE_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [trimmed, hasQuery]);

  // Recent searches load each time the panel opens. They're a convenience: a failure just hides them.
  useEffect(() => {
    if (!isOpen) return undefined;
    let cancelled = false;
    topbarApi.getRecentSearches().then((list) => !cancelled && setRecent(list)).catch(() => !cancelled && setRecent([]));
    return () => {
      cancelled = true;
    };
  }, [isOpen]);

  // "/" focuses search from anywhere, unless the person is already typing
  useEffect(() => {
    function handleShortcut(event) {
      const isTyping = ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName);
      if (event.key === "/" && !isTyping) {
        event.preventDefault();
        inputRef.current?.focus();
      }
    }
    document.addEventListener("keydown", handleShortcut);
    return () => document.removeEventListener("keydown", handleShortcut);
  }, []);

  const groups = hasQuery
    ? [
        { title: "Assets", items: results.assets, priceKey: "price" },
        { title: "NFT collections", items: results.collections, priceKey: "floorUsd" },
        { title: "Insights", items: results.insights, priceKey: null },
      ].filter((g) => g.items.length > 0)
    : recent.length
      ? [{ title: "Recent searches", items: recent.map((q) => ({ id: `recent-${q}`, kind: "recent", name: q })), priceKey: null }]
      : [];
  const flat = groups.flatMap((g) => g.items);
  const showResults = !hasQuery || status === "done";

  const changeQuery = (value) => {
    setQuery(value);
    setActive(-1);
    if (!value.trim()) {
      setResults(EMPTY);
      setStatus("idle");
    }
  };

  const select = (item) => {
    if (item.kind === "recent") {
      changeQuery(item.name);
      inputRef.current?.focus();
      return;
    }
    if (trimmed) topbarApi.recordSearch(trimmed).catch(() => {}); // remembered for next time
    close();
    changeQuery("");
    if (item.kind === "insight" && item.url) {
      window.open(item.url, "_blank", "noopener,noreferrer");
      return;
    }
    const href = hrefFor(item);
    if (href) navigate(href);
  };

  const clearRecent = () => {
    setRecent([]);
    topbarApi.clearRecentSearches().catch(() => {});
  };

  const onKeyDown = (e) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!isOpen) open();
      if (!flat.length || !showResults) return;
      setActive((i) => (e.key === "ArrowDown" ? (i + 1) % flat.length : (i <= 0 ? flat.length - 1 : i - 1)));
    } else if (e.key === "Enter") {
      // Enter opens the highlighted row, or the first result if nothing is highlighted.
      const item = flat[active >= 0 ? active : 0];
      if (item && showResults) {
        e.preventDefault();
        select(item);
      }
    } else if (e.key === "Escape") {
      close();
      inputRef.current?.blur();
    }
  };

  const optionId = (i) => `tb-search-opt-${i}`;
  let index = -1;

  return (
    <div className="tb-search" ref={ref}>
      <div className={`tb-search-box ${isOpen ? "tb-search-box-active" : ""}`}>
        <IconSearch size={14} />
        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-expanded={isOpen}
          aria-controls="tb-search-panel"
          aria-autocomplete="list"
          aria-activedescendant={active >= 0 ? optionId(active) : undefined}
          className="tb-search-input"
          placeholder="Search assets, collections, insights…"
          aria-label="Search assets, collections, and insights"
          value={query}
          maxLength={64}
          onFocus={open}
          onChange={(e) => {
            changeQuery(e.target.value);
            open();
          }}
          onKeyDown={onKeyDown}
        />
        {hasQuery ? (
          <button type="button" className="tb-search-clear" onClick={() => { changeQuery(""); inputRef.current?.focus(); }} aria-label="Clear search">
            <IconX size={12} />
          </button>
        ) : (
          <kbd className="tb-search-kbd">/</kbd>
        )}
      </div>

      {isOpen && (
        <>
          <div className="tb-search-backdrop" onClick={close} />
          <div className="tb-search-panel" id="tb-search-panel" role="listbox" aria-label="Search results">
            {hasQuery && status === "error" ? (
              <div className="tb-search-empty tb-search-error" role="alert">Search isn&apos;t working right now. {errorText}</div>
            ) : hasQuery && status !== "done" ? (
              <div className="tb-search-empty">Searching…</div>
            ) : hasQuery && flat.length === 0 ? (
              <div className="tb-search-empty">No results for &quot;{trimmed}&quot;</div>
            ) : !hasQuery && flat.length === 0 ? (
              <div className="tb-search-empty">Start typing to search assets, NFT collections, and insights.</div>
            ) : (
              groups.map((g) => (
                <div className="tb-search-group" key={g.title}>
                  <div className={`tb-search-group-title ${g.items[0]?.kind === "recent" ? "tb-search-recent-head" : ""}`}>
                    <span>{g.title}</span>
                    {g.items[0]?.kind === "recent" && (
                      <button type="button" className="tb-search-recent-clear" onClick={clearRecent}>Clear</button>
                    )}
                  </div>
                  {g.items.map((item) => {
                    index += 1;
                    const i = index;
                    return (
                      <SearchResultItem
                        key={item.id}
                        id={optionId(i)}
                        item={item}
                        priceKey={g.priceKey}
                        active={i === active}
                        onHover={() => setActive(i)}
                        onSelect={select}
                      />
                    );
                  })}
                </div>
              ))
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
