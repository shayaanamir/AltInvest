import { useState } from "react";
import { ThemeProvider, useTheme } from "./context/ThemeContext";
import { makeStyles } from "./styles/makeStyles";
import Sidebar from "./components/layout/Sidebar";
import Topbar from "./components/layout/Topbar";
import DashboardPage from "./pages/DashboardPage";
import PortfolioPage from "./pages/PortfolioPage";
import AssetDetailPage from "./pages/AssetDetailPage";

function Shell() {
  const { tokens: t } = useTheme();
  const s = makeStyles(t);
  const [activePage, setActivePage] = useState("Dashboard");

  const renderPage = () => {
    switch (activePage) {
      case "Portfolio":
        return <PortfolioPage />;
      case "Asset Detail":
        return <AssetDetailPage onNavigate={setActivePage} />;
      case "Dashboard":
      default:
        return <DashboardPage />;
    }
  };

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