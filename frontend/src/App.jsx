import { useState } from "react";
import { ThemeProvider, useTheme } from "./context/ThemeContext";
import { makeStyles } from "./styles/makeStyles";
import Sidebar from "./components/layout/Sidebar";
import Topbar from "./components/layout/Topbar";
import DashboardPage from "./pages/DashboardPage";
import PortfolioPage from "./pages/PortfolioPage";
import AssetDetailPage from "./pages/AssetDetailPage";
import SentimentPage from "./pages/SentimentPage";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/auth/LoginPage";
import SignupPage from "./pages/auth/SignupPage";
import OnboardingPage from "./pages/onboarding/OnboardingPage";

// Pages that render without sidebar/topbar shell
const BARE_PAGES = ["Landing", "Login", "Signup", "Onboarding"];

function Shell() {
  const { tokens: t } = useTheme();
  const s = makeStyles(t);
  const [activePage, setActivePage] = useState("Landing");

  const navigate = (page) => setActivePage(page);

  const renderPage = () => {
    switch (activePage) {
      case "Landing":
        return <LandingPage onNavigate={navigate} />;
      case "Login":
        return <LoginPage onNavigate={navigate} />;
      case "Signup":
        // After signup → Onboarding (not Dashboard)
        return <SignupPage onNavigate={(p) => navigate(p === "Dashboard" ? "Onboarding" : p)} />;
      case "Onboarding":
        return <OnboardingPage onNavigate={navigate} />;
      case "Portfolio":
        return <PortfolioPage />;
      case "Asset Detail":
        return <AssetDetailPage onNavigate={navigate} />;
      case "Sentiment":
        return <SentimentPage />;
      case "Dashboard":
      default:
        return <DashboardPage />;
    }
  };

  const isBare = BARE_PAGES.includes(activePage);

  if (isBare) {
    return renderPage();
  }

  return (
    <div style={s.root}>
      <Sidebar activePage={activePage} onNavigate={navigate} />
      <div style={s.main}>
        <Topbar />
        {renderPage()}
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <Shell />
    </ThemeProvider>
  );
}