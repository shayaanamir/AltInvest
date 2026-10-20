import { timeAgo } from "../../../utils/dateTime";
import { NOTIFICATION_TYPE_LABELS } from "../../../services/notificationsApi";
import { IconX } from "../../icons";

/** One notification row. `full` also shows the message (Notifications page). */
export default function NotificationItem({ notification, onSelect, onDismiss, full = false }) {
  return (
    <div className={`tb-notification-item ${notification.read ? "" : "unread"} ${full ? "full" : ""}`}>
      <button type="button" className="tb-notification-main" onClick={onSelect}>
        <span className="tb-notification-dot" aria-label={notification.read ? undefined : "Unread"} />
        <div className="tb-notification-text">
          <div className="tb-notification-title-row">
            <span className="tb-notification-type">{NOTIFICATION_TYPE_LABELS[notification.type] || "Update"}</span>
            <span className="tb-notification-time">{timeAgo(notification.timestamp)}</span>
          </div>
          <div className="tb-notification-title">{notification.title}</div>
          {full && notification.message && <div className="tb-notification-message">{notification.message}</div>}
        </div>
      </button>
      {onDismiss && (
        <button type="button" className="tb-notification-dismiss" onClick={onDismiss} title="Dismiss" aria-label={`Dismiss: ${notification.title}`}>
          <IconX size={11} />
        </button>
      )}
    </div>
  );
}
