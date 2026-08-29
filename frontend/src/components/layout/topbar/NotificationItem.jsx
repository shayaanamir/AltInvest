import { timeAgo } from "../../../utils/dateTime";

const TYPE_LABEL = {
  alert_triggered: "Alert",
  market_event: "Market",
  system: "System",
};

export default function NotificationItem({ notification, onSelect }) {
  return (
    <button
      type="button"
      className={`tb-notification-item ${notification.read ? "" : "unread"}`}
      onClick={onSelect}
    >
      <span className="tb-notification-dot" />
      <div className="tb-notification-text">
        <div className="tb-notification-title-row">
          <span className="tb-notification-type">{TYPE_LABEL[notification.type] || "Update"}</span>
          <span className="tb-notification-time">{timeAgo(notification.timestamp)}</span>
        </div>
        <div className="tb-notification-title">{notification.title}</div>
      </div>
    </button>
  );
}