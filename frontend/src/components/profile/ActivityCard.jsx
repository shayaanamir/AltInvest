import { useNavigate } from "react-router-dom";

const ITEMS = [
  { key: "holdingsCount", label: "Holdings", icon: "folder" },
  { key: "watchlistsCount", label: "Watchlists", icon: "star" },
  { key: "alertsCount", label: "Alerts", icon: "bell" },
];

const ICONS = {
  folder: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
    </svg>
  ),
  star: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2.5l2.9 6.4 6.9.7-5.2 4.7 1.5 6.9L12 17.6l-6.1 3.6 1.5-6.9-5.2-4.7 6.9-.7z" />
    </svg>
  ),
  bell: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8a6 6 0 10-12 0c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.7 21a2 2 0 01-3.4 0" />
    </svg>
  ),
};

export default function ActivityCard({ activitySummary }) {
  const navigate = useNavigate();
  if (!activitySummary) return null;

  return (
    <div className="sv2-card set-subcard prof-activity-card">
      <div className="prof-activity-label">Activity</div>
      <div className="prof-activity-list">
        {ITEMS.map((item) => (
          <div key={item.key} className="prof-activity-row">
            <span className="prof-activity-icon">{ICONS[item.icon]}</span>
            <span className="prof-activity-name">{item.label}</span>
            <span className="prof-activity-count">{activitySummary[item.key] ?? 0}</span>
          </div>
        ))}
      </div>
      <button className="set-link-btn prof-open-settings" onClick={() => navigate("/settings")}>
        Open settings →
      </button>
    </div>
  );
}