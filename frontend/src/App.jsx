import { useEffect, useState, useRef } from "react";
import { BrowserRouter, Routes, Route, useNavigate, useLocation, Navigate } from "react-router-dom";
import { ThemeProvider } from "./context/ThemeContext";
import "./styles/tokens.css";
import Sidebar from "./components/layout/Sidebar";
import Topbar from "./components/layout/Topbar";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import SessionExpiredModal from "./components/auth/SessionExpiredModal";
import { onSessionExpired } from "./hooks/sessionEvents";
import { ROUTES, BARE_PAGES, getPath, getPageName } from "./routes";

function ShellRoutes() {
  const location = useLocation();
  const navigateRouter = useNavigate();
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
          key === "Landing" || key === "Login" || key === "Onboarding" ? <Element onNavigate={navigate} />
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

  const shell = isBare ? pageContent : (
    <div className="sv2" style={{ display: "flex", height: "100vh", width: "100vw", background: "var(--sv2-bg)", fontFamily: "'DM Sans','Segoe UI',sans-serif", color: "var(--sv2-text)", overflow: "hidden", transition: "background 0.25s, color 0.25s" }}>
      <Sidebar activePage={activePage} onNavigate={navigate} />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", background: "var(--sv2-bg)", transition: "background 0.25s" }}>
        <Topbar />
        <div style={{ flex: 1, overflow: "auto", padding: "40px 40px 20px" }}>{pageContent}</div>
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
      <BrowserRouter>
        <ShellRoutes />
      </BrowserRouter>
    </ThemeProvider>
  );
}