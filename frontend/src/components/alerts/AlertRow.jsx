import { relativeTime } from "../../utils/dateTime";
import { IconTrash, IconPlay, IconPause, IconPencil } from "../icons";
import ToggleSwitch from "../shared/ToggleSwitch";

export default function AlertRow({ alert, onToggle, onEdit, onDelete }) {
  const isPaused = alert.status === "paused";
  // The icon shows the action a click performs: pause a running alert, resume a paused one,
  // re-arm one that has already fired.
  const isRunning = alert.status === "active";
  const quickActionLabel = isRunning ? "Pause alert" : alert.status === "triggered" ? "Re-arm alert" : "Resume alert";
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
        <button
          className="alr-icon-btn"
          title={quickActionLabel}
          aria-label={quickActionLabel}
          onClick={() => onToggle(alert.id, isRunning ? "paused" : "active")}
        >
          {isRunning ? <IconPause /> : <IconPlay />}
        </button>
        <ToggleSwitch
          checked={!isPaused}
          onChange={() => onToggle(alert.id)}
          label="Toggle alert"
        />
        <button className="alr-icon-btn" title="Edit alert" aria-label="Edit alert" onClick={() => onEdit(alert.id)}>
          <IconPencil />
        </button>
        <button className="alr-icon-btn" title="Delete alert" aria-label="Delete alert" onClick={() => onDelete(alert.id)}>
          <IconTrash />
        </button>
      </div>
    </div>
  );
}