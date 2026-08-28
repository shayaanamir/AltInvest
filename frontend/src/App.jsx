import { BrowserRouter, Routes, Route, useNavigate, useLocation, Navigate } from "react-router-dom";
import { ThemeProvider } from "./context/ThemeContext";
import "./styles/tokens.css";
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
import SettingsPage from "./pages/SettingsPage";
import ProfilePage from "./pages/ProfilePage";

const BARE_PAGES = ["Landing", "Login", "Signup", "Onboarding"];

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
    case "Profile": return "/profile";
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
  if (pathname.startsWith("/profile")) return "Profile";
  return "Dashboard";
};

function ShellRoutes() {
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
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="/profile" element={<ProfilePage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );

  if (isBare) {
    return pageContent;
  }

  return (
    <div
      className="sv2"
      style={{
        display: "flex",
        height: "100vh",
        width: "100vw",
        background: "var(--sv2-bg)",
        fontFamily: "'DM Sans','Segoe UI',sans-serif",
        color: "var(--sv2-text)",
        overflow: "hidden",
        transition: "background 0.25s, color 0.25s",
      }}
    >
      <Sidebar activePage={activePage} onNavigate={navigate} />
      <div style={{
        flex: 1, display: "flex", flexDirection: "column",
        overflow: "hidden", background: "var(--sv2-bg)", transition: "background 0.25s",
      }}>
        <Topbar />
        <div style={{ flex: 1, overflow: "auto", padding: "40px 40px 20px" }}>
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