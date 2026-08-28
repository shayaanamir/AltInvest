import { useTheme } from "../context/ThemeContext";
import { makeStyles } from "../styles/makeStyles";
import PortfolioStats from "../components/portfolio/PortfolioStats";
import PerformanceHistory from "../components/portfolio/PerformanceHistory";
import AssetAllocation from "../components/portfolio/AssetAllocation";
import CurrentHoldings from "../components/portfolio/CurrentHoldings";

export default function PortfolioPage() {
  const { tokens: t } = useTheme();
  const s = makeStyles(t);

  return (
    <div style={s.content}>
      {/* Page header */}
      <div style={s.pageHeader}>
        <div>
          <h1 style={s.pageTitle}>My Portfolio</h1>
          <p style={s.pageSub}>Track your alternative asset holdings and AI-driven optimization suggestions.</p>
        </div>
      </div>

      <PortfolioStats />

      <div style={s.portfolioChartsRow}>
        <PerformanceHistory />
        <AssetAllocation />
      </div>

      <CurrentHoldings />
    </div>
  );
}