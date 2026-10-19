// frontend/src/content/uiOptions.js
// Fixed choices the UI offers in dropdowns and forms. This is interface vocabulary, not data:
// nothing here describes a user, asset or market.

export const CURRENCY_OPTIONS = [
  { code: "USD", label: "US Dollar ($)" },
  { code: "EUR", label: "Euro (€)" },
  { code: "GBP", label: "British Pound (£)" },
  { code: "INR", label: "Indian Rupee (₹)" },
  { code: "JPY", label: "Japanese Yen (¥)" },
];

export const DATE_FORMAT_OPTIONS = ["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"];
export const LANDING_PAGE_OPTIONS = ["Dashboard", "Portfolio", "Sentiment"];
export const DASHBOARD_LAYOUT_OPTIONS = ["minimal", "analyst", "trader", "ai-first"];
export const DENSITY_OPTIONS = ["comfortable", "compact"];

// Defaults shown for a notification setting the server hasn't stored yet (same as the
// defaults backend/db/queries.py writes for a new account).
export const NOTIFICATION_DEFAULTS = {
  channels: { inApp: true, push: true, email: false },
  alertTypes: {
    aaiThresholdOnly: true,
    priceAlerts: true,
    sentimentShifts: false,
    minorPriceWiggles: false,
    marketNews: true,
    systemMessages: true,
  },
  quietHours: { enabled: false, start: "22:00", end: "07:00", timezone: "UTC" },
};

export const ACCOUNT_DELETION = {
  requiresTypedConfirmation: true,
  confirmationPhrase: "DELETE MY ACCOUNT",
};

// Mirrors backend/routes/alerts.py's valid metric types and conditions.
export const ALERT_METRIC_OPTIONS = [
  { key: "price", label: "Price" },
  { key: "aai_score", label: "AAI Score" },
  { key: "sentiment", label: "Sentiment" },
  { key: "risk", label: "Risk Score" },
];

export const ALERT_CONDITION_OPTIONS = [
  { key: "above", label: "crosses above" },
  { key: "below", label: "crosses below" },
  { key: "shifts_bearish", label: "shifts bearish" },
  { key: "shifts_bullish", label: "shifts bullish" },
];
