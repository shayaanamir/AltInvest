import { useState } from "react";
import { IconExternal, IconChevronDown } from "./icons";

export default function WhatWeReadList({ detail, colors }) {
  const [showAll, setShowAll] = useState(false);
  const [showSources, setShowSources] = useState(false);

  const headlines = detail.headlines;
  const visible = showAll ? headlines : headlines.slice(0, 3);
  const remaining = headlines.length - visible.length;
  const sourceEntries = Object.entries(detail.articlesBySource);

  return (
    <div className="sv2-card sv2-card-pad">
      <div className="sv2-card-title" style={{ marginBottom: 8 }}>What we read</div>

      {visible.map((h, i) => (
        <div key={i} className="sv2-news-item">
          <span className={`sv2-dot ${h.score > 0.1 ? "positive" : h.score < -0.1 ? "negative" : "neutral"}`} />
          <div>
            <a href={h.link} target="_blank" rel="noreferrer" className="sv2-news-title">{h.title} <IconExternal /></a>
            <div className="sv2-meta-line">
              <span>{h.source}</span><span>·</span><span>{Math.round(h.age_hours)}h ago</span>
            </div>
          </div>
        </div>
      ))}

      {remaining > 0 && (
        <button className="sv2-pill-btn sv2-mt-12" onClick={() => setShowAll(true)}>See {remaining} more</button>
      )}

      <hr style={{ border: "none", borderTop: "1px solid var(--sv2-border)", margin: "18px 0" }} />

      <div className="sv2-small sv2-muted">
        Roughly {detail.sourceBreakdown.newsPct}% of this read comes from news / nlp, {detail.sourceBreakdown.marketPct}% from market signals.
      </div>
      <div className="sv2-dist-bar" style={{ marginTop: 10 }}>
        <div style={{ width: `${detail.sourceBreakdown.newsPct}%`, background: colors.accent }} />
        <div style={{ width: `${detail.sourceBreakdown.marketPct}%`, background: colors.border }} />
      </div>

      <button className="sv2-pill-btn sv2-mt-12" onClick={() => setShowSources((s) => !s)}>
        Where it came from ({sourceEntries.length}) <IconChevronDown />
      </button>

      {showSources && (
        <div className="sv2-mt-12 sv2-flex-col sv2-gap-6">
          {sourceEntries.map(([src, count]) => (
            <div key={src} className="sv2-flex-between sv2-small sv2-muted">
              <span>{src}</span><span>{count}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}