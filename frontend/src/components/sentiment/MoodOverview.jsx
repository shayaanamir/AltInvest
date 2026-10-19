import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../errors";
import { sentimentApi } from "../../services/sentimentApi";
import MoodGaugeCard from "./MoodGaugeCard";

function cap(s) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

// Shown where there is no reading to draw: honest about why, never a placeholder number.
function NoReadingCard({ eyebrow, reason }) {
  return (
    <div className="sv2-card sv2-card-pad">
      <div className="sv2-eyebrow">{eyebrow}</div>
      <div className="sv2-muted sv2-small" style={{ marginTop: 12 }}>{reason}</div>
    </div>
  );
}

export default function MoodOverview({ colors }) {
  const { data, error, refetch } = useAsync(() => sentimentApi.getMoodOverview(), []);

  if (error) {
    return (
      <div className="sv2-card sv2-card-pad">
        <ErrorState error={error} onRetry={refetch} title="Couldn't load market mood" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="sv2-mood-grid">
        <div className="sv2-card sv2-card-pad sv2-muted sv2-small">Loading crypto mood…</div>
        <div className="sv2-card sv2-card-pad sv2-muted sv2-small">Loading NFT mood…</div>
        <div className="sv2-card sv2-card-pad sv2-muted sv2-small">Loading real estate mood…</div>
      </div>
    );
  }

  const { crypto, nft, realEstate } = data;
  const gauge = { arcGreen: colors.arcGreen, arcRed: colors.arcRed, greyArc: colors.greyArc };
  const signed = (n) => `${n >= 0 ? "+" : ""}${n}`;

  return (
    <div className="sv2-mood-grid">
      {crypto ? (
        <MoodGaugeCard
          eyebrow="Crypto Market Mood"
          title={crypto.label}
          metaLine={`${signed(crypto.avgScore)} average · ${cap(crypto.confidenceLabel)} confidence · built from ${crypto.assetCount} assets`}
          caption="Confidence here reflects article volume."
          axisLabels={["BEARISH", "NEUTRAL", "BULLISH"]}
          score={crypto.avgScore}
          {...gauge}
        />
      ) : (
        <NoReadingCard eyebrow="Crypto Market Mood" reason="No sentiment readings yet. Use Refresh Pipeline to collect them." />
      )}

      {nft ? (
        <MoodGaugeCard
          eyebrow="NFT Market Mood"
          title={nft.label}
          metaLine={`${signed(nft.avgScore)} average · ${cap(nft.confidenceLabel)} confidence · built from ${nft.assetCount} collections`}
          caption="Confidence here reflects social-volume coverage."
          axisLabels={["COOLING", "NEUTRAL", "HEATING UP"]}
          score={nft.avgScore}
          {...gauge}
        />
      ) : (
        <NoReadingCard eyebrow="NFT Market Mood" reason="There is no NFT sentiment source yet, so no mood can be shown." />
      )}

      {realEstate ? (
        <MoodGaugeCard
          eyebrow="Tokenized Real Estate Mood"
          title={realEstate.label}
          metaLine={`${signed(realEstate.avgScore)} average · ${cap(realEstate.confidenceLabel)} confidence · built from ${realEstate.propertyCount} properties`}
          caption="Confidence here reflects listing & transaction volume."
          axisLabels={["DECLINING", "NEUTRAL", "APPRECIATING"]}
          score={realEstate.avgScore}
          {...gauge}
        />
      ) : (
        <NoReadingCard eyebrow="Tokenized Real Estate Mood" reason="There is no real-estate sentiment source yet, so no mood can be shown." />
      )}
    </div>
  );
}
