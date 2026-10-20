import DashboardPage from "./pages/DashboardPage";
import PortfolioPage from "./pages/PortfolioPage";
import AssetDetailPage from "./pages/AssetDetailPage";
import SentimentPage from "./pages/SentimentPage";
import DiscoverPage from "./pages/DiscoverPage";
import WatchlistsPage from "./pages/WatchlistsPage";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import VerifyEmailPage from "./pages/VerifyEmailPage";
import OnboardingPage from "./pages/OnboardingPage";
import ComparePage from "./pages/ComparePage";
import AlertsPage from "./pages/AlertsPage";
import SettingsPage from "./pages/SettingsPage";
import ProfilePage from "./pages/ProfilePage";
import NotificationsPage from "./pages/NotificationsPage";

export const ROUTES = [
  { key: "Landing", path: "/", element: LandingPage, bare: true, inNav: false },
  { key: "Login", path: "/login", element: LoginPage, bare: true, inNav: false },
  { key: "Signup", path: "/signup", element: SignupPage, bare: true, inNav: false },
  { key: "ForgotPassword", path: "/forgot-password", element: ForgotPasswordPage, bare: true, inNav: false },
  { key: "ResetPassword", path: "/reset-password", element: ResetPasswordPage, bare: true, inNav: false },
  { key: "VerifyEmail", path: "/verify-email", element: VerifyEmailPage, bare: true, inNav: false },
  { key: "Onboarding", path: "/onboarding", element: OnboardingPage, bare: true, inNav: false, protected: true },
  { key: "Dashboard", path: "/dashboard", element: DashboardPage, inNav: true, icon: "Dashboard", protected: true },
  { key: "Discover", path: "/discover", element: DiscoverPage, inNav: true, icon: "Discover", protected: true },
  { key: "Sentiment", path: "/sentiment", element: SentimentPage, inNav: true, icon: "Sentiment", protected: true },
  { key: "Compare", path: "/compare", element: ComparePage, inNav: true, icon: "Compare", protected: true },
  { key: "Portfolio", path: "/portfolio", element: PortfolioPage, inNav: true, icon: "Portfolio", protected: true },
  { key: "Watchlists", path: "/watchlists", element: WatchlistsPage, inNav: true, icon: "Watchlists", protected: true },
  { key: "Alerts", path: "/alerts", element: AlertsPage, inNav: true, icon: "Alerts", protected: true },
  { key: "Asset Detail", path: "/asset-detail", element: AssetDetailPage, inNav: false, protected: true },
  { key: "Notifications", path: "/notifications", element: NotificationsPage, inNav: false, bottomNav: true, icon: "Notifications", protected: true },
  { key: "Profile", path: "/profile", element: ProfilePage, inNav: false, bottomNav: true, icon: "Profile", protected: true },
  { key: "Settings", path: "/settings", element: SettingsPage, inNav: false, bottomNav: true, icon: "Settings", protected: true },
];

export const NAV_ITEMS = ROUTES.filter((r) => r.inNav);
export const BOTTOM_NAV = ROUTES.filter((r) => r.bottomNav);
export const BARE_PAGES = ROUTES.filter((r) => r.bare).map((r) => r.key);

export function getPath(pageKey) {
  return ROUTES.find((r) => r.key === pageKey)?.path ?? "/";
}

// The page a URL belongs to: its exact path (a trailing "/" is ignored). Anything else is "NotFound",
// matching what the router renders (prefix matching used to call "/dashboardx" the dashboard).
export function getPageName(pathname) {
  const path = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
  if (path === "/") return "Landing";
  const match = ROUTES.find((r) => r.path !== "/" && path === r.path);
  return match?.key ?? "NotFound";
}