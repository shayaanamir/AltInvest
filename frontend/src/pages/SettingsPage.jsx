import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "../styles/settingsProfile.css";
import { authApi } from "../services/authApi";
import { useAsync } from "../hooks/useAsync";
import { settingsApi } from "../services/settingsApi";
import { applySavedPreference, resetAppPreferences } from "../services/appPreferences";
import SettingsSidebar from "../components/settings/SettingsSidebar";
import PreferencesSection from "../components/settings/PreferencesSection";
import AppearanceSection from "../components/settings/AppearanceSection";
import NotificationsSection from "../components/settings/NotificationsSection";
import SecuritySection from "../components/settings/SecuritySection";
import ConnectedAccountsSection from "../components/settings/ConnectedAccountsSection";
import DataAccountSection from "../components/settings/DataAccountSection";
import SettingsFooter from "../components/settings/SettingsFooter";
import { ErrorState, useToast } from "../errors";

const TABS = [
  { key: "preferences", label: "Preferences", icon: "tune" },
  { key: "appearance", label: "Appearance", icon: "palette" },
  { key: "notifications", label: "Notifications", icon: "bell" },
  { key: "security", label: "Security", icon: "shield" },
  { key: "connected", label: "Connected accounts", icon: "link" },
  { key: "data", label: "Data & account", icon: "db" },
];

// Maps sidebar tab keys ("connected") to settingsApi section keys ("connectedAccounts")
const TAB_TO_SECTION = {
  preferences: "preferences",
  appearance: "appearance",
  notifications: "notifications",
  security: "security",
  connected: "connectedAccounts",
};

export default function SettingsPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("preferences");
  const toast = useToast();
  const { data: initialSettings, loading, error, refetch } = useAsync(() => settingsApi.getSettings(), []);
  const [settings, setSettings] = useState(null);

  useEffect(() => {
    if (initialSettings) setSettings(initialSettings);
  }, [initialSettings]);

  const updateSection = (sectionKey, patch) => {
    const previous = settings?.[sectionKey];
    // Optimistic local update first
    setSettings((prev) => ({ ...prev, [sectionKey]: { ...prev[sectionKey], ...patch } }));

    // Most changes take effect straight away. The currency waits for the save: switching it re-renders
    // every page (this one included), which reloads settings from the server.
    const { displayCurrency, ...immediate } = patch;
    applySavedPreference(sectionKey, immediate);
    settingsApi
      .updateSection(sectionKey, patch)
      .then(() => displayCurrency !== undefined && applySavedPreference(sectionKey, { displayCurrency }))
      .catch((e) => {
        setSettings((prev) => ({ ...prev, [sectionKey]: previous })); // put the old value back
        applySavedPreference(sectionKey, previous); // undo the live change too
        toast.error(e, { title: "Couldn't save that setting" });
      });
  };

  const handleLogout = () => {
    authApi.logout();
    resetAppPreferences();
    navigate("/");
  };

  return (
    <div className="sv2">
      <div className="sv2-page">
        <div className="set-header">
          <div>
            <h1 className="sv2-h1" style={{ marginTop: 0 }}>Settings</h1>
            <p className="sv2-lead">Account configuration — everything here applies immediately.</p>
          </div>
          <button className="sv2-btn-outline" style={{ width: "auto" }} onClick={() => navigate("/profile")}>
            View profile
          </button>
        </div>

        <div className="set-layout" style={{ marginBottom: 16 }}>
          <SettingsSidebar tabs={TABS} activeTab={activeTab} onSelect={setActiveTab} />

          <div className="set-content-col">
            {error ? (
              <div className="sv2-card set-subcard">
                <ErrorState error={error} onRetry={refetch} variant="panel" title="Couldn't load your settings" />
              </div>
            ) : loading || !settings ? (
              <div className="sv2-card set-subcard sv2-muted sv2-small">Loading settings…</div>
            ) : (
              <>
                {activeTab === "preferences" && (
                  <PreferencesSection data={settings.preferences} onChange={(p) => updateSection("preferences", p)} />
                )}
                {activeTab === "appearance" && (
                  <AppearanceSection data={settings.appearance} onChange={(p) => updateSection("appearance", p)} />
                )}
                {activeTab === "notifications" && (
                  <NotificationsSection data={settings.notifications} onChange={(p) => updateSection("notifications", p)} />
                )}
                {activeTab === "security" && <SecuritySection data={settings.security} />}
                {activeTab === "connected" && (
                  <ConnectedAccountsSection data={settings.connectedAccounts} onChange={(p) => updateSection("connectedAccounts", p)} />
                )}
                {activeTab === "data" && <DataAccountSection data={settings.dataControls} />}
              </>
            )}
          </div>
        </div>

        <SettingsFooter onOpenProfile={() => navigate("/profile")} onLogout={handleLogout} />
      </div>
    </div>
  );
}