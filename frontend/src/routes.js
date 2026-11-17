import { lazy } from "react";

// Each page is its own chunk, loaded when its route is first opened (App.jsx shows a fallback meanwhile).
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const PortfolioPage = lazy(() => import("./pages/PortfolioPage"));
const AssetDetailPage = lazy(() => import("./pages/AssetDetailPage"));
const NftCollectionPage = lazy(() => import("./pages/NftCollectionPage"));
const SentimentPage = lazy(() => import("./pages/SentimentPage"));
const DiscoverPage = lazy(() => import("./pages/DiscoverPage"));
const WatchlistsPage = lazy(() => import("./pages/WatchlistsPage"));
const LandingPage = lazy(() => import("./pages/LandingPage"));
const LoginPage = lazy(() => import("./pages/LoginPage"));
const SignupPage = lazy(() => import("./pages/SignupPage"));
const ForgotPasswordPage = lazy(() => import("./pages/ForgotPasswordPage"));
const ResetPasswordPage = lazy(() => import("./pages/ResetPasswordPage"));
const VerifyEmailPage = lazy(() => import("./pages/VerifyEmailPage"));
const OnboardingPage = lazy(() => import("./pages/OnboardingPage"));
const ComparePage = lazy(() => import("./pages/ComparePage"));
const AlertsPage = lazy(() => import("./pages/AlertsPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const ProfilePage = lazy(() => import("./pages/ProfilePage"));
const NotificationsPage = lazy(() => import("./pages/NotificationsPage"));

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
  { key: "NFT Collection", path: "/nft-collection", element: NftCollectionPage, inNav: false, protected: true },
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