import SettingsRow from "./SettingsRow";
import { getDisplayCurrency, useAppPreferences } from "../../services/appPreferences";

export default function PreferencesSection({ data, onChange }) {
  useAppPreferences(); // re-render when the rates arrive
  if (!data) return null;
  const fx = getDisplayCurrency();
  const currencyNote = fx.unavailable
    ? `No ${fx.wanted} exchange rate is available right now, so values are shown in USD.`
    : fx.code === "USD"
      ? "Prices and values are stored in USD."
      : `Converted from USD at the European Central Bank reference rate of ${fx.asOf}.`;

  return (
    <div className="sv2-card set-content">
      <div className="set-section-head">
        <div className="set-section-title">Preferences</div>
        <div className="set-section-sub">Formatting and where the app opens</div>
      </div>

      <SettingsRow title="Display currency" description={currencyNote}>
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

      <SettingsRow title="Date format">
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