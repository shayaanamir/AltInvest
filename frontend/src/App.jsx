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

// Pages that skip the app shell (no sidebar/topbar)
const BARE_PAGES = ["Landing", "Login", "Signup"];

function Shell() {
  const { tokens: t } = useTheme();
  const s = makeStyles(t);
  const [activePage, setActivePage] = useState("Landing");

  const renderPage = () => {
    switch (activePage) {
      case "Landing":
        return <LandingPage onNavigate={setActivePage} />;
      case "Login":
        return <LoginPage onNavigate={setActivePage} />;
      case "Signup":
        return <SignupPage onNavigate={setActivePage} />;
      case "Portfolio":
        return <PortfolioPage />;
      case "Asset Detail":
        return <AssetDetailPage onNavigate={setActivePage} />;
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
      <Sidebar activePage={activePage} onNavigate={setActivePage} />
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