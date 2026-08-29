import { useNavigate } from "react-router-dom";
import { IconFolder, IconStar, IconBell } from "../icons";

const ITEMS = [
  { key: "holdingsCount", label: "Holdings", icon: "folder" },
  { key: "watchlistsCount", label: "Watchlists", icon: "star" },
  { key: "alertsCount", label: "Alerts", icon: "bell" },
];

const ICONS = {
  folder: <IconFolder size={16} />,
  star: <IconStar size={16} />,
  bell: <IconBell size={16} />,
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