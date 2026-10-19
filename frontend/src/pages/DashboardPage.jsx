import "../styles/dashboard.css";
import DashboardHeroHeader from "../components/dashboard/DashboardHeroHeader";
import GetStartedBanner from "../components/dashboard/GetStartedBanner";
import DashboardStatCards from "../components/dashboard/DashboardStatCards";
import PortfolioPerformanceCard from "../components/dashboard/PortfolioPerformanceCard";
import MarketInsightsCard from "../components/dashboard/MarketInsightsCard";
import TrendingAssetsSection from "../components/dashboard/TrendingAssetsSection";
import TrendingCollectionsSection from "../components/dashboard/TrendingCollectionsSection";
import { ErrorBoundary } from "../errors";

export default function DashboardPage() {
  return (
    <div className="sv2">
      <div className="sv2-page">
        <DashboardHeroHeader />
        <GetStartedBanner />
        <ErrorBoundary variant="section" label="Market stats"><DashboardStatCards /></ErrorBoundary>

        <div className="dv2-main-grid">
          <ErrorBoundary variant="section" label="Portfolio performance"><PortfolioPerformanceCard /></ErrorBoundary>
          <ErrorBoundary variant="section" label="Market insights"><MarketInsightsCard /></ErrorBoundary>
        </div>

        <ErrorBoundary variant="section" label="Trending assets"><TrendingAssetsSection /></ErrorBoundary>
        <ErrorBoundary variant="section" label="Trending collections"><TrendingCollectionsSection /></ErrorBoundary>
      </div>
    </div>
  );
}
