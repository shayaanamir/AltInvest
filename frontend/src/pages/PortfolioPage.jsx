import "../styles/dashboard.css";
import "../styles/portfolio.css";
import PortfolioHeader from "../components/portfolio/PortfolioHeader";
import PortfolioStats from "../components/portfolio/PortfolioStats";
import PerformanceHistory from "../components/portfolio/PerformanceHistory";
import AssetAllocation from "../components/portfolio/AssetAllocation";
import CryptoHoldingsTable from "../components/portfolio/CryptoHoldingsTable";
import NftHoldingsGrid from "../components/portfolio/NftHoldingsGrid";
import PortfolioIntelligence from "../components/portfolio/PortfolioIntelligence";
import { ErrorBoundary } from "../errors";

export default function PortfolioPage() {
  return (
    <div className="sv2">
      <div className="sv2-page">
        <PortfolioHeader />
        <ErrorBoundary variant="section" label="Portfolio summary"><PortfolioStats /></ErrorBoundary>

        <div className="dv2-main-grid" style={{ marginTop: 14 }}>
          <ErrorBoundary variant="section" label="Performance history"><PerformanceHistory /></ErrorBoundary>
          <ErrorBoundary variant="section" label="Asset allocation"><AssetAllocation /></ErrorBoundary>
        </div>

        <ErrorBoundary variant="section" label="Holdings"><CryptoHoldingsTable /></ErrorBoundary>
        <ErrorBoundary variant="section" label="NFT holdings"><NftHoldingsGrid /></ErrorBoundary>
        <ErrorBoundary variant="section" label="Portfolio intelligence"><PortfolioIntelligence /></ErrorBoundary>
      </div>
    </div>
  );
}