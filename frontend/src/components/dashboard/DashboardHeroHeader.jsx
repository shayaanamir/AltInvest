import { useState, useEffect } from "react";
import { dashboardApi } from "../../services/dashboardApi";

export default function DashboardHeroHeader() {
  const [userName, setUserName] = useState(null);

  useEffect(() => {
    dashboardApi.getCurrentUser().then((u) => setUserName(u.name)).catch(console.error);
  }, []);

  return (
    <div className="dv2-hero">
      <div>
        <h1 className="dv2-hero-title">Market overview</h1>
        <p className="dv2-hero-sub">
          {userName
            ? `${userName.split(" ")[0]}, here's how your markets look right now.`
            : "Here's how your markets look right now."}
        </p>
      </div>
      <div className="dv2-hero-actions">
        <button className="dv2-btn-ghost" type="button">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" className="bi bi-file-earmark-text" viewBox="0 0 16 16">
            <path d="M5.5 7a.5.5 0 0 0 0 1h5a.5.5 0 0 0 0-1zM5 9.5a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5m0 2a.5.5 0 0 1 .5-.5h2a.5.5 0 0 1 0 1h-2a.5.5 0 0 1-.5-.5"/>
            <path d="M9.5 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4.5zm0 1v2A1.5 1.5 0 0 0 11 4.5h2V14a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1z"/>
          </svg>
          Generate report
        </button>
        <button className="dv2-btn-accent" type="button">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" className="bi bi-sparkle" viewBox="0 0 10 10">
            <path d="M5 1 Q5.8 4.2 9 5 Q5.8 5.8 5 9 Q4.2 5.8 1 5 Q4.2 4.2 5 1z" />
          </svg>
          AI analysis
        </button>
      </div>
    </div>
  );
}