import { useLocation, useNavigate } from "react-router-dom";
import { isAuthenticated } from "../hooks/useAuth";

/** Shown for any URL that isn't a page. Inside the app shell when signed in, on its own otherwise. */
export default function NotFoundPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const signedIn = isAuthenticated();

  return (
    <div className="sv2">
      <div className={signedIn ? "sv2-page" : "sv2-page nf-standalone"}>
        <div className="nf-card sv2-card">
          <div className="nf-code">404</div>
          <h1 className="sv2-h1" style={{ marginTop: 0 }}>This page doesn&apos;t exist</h1>
          <p className="sv2-lead">
            Nothing lives at <code className="nf-path">{location.pathname}</code>. The link may be old or mistyped.
          </p>
          <div className="nf-actions">
            <button type="button" className="sv2-btn-outline" style={{ width: "auto" }} onClick={() => navigate(-1)}>
              Go back
            </button>
            <button type="button" className="set-btn-accent" onClick={() => navigate(signedIn ? "/dashboard" : "/", { replace: true })}>
              {signedIn ? "Go to the dashboard" : "Go to the home page"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
