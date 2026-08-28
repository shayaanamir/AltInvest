import SettingsRow from "./SettingsRow";

export default function PreferencesSection({ data, onChange }) {
  if (!data) return null;

  return (
    <div className="sv2-card set-content">
      <div className="set-section-head">
        <div className="set-section-title">Preferences</div>
        <div className="set-section-sub">Formatting and where the app opens</div>
      </div>

      <SettingsRow title="Display currency">
        <select
          className="sv2-select set-select"
          value={data.displayCurrency}
          onChange={(e) => onChange({ displayCurrency: e.target.value })}
        >
          {data.currencyOptions.map((c) => (
            <option key={c.code} value={c.code}>{c.label}</option>
          ))}
        </select>
      </SettingsRow>

      <SettingsRow title="Date & number format">
        <select
          className="sv2-select set-select"
          value={data.dateFormat}
          onChange={(e) => onChange({ dateFormat: e.target.value })}
        >
          {data.dateFormatOptions.map((f) => (
            <option key={f} value={f}>{f}</option>
          ))}
        </select>
      </SettingsRow>

      <SettingsRow title="Default landing page" description="Where AltInvest opens after sign-in">
        <select
          className="sv2-select set-select"
          value={data.defaultLandingPage}
          onChange={(e) => onChange({ defaultLandingPage: e.target.value })}
        >
          {data.landingPageOptions.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
      </SettingsRow>

      <SettingsRow title="Default dashboard layout" description="Chosen during onboarding — editable any time">
        <select
          className="sv2-select set-select"
          value={data.defaultDashboardLayout}
          onChange={(e) => onChange({ defaultDashboardLayout: e.target.value })}
        >
          {(data.dashboardLayoutOptions || []).map((l) => (
            <option key={l} value={l}>{l}</option>
          ))}
        </select>
      </SettingsRow>
    </div>
  );
}