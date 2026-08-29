import { USE_MOCK } from "../config";
import { apiFetch } from "./apiClient";
import settingsData from "../data/sample_data/settings.json";

const SIM_DELAY = 300;
const delay = (fn) => new Promise((resolve) => setTimeout(() => resolve(fn()), SIM_DELAY));

const DASHBOARD_LAYOUT_OPTIONS = ["minimal", "analyst", "trader", "ai-first"];

function mapBackendSettings(s) {
  return {
    preferences: {
      displayCurrency: s.preferences?.display_currency ?? "USD",
      currencyOptions: settingsData.preferences.currencyOptions,
      dateFormat: s.preferences?.date_format ?? "MM/DD/YYYY",
      dateFormatOptions: settingsData.preferences.dateFormatOptions,
      defaultLandingPage: s.preferences?.default_landing_page ?? "Dashboard",
      landingPageOptions: settingsData.preferences.landingPageOptions,
      defaultDashboardLayout: s.preferences?.default_dashboard_layout ?? "ai-first",
      dashboardLayoutOptions: DASHBOARD_LAYOUT_OPTIONS,
    },
    appearance: {
      theme: s.appearance?.theme ?? "dark",
      density: s.appearance?.density ?? "comfortable",
      densityOptions: settingsData.appearance.densityOptions,
    },
    notifications: {
      channels: s.notifications?.channels ?? settingsData.notifications.channels,
      alertTypes: s.notifications?.alert_types ?? settingsData.notifications.alertTypes,
      quietHours: s.notifications?.quiet_hours
        ? {
            enabled: s.notifications.quiet_hours.enabled,
            start: s.notifications.quiet_hours.start,
            end: s.notifications.quiet_hours.end,
            timezone: s.notifications.quiet_hours.timezone,
          }
        : settingsData.notifications.quietHours,
    },
    security: {
      twoFactorEnabled: s.security?.two_factor_enabled ?? false,
      twoFactorStatus: "coming_soon",
      // Active sessions aren't backed by a real route yet
      // (GET /settings/sessions is on the "missing routes" list).
      activeSessions: settingsData.security.activeSessions,
    },
    connectedAccounts: {
      google: { connected: !!s.connected_accounts?.google, status: "coming_soon" },
      github: { connected: !!s.connected_accounts?.github, status: "coming_soon" },
      wallet: { connected: !!s.connected_accounts?.wallet, status: "proposed" },
    },
    dataControls: {
      // /settings/export doesn't exist yet — client-side export
      // (DataAccountSection.jsx) still works against real portfolio/
      // watchlist/alert data once those services are wired.
      exportFormats: ["CSV", "JSON"],
      lastExportAt: null,
      accountDeletion: settingsData.dataControls.accountDeletion,
    },
  };
}

// Reverse-map a section's frontend-shaped patch into the backend's
// snake_case field names for PATCH /settings/{section}.
function toBackendPayload(section, patch) {
  if (section === "preferences") {
    const out = {};
    if (patch.displayCurrency !== undefined) out.display_currency = patch.displayCurrency;
    if (patch.dateFormat !== undefined) out.date_format = patch.dateFormat;
    if (patch.defaultLandingPage !== undefined) out.default_landing_page = patch.defaultLandingPage;
    if (patch.defaultDashboardLayout !== undefined) out.default_dashboard_layout = patch.defaultDashboardLayout;
    return out;
  }
  if (section === "appearance") {
    const out = {};
    if (patch.theme !== undefined) out.theme = patch.theme;
    if (patch.density !== undefined) out.density = patch.density;
    return out;
  }
  if (section === "notifications") {
    const out = {};
    if (patch.channels !== undefined) out.channels = patch.channels;
    if (patch.alertTypes !== undefined) out.alert_types = patch.alertTypes;
    if (patch.quietHours !== undefined) out.quiet_hours = patch.quietHours;
    return out;
  }
  if (section === "security") {
    const out = {};
    if (patch.twoFactorEnabled !== undefined) out.two_factor_enabled = patch.twoFactorEnabled;
    return out;
  }
  if (section === "connectedAccounts") {
    // backend section key is "connected_accounts", handled by caller
    const out = {};
    Object.entries(patch).forEach(([k, v]) => {
      out[k] = !!v.connected;
    });
    return out;
  }
  return patch;
}

const SECTION_BACKEND_KEY = {
  preferences: "preferences",
  appearance: "appearance",
  notifications: "notifications",
  security: "security",
  connectedAccounts: "connected_accounts",
};

export const settingsApi = {
  getSettings: () => {
    if (USE_MOCK) {
      return delay(() => ({
        preferences: { ...settingsData.preferences, dashboardLayoutOptions: DASHBOARD_LAYOUT_OPTIONS },
        appearance: settingsData.appearance,
        notifications: settingsData.notifications,
        security: settingsData.security,
        connectedAccounts: settingsData.connectedAccounts,
        dataControls: settingsData.dataControls,
      }));
    }
    return apiFetch("/settings").then(mapBackendSettings);
  },

  updateSection: (section, patch) => {
    if (USE_MOCK) return delay(() => ({ status: "updated" }));
    const backendSection = SECTION_BACKEND_KEY[section];
    if (!backendSection) {
      console.warn(`settingsApi.updateSection: unknown section "${section}", skipping backend call`);
      return Promise.resolve({ status: "skipped" });
    }
    const payload = toBackendPayload(section, patch);
    if (Object.keys(payload).length === 0) return Promise.resolve({ status: "skipped" });
    return apiFetch(`/settings/${backendSection}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }).then(mapBackendSettings);
  },
};