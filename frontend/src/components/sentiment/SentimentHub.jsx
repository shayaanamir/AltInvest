import MoodOverview from "./MoodOverview";
import MoodTrendChart from "./MoodTrendChart";
import AssetSentimentList from "./AssetSentimentList";
import ThemesPanel from "./ThemesPanel";
import WhatWereReadingPanel from "./WhatWereReadingPanel";

export default function SentimentHub({ colors, onSelectAsset }) {
  return (
    <div className="sv2-flex-col sv2-gap-16">
      <div>
        <h1 className="sv2-h1">Sentiment Hub</h1>
        <p className="sv2-lead">What people are saying, and how strongly, across crypto and NFTs.</p>
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