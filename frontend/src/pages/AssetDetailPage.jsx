import { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import "../styles/assetDetail.css";
import { assetDetailApi } from "../services/assetDetailApi";
import AssetHeaderCard from "../components/assetDetail/AssetHeaderCard";
import PricePerformanceCard from "../components/assetDetail/PricePerformanceCard";
import MarketStatisticsCard from "../components/assetDetail/MarketStatisticsCard";
import AaiScoreCard from "../components/assetDetail/AaiScoreCard";
import RiskOverviewCard from "../components/assetDetail/RiskOverviewCard";
import SentimentReadCard from "../components/assetDetail/SentimentReadCard";
import AboutAssetCard from "../components/assetDetail/AboutAssetCard";
import SimilarAssetsSection from "../components/assetDetail/SimilarAssetsSection";

export default function AssetDetailPage({ onNavigate }) {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const symbol = searchParams.get("symbol") || "BTC";

  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    assetDetailApi.getAssetDetail(symbol).then((d) => {
      setDetail(d);
      setLoading(false);
    }).catch(console.error);
  }, [symbol]);

  const handleBack = () => {
    if (onNavigate) onNavigate("Dashboard");
    else navigate("/dashboard");
  };

  return (
    <div className="sv2">
      <div className="sv2-page adt-page">
        {loading || !detail ? (
          <div className="sv2-muted sv2-small">Loading asset…</div>
        ) : (
          <>
            <AssetHeaderCard header={detail.header} onBack={handleBack} />

            <PricePerformanceCard
              priceHistory={detail.priceHistory}
              forecast={detail.forecast}
              aaiPanel={detail.aaiPanel}
            />

            <MarketStatisticsCard marketStats={detail.marketStats} />

            {/* AAI Score comes first in this row, per the redesign */}
            <div className="adt-panel-row">
              <AaiScoreCard aaiPanel={detail.aaiPanel} />
              <RiskOverviewCard riskOverview={detail.riskOverview} />
              <SentimentReadCard sentimentSnippet={detail.sentimentSnippet} />
            </div>

            <AboutAssetCard name={detail.header.name} about={detail.about} aaiScore={detail.aaiPanel?.score} />

            <SimilarAssetsSection symbol={detail.symbol} relatedAssets={detail.relatedAssets} />
          </>
        )}
      </div>
    </div>
  );
}