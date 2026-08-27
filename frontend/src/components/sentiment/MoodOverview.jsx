import { useState, useEffect } from "react";
import { sentimentApi } from "../../services/sentimentApi";
import MoodGaugeCard from "./MoodGaugeCard";

export default function MoodOverview({ colors }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    sentimentApi.getMoodOverview().then(setData).catch(console.error);
  }, []);

  if (!data) {
    return (
      <div className="sv2-mood-grid">
        <div className="sv2-card sv2-card-pad sv2-muted sv2-small">Loading crypto mood…</div>
        <div className="sv2-card sv2-card-pad sv2-muted sv2-small">Loading NFT mood…</div>
      </div>
    );
  }

  const { crypto, nft } = data;

  return (
    <div className="sv2-mood-grid">
      <MoodGaugeCard
        eyebrow="Crypto Market Mood"
        title={crypto.label}
        metaLine={`${crypto.avgScore >= 0 ? "+" : ""}${crypto.avgScore} average · ${cap(crypto.confidenceLabel)} confidence · built from ${crypto.assetCount} assets`}
        caption="Confidence here reflects article volume."
        axisLabels={["BEARISH", "NEUTRAL", "BULLISH"]}
        score={crypto.avgScore}
        arcGreen={colors.arcGreen}
        arcRed={colors.arcRed}
        greyArc={colors.greyArc}
      />
      <MoodGaugeCard
        eyebrow="NFT Market Mood"
        title={nft.label}
        metaLine={`${nft.avgScore >= 0 ? "+" : ""}${nft.avgScore} average · ${cap(nft.confidenceLabel)} confidence · built from ${nft.assetCount} collections`}
        caption="Confidence here reflects social-volume coverage."
        axisLabels={["COOLING", "NEUTRAL", "HEATING UP"]}
        score={nft.avgScore}
        arcGreen={colors.arcGreen}
        arcRed={colors.arcRed}
        greyArc={colors.greyArc}
        infoNote={
          nft.excludedCount > 0
            ? `${nft.excludedCount} tracked collection${nft.excludedCount > 1 ? "s have" : " has"} too little evidence to contribute and ${nft.excludedCount > 1 ? "are" : "is"} excluded from this reading.`
            : null
        }
      />
    </div>
  );
}

function cap(s) {
  return s ? s[0].toUpperCase() + s.slice(1) : s;
}