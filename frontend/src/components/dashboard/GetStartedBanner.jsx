import { useState, useEffect } from "react";
import { dashboardApi } from "../../services/dashboardApi";

export default function GetStartedBanner() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    dashboardApi.getMarketStats().then(setStats).catch(console.error);
  }, []);

  // Only shows once the person actually has zero tracked holdings.
  if (!stats || stats.holdingsCount > 0) return null;

  return (
    <div className="sv2-card dv2-getstarted">
      <div className="dv2-getstarted-icon" aria-hidden="true">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 7H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z" />
          <path d="M16 7V5a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v2" />
          <circle cx="16" cy="13" r="1.4" fill="currentColor" stroke="none" />
        </svg>
      </div>
      <div className="dv2-getstarted-body">
        <p className="dv2-getstarted-title">Get started</p>
        <p className="dv2-getstarted-desc">
          Your dashboard becomes personal once it knows what you own. Add a position, or browse the
          universe first — nothing here is fabricated for you.
        </p>
      </div>
      <div className="dv2-getstarted-actions">
        <button className="dv2-btn-accent" type="button">+ Add your first holding</button>
        <button className="dv2-btn-ghost" type="button">⌕ Explore Discover</button>
      </div>
    </div>
  );
}