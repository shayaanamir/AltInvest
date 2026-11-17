import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "../styles/dashboard.css";
import DashboardHeroHeader from "../components/dashboard/DashboardHeroHeader";
import GetStartedBanner from "../components/dashboard/GetStartedBanner";
import DashboardStatCards from "../components/dashboard/DashboardStatCards";
import PortfolioPerformanceCard from "../components/dashboard/PortfolioPerformanceCard";
import MarketInsightsCard from "../components/dashboard/MarketInsightsCard";
import TrendingAssetsSection from "../components/dashboard/TrendingAssetsSection";
import TrendingCollectionsSection from "../components/dashboard/TrendingCollectionsSection";
import { ErrorBoundary } from "../errors";
import { useAppPreferences } from "../services/appPreferences";
import { getFocus, rowKind } from "../utils/homeFocus";

// Every widget loads its own data and sits in its own error boundary, so a home focus can show,
// hide and reorder them freely (utils/homeFocus.js decides which, and in what order).
const WIDGETS = {
  stats: () => <ErrorBoundary variant="section" label="Market stats"><DashboardStatCards /></ErrorBoundary>,
  performance: () => <ErrorBoundary variant="section" label="Portfolio performance"><PortfolioPerformanceCard /></ErrorBoundary>,
  insights: () => <ErrorBoundary variant="section" label="Market insights"><MarketInsightsCard /></ErrorBoundary>,
  assets: () => <ErrorBoundary variant="section" label="Trending assets"><TrendingAssetsSection /></ErrorBoundary>,
  collections: () => <ErrorBoundary variant="section" label="Trending collections"><TrendingCollectionsSection /></ErrorBoundary>,
};

function Row({ row }) {
  const kind = rowKind(row);
  const widgets = row.map((id) => <div key={id} className="dv2-widget">{WIDGETS[id]()}</div>);
  if (kind === "stats") return <>{widgets}</>;
  const single = row.length === 1 ? ` dv2-${kind}-grid--single` : "";
  return <div className={`dv2-${kind}-grid${single}`}>{widgets}</div>;
}

export default function DashboardPage() {
  const { loaded, dashboardFocus } = useAppPreferences();
  const navigate = useNavigate();

  // The saved focus arrives a moment after sign-in on a fresh page load. Wait for it so the wrong
  // layout doesn't flash, but not forever: if settings can't be read, the default layout shows.
  const [gaveUp, setGaveUp] = useState(false);
  useEffect(() => {
    if (loaded) return undefined;
    const t = setTimeout(() => setGaveUp(true), 2500);
    return () => clearTimeout(t);
  }, [loaded]);

  const focus = getFocus(dashboardFocus);

  return (
    <div className="sv2">
      <div className="sv2-page">
        <DashboardHeroHeader />
        <GetStartedBanner />

        {loaded || gaveUp ? (
          <>
            {focus.rows.map((row) => <Row key={row.join("+")} row={row} />)}
            <p className="dv2-focus-note">
              Home focus: <strong>{focus.label}</strong> · {focus.blurb}.{" "}
              <button type="button" className="dv2-focus-link" onClick={() => navigate("/settings")}>
                Change in Settings
              </button>
            </p>
          </>
        ) : (
          <div className="sv2-muted sv2-small">Loading your dashboard…</div>
        )}
      </div>
    </div>
  );
}
