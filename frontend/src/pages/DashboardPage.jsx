import "../styles/sentiment.css";
import "../styles/dashboard.css";
import DashboardHeroHeader from "../components/dashboard/DashboardHeroHeader";
import GetStartedBanner from "../components/dashboard/GetStartedBanner";
import DashboardStatCards from "../components/dashboard/DashboardStatCards";
import PortfolioPerformanceCard from "../components/dashboard/PortfolioPerformanceCard";
import MarketInsightsCard from "../components/dashboard/MarketInsightsCard";
import TrendingAssetsSection from "../components/dashboard/TrendingAssetsSection";
import TrendingCollectionsSection from "../components/dashboard/TrendingCollectionsSection";

export default function DashboardPage() {
  return (
    <div className="sv2">
      <div className="sv2-page">
        <DashboardHeroHeader />
        <GetStartedBanner />
        <DashboardStatCards />

        <div className="dv2-main-grid">
          <PortfolioPerformanceCard />
          <MarketInsightsCard />
        </div>

        <TrendingAssetsSection />
        <TrendingCollectionsSection />
      </div>
    </div>
  );
}
