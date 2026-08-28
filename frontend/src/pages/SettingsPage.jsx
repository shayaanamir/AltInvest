import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "../styles/sentiment.css";
import "../styles/settingsProfile.css";
import { settingsApi } from "../services/settingsApi";
import SettingsSidebar from "../components/settings/SettingsSidebar";
import PreferencesSection from "../components/settings/PreferencesSection";
import AppearanceSection from "../components/settings/AppearanceSection";
import NotificationsSection from "../components/settings/NotificationsSection";
import SecuritySection from "../components/settings/SecuritySection";
import ConnectedAccountsSection from "../components/settings/ConnectedAccountsSection";
import DataAccountSection from "../components/settings/DataAccountSection";
import SettingsFooter from "../components/settings/SettingsFooter";

const TABS = [
  { key: "preferences", label: "Preferences", icon: "tune" },
  { key: "appearance", label: "Appearance", icon: "palette" },
  { key: "notifications", label: "Notifications", icon: "bell" },
  { key: "security", label: "Security", icon: "shield" },
  { key: "connected", label: "Connected accounts", icon: "link" },
  { key: "data", label: "Data & account", icon: "db" },
];

export default function SettingsPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("preferences");
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    settingsApi.getSettings().then((data) => {
      setSettings(data);
      setLoading(false);
    }).catch(console.error);
  }, []);

  const updateSection = (section, patch) => {
    setSettings((prev) => ({ ...prev, [section]: { ...prev[section], ...patch } }));
  };

  const handleLogout = () => {
    localStorage.removeItem("altinvest_token");
    localStorage.removeItem("altinvest_user");
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
            {loading || !settings ? (
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