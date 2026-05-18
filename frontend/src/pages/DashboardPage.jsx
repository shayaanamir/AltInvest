import { useTheme } from "../context/ThemeContext";
import { makeStyles } from "../styles/makeStyles";
import StatsRow from "../components/dashboard/StatsRow";
import InsightsPanel from "../components/dashboard/InsightsPanel";
import TrendingAssets from "../components/dashboard/TrendingAssets";
import PerformanceChart from "../components/charts/PerformanceChart";

export default function DashboardPage() {
  const { tokens: t } = useTheme();
  const s = makeStyles(t);

  return (
    <div style={s.content}>
      {/* Page header */}
      <div style={s.pageHeader}>
        <div>
          <h1 style={s.pageTitle}>Market Overview</h1>
          <p style={s.pageSub}>Track sentiment, trends, and movement across alternative assets.</p>
        </div>
        {/* <div style={s.pageActions}>
          <button style={s.btnOutline}>Generate Report</button>
          <button style={s.btnPrimary}>✦ AI Analysis</button>
        </div> */}
      </div>

      <StatsRow />

      <div style={s.chartsRow}>
        <PerformanceChart />
        <InsightsPanel />
      </div>

      <TrendingAssets />
    </div>
  );
}
