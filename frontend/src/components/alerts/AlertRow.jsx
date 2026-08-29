import { relativeTime } from "../../utils/dateTime";
import { IconTrash, IconPlay, IconPause, IconPencil } from "../icons";

export default function AlertRow({ alert, onToggle, onEdit, onDelete }) {
  const isPaused = alert.status === "paused";
  const dateLine =
    alert.status === "triggered" && alert.lastTriggeredAt
      ? `triggered ${relativeTime(alert.lastTriggeredAt)}`
      : `created ${(alert.createdAt || "").slice(0, 10)}`;

  return (
    <div className="alr-row">
      <div className="alr-avatar" style={{ background: alert.avatarColor }}>
        {alert.avatarSymbol}
      </div>
      <div className="alr-info">
        <div className="alr-name">{alert.name}</div>
        <div className="alr-condition">{alert.conditionText}</div>
      </div>
      <span className="alr-channel-badge">{alert.deliveryChannel}</span>
      <span className="alr-date">{dateLine}</span>
      <div className="alr-actions">
        <button className="alr-icon-btn" title={isPaused ? "Paused" : "Running"} disabled>
          {isPaused ? <IconPause /> : <IconPlay />}
        </button>
        <button
          className={`alr-toggle ${!isPaused ? "on" : ""}`}
          onClick={() => onToggle(alert.id)}
          aria-label="Toggle alert"
        >
          <span className="alr-toggle-thumb" />
        </button>
        <button className="alr-icon-btn" onClick={() => onEdit(alert.id)}>
          <IconPencil />
        </button>
        <button className="alr-icon-btn" onClick={() => onDelete(alert.id)}>
          <IconTrash />
        </button>
      </div>
    </div>
  );
}