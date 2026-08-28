import settingsData from "../data/sample_data/settings.json";

const SIM_DELAY = 300;
const delay = (fn) => new Promise((resolve) => setTimeout(() => resolve(fn()), SIM_DELAY));

// Dashboard layouts are a fixed, app-defined set (see pages/onboarding/Step5Layout.jsx)
// rather than sample data — surfaced here purely as the select's option list.
const DASHBOARD_LAYOUT_OPTIONS = ["minimal", "analyst", "trader", "ai-first"];

export const settingsApi = {
  getSettings: () =>
    delay(() => ({
      preferences: {
        ...settingsData.preferences,
        dashboardLayoutOptions: DASHBOARD_LAYOUT_OPTIONS,
      },
      appearance: settingsData.appearance,
      notifications: settingsData.notifications,
      security: settingsData.security,
      connectedAccounts: settingsData.connectedAccounts,
      dataControls: settingsData.dataControls,
    })),
};