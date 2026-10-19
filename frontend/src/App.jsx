import { useEffect, useState, useRef } from "react";
import { BrowserRouter, Routes, Route, useNavigate, useLocation, Navigate } from "react-router-dom";
import { ThemeProvider, useTheme } from "./context/ThemeContext";
import "./styles/tokens.css";
import Sidebar from "./components/layout/Sidebar";
import Topbar from "./components/layout/Topbar";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import SessionExpiredModal from "./components/auth/SessionExpiredModal";
import { ErrorBoundary, ConnectionBanner, ToastProvider } from "./errors";
import { onSessionExpired } from "./hooks/sessionEvents";
import { isAuthenticated } from "./hooks/useAuth";
import { loadAppPreferences, resetAppPreferences, useAppPreferences, getDisplayCurrency } from "./services/appPreferences";
import { ROUTES, BARE_PAGES, getPath, getPageName } from "./routes";

// Applies the saved settings that act on the whole app: loads them once the user is signed in,
// then sets the theme (density and date format are read from the same store).
function PreferencesBridge() {
  const location = useLocation();
  const { loaded, theme } = useAppPreferences();
  const { setTheme } = useTheme();

  useEffect(() => {
    if (isAuthenticated()) {
      if (!loaded) loadAppPreferences().catch(() => {}); // settings are optional; defaults apply if this fails
    } else if (loaded) {
      resetAppPreferences();
    }
  }, [location.pathname, loaded]);

  useEffect(() => {
    if (theme) setTheme(theme);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [theme]);

  return null;
}

function ShellRoutes() {
  const location = useLocation();
  const navigateRouter = useNavigate();
  useAppPreferences(); // re-render when the display currency changes
  const [sessionExpired, setSessionExpired] = useState(false);

  // Track the current path so the modal's "Sign In" button can send the
  // person back to where they were once they re-authenticate.
  const currentPathRef = useRef(location.pathname + location.search);
  currentPathRef.current = location.pathname + location.search;

  useEffect(() => {
    return onSessionExpired(() => setSessionExpired(true));
  }, []);

  const activePage = getPageName(location.pathname);
  const isBare = BARE_PAGES.includes(activePage);

  const navigate = (page) => navigateRouter(getPath(page));

  const handleSessionExpiredConfirm = () => {
    setSessionExpired(false);
    const returnPath = currentPathRef.current;
    navigateRouter(`/login?return=${encodeURIComponent(returnPath)}`);
  };

  const pageContent = (
    <Routes>
      {ROUTES.map(({ key, path, element: Element, protected: isProtected }) => {
        const inner =
          key === "Landing" || key === "Login" || key === "Onboarding"
            || key === "ForgotPassword" || key === "ResetPassword" ? <Element onNavigate={navigate} />
            : key === "Signup" ? <Element onNavigate={(p) => navigate(p === "Dashboard" ? "Onboarding" : p)} />
              : key === "Asset Detail" ? <Element onNavigate={navigate} />
                : <Element />;

        return (
          <Route
            key={key}
            path={path}
            element={isProtected ? <ProtectedRoute>{inner}</ProtectedRoute> : inner}
          />
        );
      })}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );

  // Changing the display currency (or rates arriving) re-mounts the page so every amount is redone.
  const fx = getDisplayCurrency();
  const wrappedPageContent = (
    <ErrorBoundary key={`${location.pathname}|${fx.code}|${fx.asOf}`} resetKey={location.pathname}>
      {pageContent}
    </ErrorBoundary>
  );

  const shell = isBare ? <><ConnectionBanner />{wrappedPageContent}</> : (
    <div className="sv2" style={{ display: "flex", height: "100vh", width: "100vw", background: "var(--sv2-bg)", fontFamily: "'DM Sans','Segoe UI',sans-serif", color: "var(--sv2-text)", overflow: "hidden", transition: "background 0.25s, color 0.25s" }}>
      <Sidebar activePage={activePage} onNavigate={navigate} />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", background: "var(--sv2-bg)", transition: "background 0.25s" }}>
        <Topbar />
        <ConnectionBanner />
        <div className="app-content">{wrappedPageContent}</div>
      </div>
    </div>
  );

  return (
    <>
      {shell}
      {sessionExpired && <SessionExpiredModal onConfirm={handleSessionExpiredConfirm} />}
    </>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <ToastProvider>
        <BrowserRouter>
          <PreferencesBridge />
          <ShellRoutes />
        </BrowserRouter>
      </ToastProvider>
    </ThemeProvider>
  );
}