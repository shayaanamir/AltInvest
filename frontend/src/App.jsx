import { useEffect } from "react";
import { BrowserRouter, Routes, Route, useNavigate, useLocation, Navigate } from "react-router-dom";
import { ThemeProvider } from "./context/ThemeContext";
import "./styles/tokens.css";
import Sidebar from "./components/layout/Sidebar";
import Topbar from "./components/layout/Topbar";
import { ROUTES, BARE_PAGES, getPath, getPageName } from "./routes";
import { ensureDevSession } from "./hooks/useAuth";

function ShellRoutes() {
  const location = useLocation();
  const navigateRouter = useNavigate();

  const activePage = getPageName(location.pathname);
  const isBare = BARE_PAGES.includes(activePage);

  const navigate = (page) => navigateRouter(getPath(page));

  const pageContent = (
    <Routes>
      {ROUTES.map(({ key, path, element: Element }) => (
        <Route
          key={key}
          path={path}
          element={
            key === "Landing" || key === "Login" || key === "Onboarding" ? <Element onNavigate={navigate} />
            : key === "Signup" ? <Element onNavigate={(p) => navigate(p === "Dashboard" ? "Onboarding" : p)} />
            : key === "Asset Detail" ? <Element onNavigate={navigate} />
            : <Element />
          }
        />
      ))}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );

  if (isBare) return pageContent;

  return (
    <div className="sv2" style={{ display: "flex", height: "100vh", width: "100vw", background: "var(--sv2-bg)", fontFamily: "'DM Sans','Segoe UI',sans-serif", color: "var(--sv2-text)", overflow: "hidden", transition: "background 0.25s, color 0.25s" }}>
      <Sidebar activePage={activePage} onNavigate={navigate} />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", background: "var(--sv2-bg)", transition: "background 0.25s" }}>
        <Topbar />
        <div style={{ flex: 1, overflow: "auto", padding: "40px 40px 20px" }}>{pageContent}</div>
      </div>
    </div>
  );
}

export default function App() {
  // TEMPORARY — see hooks/useAuth.js. Ensures every user-scoped fetch has a
  // valid JWT before the person clicks anything. Remove once a real login
  // screen is the actual entry point into the app.
  // useEffect(() => {
  //   ensureDevSession().catch(() => {
  //     // Swallow here — individual apiFetch calls will surface a clear error
  //     // (401 → clearSession) if something's genuinely wrong with the seed.
  //   });
  // }, []);

  return (
    <ThemeProvider>
      <BrowserRouter>
        <ShellRoutes />
      </BrowserRouter>
    </ThemeProvider>
  );
}