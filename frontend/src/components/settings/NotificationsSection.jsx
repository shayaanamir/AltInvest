import SettingsRow from "./SettingsRow";
import ToggleSwitch from "./ToggleSwitch";

// The browser's timezone, so quiet hours mean the user's own night (the server checks them in it).
const browserTimezone = () => {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
};

// Only settings the server acts on are shown (audit G-23): triggered alerts always appear in the
// notification center; Email and Quiet hours decide whether, and when, Email-channel alerts are emailed.
export default function NotificationsSection({ data, onChange }) {
  if (!data) return null;
  const { channels, quietHours } = data;

  const setChannel = (key, val) => onChange({ channels: { ...channels, [key]: val } });
  const setQuietHours = (patch) => onChange({ quietHours: { ...quietHours, ...patch } });

  return (
    <div className="sv2-card set-content">
      <div className="set-section-head">
        <div className="set-section-title">Notifications</div>
        <div className="set-section-sub">
          Triggered alerts always appear in the notification center. These control alert emails.
        </div>
      </div>

      <SettingsRow title="Email" description="Email me when an alert set to the Email channel triggers">
        <ToggleSwitch checked={channels.email !== false} onChange={(v) => setChannel("email", v)} />
      </SettingsRow>
      <SettingsRow
        title="Quiet hours"
        description={`Hold alert emails ${quietHours.start} – ${quietHours.end}${
          quietHours.enabled ? ` (${quietHours.timezone || "UTC"})` : ""
        } and send them when quiet hours end`}
      >
        <ToggleSwitch
          checked={quietHours.enabled}
          onChange={(v) => setQuietHours(v ? { enabled: true, timezone: browserTimezone() } : { enabled: false })}
        />
      </SettingsRow>
    </div>
  );
}
