import SettingsRow from "./SettingsRow";
import ToggleSwitch from "./ToggleSwitch";

export default function NotificationsSection({ data, onChange }) {
  if (!data) return null;
  const { channels, alertTypes, quietHours } = data;

  const setChannel = (key, val) => onChange({ channels: { ...channels, [key]: val } });
  const setAlertType = (key, val) => onChange({ alertTypes: { ...alertTypes, [key]: val } });
  const setQuietHours = (patch) => onChange({ quietHours: { ...quietHours, ...patch } });

  return (
    <div className="sv2-card set-content">
      <div className="set-section-head">
        <div className="set-section-title">Notifications</div>
        <div className="set-section-sub">Channels and how granular alerts should be</div>
      </div>

      <SettingsRow title="In-app notifications" description="Notification Center and toasts">
        <ToggleSwitch checked={channels.inApp} onChange={(v) => setChannel("inApp", v)} />
      </SettingsRow>
      <SettingsRow title="Email" description="Daily digest and triggered alerts">
        <ToggleSwitch checked={channels.email} onChange={(v) => setChannel("email", v)} />
      </SettingsRow>
      <SettingsRow title="Push" description="Mobile push for triggered alerts">
        <ToggleSwitch checked={channels.push} onChange={(v) => setChannel("push", v)} />
      </SettingsRow>
      <SettingsRow title="AAI threshold alerts" description="Score crosses a line you set">
        <ToggleSwitch checked={alertTypes.aaiThresholdOnly} onChange={(v) => setAlertType("aaiThresholdOnly", v)} />
      </SettingsRow>
      <SettingsRow title="Minor price moves" description="Off by default — this is the noisy one">
        <ToggleSwitch checked={alertTypes.minorPriceWiggles} onChange={(v) => setAlertType("minorPriceWiggles", v)} />
      </SettingsRow>
      <SettingsRow title="Sentiment shifts" description="Direction changes with sufficient evidence">
        <ToggleSwitch checked={alertTypes.sentimentShifts} onChange={(v) => setAlertType("sentimentShifts", v)} />
      </SettingsRow>
      <SettingsRow
        title="Quiet hours"
        description={`Hold non-critical notifications ${quietHours.start} – ${quietHours.end}`}
      >
        <ToggleSwitch checked={quietHours.enabled} onChange={(v) => setQuietHours({ enabled: v })} />
      </SettingsRow>
    </div>
  );
}