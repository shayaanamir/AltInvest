import MoodOverview from "./MoodOverview";
import MoodTrendChart from "./MoodTrendChart";
import AssetSentimentList from "./AssetSentimentList";
import ThemesPanel from "./ThemesPanel";
import WhatWereReadingPanel from "./WhatWereReadingPanel";

export default function SentimentHub({ colors, onSelectAsset, onRefresh, refreshing }) {
  return (
    <div className="sv2-flex-col sv2-gap-16">
      <div className="sv2-flex-between" style={{ alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 className="sv2-h1">Sentiment Hub</h1>
          <p className="sv2-lead">What people are saying, and how strongly, across crypto and NFTs.</p>
        </div>
        {onRefresh && (
          <button
            className="sv2-refresh-btn"
            onClick={onRefresh}
            disabled={refreshing}
            style={{ height: "40px", cursor: refreshing ? "not-allowed" : "pointer" }}
          >
            {refreshing ? (
              <>
                <span className="sv2-spinner"></span>
                <span>Refreshing pipeline...</span>
              </>
            ) : (
              <>
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="currentColor" viewBox="0 0 16 16" style={{ transform: "scale(1.1)" }}>
                  <path fillRule="evenodd" d="M8 3a5 5 0 1 0 4.546 2.914.5.5 0 0 1 .908-.417A6 6 0 1 1 8 2z"/>
                  <path d="M8 4.466V.534a.25.25 0 0 1 .41-.192l2.36 1.966c.12.1.12.284 0 .384L8.41 4.658A.25.25 0 0 1 8 4.466z"/>
                </svg>
                <span>Refresh Pipeline</span>
              </>
            )}
          </button>
        )}
      </div>

      <MoodOverview colors={colors} />
      <MoodTrendChart colors={colors} />

      <div className="sv2-hub-bottom">
        <AssetSentimentList colors={colors} onSelectAsset={onSelectAsset} />
        <div className="sv2-flex-col sv2-gap-16">
          <ThemesPanel />
          <WhatWereReadingPanel />
        </div>
      </div>
    </div>
  );
}