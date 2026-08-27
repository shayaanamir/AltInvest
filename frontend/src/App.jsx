import { BrowserRouter, Routes, Route, useNavigate, useLocation, Navigate } from "react-router-dom";
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

const BARE_PAGES = ["Landing", "Login", "Signup", "Onboarding"];

// Map logical string paths to router paths
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
  return "Dashboard";
};

function ShellRoutes() {
  const { tokens: t } = useTheme();
  const s = makeStyles(t);
  
  const location = useLocation();
  const navigateRouter = useNavigate();
  
  const activePage = getPageName(location.pathname);
  const isBare = BARE_PAGES.includes(activePage);

  // Wrapper around react-router navigate to support legacy string navigation
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
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );

  if (isBare) {
    return pageContent;
  }

  return (
    <div style={s.root}>
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