import { useSearchParams, useNavigate } from "react-router-dom";
import "../styles/assetDetail.css";
import { useAsync } from "../hooks/useAsync";
import { assetDetailApi } from "../services/assetDetailApi";
import AssetHeaderCard from "../components/assetDetail/AssetHeaderCard";
import PricePerformanceCard from "../components/assetDetail/PricePerformanceCard";
import MarketStatisticsCard from "../components/assetDetail/MarketStatisticsCard";
import AaiScoreCard from "../components/assetDetail/AaiScoreCard";
import RiskOverviewCard from "../components/assetDetail/RiskOverviewCard";
import SentimentReadCard from "../components/assetDetail/SentimentReadCard";
import AboutAssetCard from "../components/assetDetail/AboutAssetCard";
import SimilarAssetsSection from "../components/assetDetail/SimilarAssetsSection";
import { ErrorState, ErrorBoundary } from "../errors";
import { onWatchlistsChanged } from "../services/holdingsEvents";

export default function AssetDetailPage({ onNavigate }) {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const symbol = searchParams.get("symbol");

  const { data: detail, loading, error, refetch } = useAsync(
    () => (symbol ? assetDetailApi.getAssetDetail(symbol) : Promise.resolve(null)),
    [symbol],
    { subscribe: onWatchlistsChanged }
  );

  const handleBack = () => {
    if (onNavigate) onNavigate("Dashboard");
    else navigate("/dashboard");
  };

  return (
    <div className="sv2">
      <div className="sv2-page adt-page">
        {loading ? (
          <div className="sv2-muted sv2-small">Loading asset…</div>
        ) : error ? (
          <>
            <button className="adt-back-btn" onClick={handleBack}>Back</button>
            <div className="sv2-card sv2-card-pad">
              <ErrorState error={error} onRetry={refetch} variant="panel" title={`Couldn't load ${symbol}`} />
            </div>
          </>
        ) : !detail ? (
          <>
            <button className="adt-back-btn" onClick={handleBack}>Back</button>
            <div className="sv2-muted sv2-small">
              {symbol ? `No asset "${symbol}" in the database.` : "No asset selected."} Crypto assets only for now — NFT collections don't have a detail page yet.
            </div>
          </>
        ) : (
          <>
            <AssetHeaderCard header={detail.header} onBack={handleBack} />

            <ErrorBoundary variant="section" label="Price chart">
              <PricePerformanceCard
                priceHistory={detail.priceHistory}
                forecast={detail.forecast}
                forecastMeta={detail.forecastMeta}
                aaiPanel={detail.aaiPanel}
              />
            </ErrorBoundary>

            <MarketStatisticsCard marketStats={detail.marketStats} />

            {/* AAI Score comes first in this row, per the redesign */}
            <div className="adt-panel-row">
              <ErrorBoundary variant="section" label="AAI score"><AaiScoreCard aaiPanel={detail.aaiPanel} /></ErrorBoundary>
              <ErrorBoundary variant="section" label="Risk overview"><RiskOverviewCard riskOverview={detail.riskOverview} /></ErrorBoundary>
              <ErrorBoundary variant="section" label="Sentiment"><SentimentReadCard sentimentSnippet={detail.sentimentSnippet} /></ErrorBoundary>
            </div>

            <AboutAssetCard name={detail.header.name} about={detail.about} aaiScore={detail.aaiPanel?.score} />

            {detail.relatedAssets.length > 0 && (
              <ErrorBoundary variant="section" label="Related assets">
                <SimilarAssetsSection title="Related assets" assets={detail.relatedAssets} showCompare={false} />
              </ErrorBoundary>
            )}
            <ErrorBoundary variant="section" label="Similar assets">
              <SimilarAssetsSection
                title="Similar profile"
                assets={detail.similarAssets}
                emptyText="Not enough scores stored to compare this asset's profile with others yet."
              />
            </ErrorBoundary>
          </>
        )}
      </div>
    </div>
  );
}