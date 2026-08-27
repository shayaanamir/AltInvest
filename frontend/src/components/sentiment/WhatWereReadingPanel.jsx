import { useState, useEffect } from "react";
import { sentimentApi, relativeTime, WATCHLIST } from "../../services/sentimentApi";
import { IconExternal } from "./icons";

export default function WhatWereReadingPanel() {
  const [tab, setTab] = useState("news");
  const [items, setItems] = useState([]);
  const [watchlistOnly, setWatchlistOnly] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setShowAll(false);
    sentimentApi.getWhatWereReading(tab).then((r) => {
      setItems(r);
      setLoading(false);
    }).catch(console.error);
  }, [tab]);

  const filtered = watchlistOnly ? items.filter((i) => WATCHLIST.includes(i.assetId)) : items;
  const visible = showAll ? filtered : filtered.slice(0, 4);

  return (
    <div className="sv2-card sv2-card-pad-sm">
      <div className="sv2-flex-between">
        <span className="sv2-card-title">What we're reading</span>
        <div className="sv2-segmented">
          <button className={tab === "news" ? "active" : ""} onClick={() => setTab("news")}>News</button>
          <button className={tab === "nft" ? "active" : ""} onClick={() => setTab("nft")}>NFT chatter</button>
        </div>
      </div>

      <label className="sv2-checkbox-row sv2-mt-12">
        <input type="checkbox" checked={watchlistOnly} onChange={(e) => setWatchlistOnly(e.target.checked)} />
        Only my watchlist
      </label>

      <div className="sv2-mt-8">
        {loading ? (
          <div className="sv2-muted sv2-small" style={{ padding: "16px 0" }}>Loading…</div>
        ) : visible.length === 0 ? (
          <div className="sv2-muted sv2-small" style={{ padding: "16px 0" }}>Nothing matches this filter.</div>
        ) : (
          visible.map((item, i) => (
            <div key={i} className="sv2-news-item">
              <span className={`sv2-dot ${item.score > 0.1 ? "positive" : item.score < -0.1 ? "negative" : "neutral"}`} />
              <div>
                <a href={item.link} target="_blank" rel="noreferrer" className="sv2-news-title">
                  {item.title} <IconExternal />
                </a>
                <div className="sv2-meta-line">
                  <span>{item.source}</span>
                  <span>·</span>
                  <span>{item.age_hours ? `${Math.round(item.age_hours)}h ago` : relativeTime()}</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {filtered.length > 4 && (
        <button className="sv2-pill-btn sv2-mt-12" onClick={() => setShowAll((s) => !s)}>
          {showAll ? "Show less" : "See more"}
        </button>
      )}
    </div>
  );
}