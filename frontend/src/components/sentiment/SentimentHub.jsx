import MoodOverview from "./MoodOverview";
import MoodTrendChart from "./MoodTrendChart";
import AssetSentimentList from "./AssetSentimentList";
import ThemesPanel from "./ThemesPanel";
import WhatWereReadingPanel from "./WhatWereReadingPanel";
import { IconRefresh } from "../icons";

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
                <IconRefresh size={12} />
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