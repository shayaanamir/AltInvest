import { BrowserRouter, Routes, Route, useNavigate, useLocation, Navigate } from "react-router-dom";
import { ThemeProvider, useTheme } from "./context/ThemeContext";
import { makeStyles } from "./styles/makeStyles";
import "./styles/sentiment.css";
import Sidebar from "./components/layout/Sidebar";
import Topbar from "./components/layout/Topbar";
import DashboardPage from "./pages/DashboardPage";
import PortfolioPage from "./pages/PortfolioPage";
import AssetDetailPage from "./pages/AssetDetailPage";
import SentimentPage from "./pages/SentimentPage";
import DiscoverPage from "./pages/DiscoverPage";
import WatchlistsPage from "./pages/WatchlistsPage";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/auth/LoginPage";
import SignupPage from "./pages/auth/SignupPage";
import OnboardingPage from "./pages/onboarding/OnboardingPage";
import ComparePage from "./pages/ComparePage";
import AlertsPage from "./pages/AlertsPage";

const BARE_PAGES = ["Landing", "Login", "Signup", "Onboarding"];

function PlaceholderPage({ title, description }) {
  return (
    <div style={{
      maxWidth: 500, margin: "60px auto", textAlign: "center",
      display: "flex", flexDirection: "column", gap: 16, alignItems: "center",
      border: "1px dashed var(--sv2-border, rgba(0,0,0,0.1))", borderRadius: 16,
      padding: "40px 30px", background: "var(--sv2-card, #ffffff)",
      fontFamily: "'DM Sans', sans-serif"
    }}>
      <div style={{
        fontSize: 32, width: 64, height: 64, borderRadius: "50%",
        background: "var(--sv2-accent-soft, rgba(191,93,56,0.1))", color: "var(--sv2-accent, #bf5d38)",
        display: "flex", alignItems: "center", justifyContent: "center"
      }}>
        ✦
      </div>
      <div>
        <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0, color: "var(--sv2-text, #24211c)" }}>{title} Desk</h2>
        <p style={{ fontSize: 13, color: "var(--sv2-text-soft, #6c6555)", marginTop: 8, lineHeight: 1.5 }}>
          {description || `The ${title} engine is running sync tests. Full asset mapping will be active soon.`}
        </p>
      </div>
    </div>
  );
}

const getPath = (page) => {
  switch (page) {
    case "Landing": return "/";
    case "Login": return "/login";
    case "Signup": return "/signup";
    case "Onboarding": return "/onboarding";
    case "Portfolio": return "/portfolio";
    case "Asset Detail": return "/asset-detail";
    case "Sentiment": return "/sentiment";
    case "Dashboard": return "/dashboard";
    case "Discover": return "/discover";
    case "Compare": return "/compare";
    case "Watchlists": return "/watchlists";
    case "Alerts": return "/alerts";
    case "Settings": return "/settings";
    default: return "/";
  }
};

const getPageName = (pathname) => {
  if (pathname === "/") return "Landing";
  if (pathname.startsWith("/login")) return "Login";
  if (pathname.startsWith("/signup")) return "Signup";
  if (pathname.startsWith("/onboarding")) return "Onboarding";
  if (pathname.startsWith("/portfolio")) return "Portfolio";
  if (pathname.startsWith("/asset-detail")) return "Asset Detail";
  if (pathname.startsWith("/sentiment")) return "Sentiment";
  if (pathname.startsWith("/dashboard")) return "Dashboard";
  if (pathname.startsWith("/discover")) return "Discover";
  if (pathname.startsWith("/compare")) return "Compare";
  if (pathname.startsWith("/watchlists")) return "Watchlists";
  if (pathname.startsWith("/alerts")) return "Alerts";
  if (pathname.startsWith("/settings")) return "Settings";
  return "Dashboard";
};

function ShellRoutes() {
  const { tokens: t } = useTheme();
  const s = makeStyles(t);

  const location = useLocation();
  const navigateRouter = useNavigate();

  const activePage = getPageName(location.pathname);
  const isBare = BARE_PAGES.includes(activePage);

  const navigate = (page) => {
    navigateRouter(getPath(page));
  };

  const pageContent = (
    <Routes>
      <Route path="/" element={<LandingPage onNavigate={navigate} />} />
      <Route path="/login" element={<LoginPage onNavigate={navigate} />} />
      <Route path="/signup" element={<SignupPage onNavigate={(p) => navigate(p === "Dashboard" ? "Onboarding" : p)} />} />
      <Route path="/onboarding" element={<OnboardingPage onNavigate={navigate} />} />
      <Route path="/portfolio" element={<PortfolioPage />} />
      <Route path="/asset-detail" element={<AssetDetailPage onNavigate={navigate} />} />
      <Route path="/sentiment" element={<SentimentPage />} />
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/discover" element={<DiscoverPage />} />
      <Route path="/watchlists" element={<WatchlistsPage />} />
      <Route path="/compare" element={<ComparePage />} />
      <Route path="/alerts" element={<AlertsPage />} />
      <Route path="/settings" element={<PlaceholderPage title="Settings" description="Customize display currency, appearance theme preferences, notification channels, and connect Web3 wallets." />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );

  if (isBare) {
    return pageContent;
  }

  return (
    <div className="sv2" style={s.root}>
      <Sidebar activePage={activePage} onNavigate={navigate} />
      <div style={s.main}>
        <Topbar />
        <div style={s.content}>
          {pageContent}
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <ShellRoutes />
      </BrowserRouter>
    </ThemeProvider>
  );
}