import "../styles/sentiment.css";
import "../styles/dashboard.css";
import "../styles/portfolio.css";
import PortfolioHeader from "../components/portfolio/PortfolioHeader";
import PortfolioStats from "../components/portfolio/PortfolioStats";
import PerformanceHistory from "../components/portfolio/PerformanceHistory";
import AssetAllocation from "../components/portfolio/AssetAllocation";
import CryptoHoldingsTable from "../components/portfolio/CryptoHoldingsTable";
import NftHoldingsGrid from "../components/portfolio/NftHoldingsGrid";
import PortfolioIntelligence from "../components/portfolio/PortfolioIntelligence";

export default function PortfolioPage() {
  return (
    <div className="sv2">
      <div className="sv2-page">
        <PortfolioHeader />
        <PortfolioStats />

        <div className="dv2-main-grid" style={{ marginTop: 14 }}>
          <PerformanceHistory />
          <AssetAllocation />
        </div>

        <CryptoHoldingsTable />
        <NftHoldingsGrid />
        <PortfolioIntelligence />
      </div>
    </div>
  );
}