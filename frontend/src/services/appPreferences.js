import { useSyncExternalStore } from "react";
// The signed-in user's saved display preferences, held where non-React code (formatters) can read them.
// Loaded from GET /settings (and GET /fx for exchange rates) after sign-in; the Settings page pushes
// changes in as they are saved.
import { apiFetch } from "./apiClient";

const DEFAULTS = {
  loaded: false,
  dateFormat: "MM/DD/YYYY",
  density: "comfortable",
  theme: null, // null = leave whatever the top-bar toggle says
  landingPage: "Dashboard",
  displayCurrency: "USD", // what the user chose
  fx: null, // { rates: { EUR: 0.89, ... }, asOf: "YYYY-MM-DD", source } from GET /fx, or null if unavailable
};

let state = { ...DEFAULTS };
const listeners = new Set();

function set(patch) {
  state = { ...state, ...patch };
  document.documentElement.setAttribute("data-density", state.density);
  listeners.forEach((fn) => fn());
}

export const getAppPreferences = () => state;

export function subscribeAppPreferences(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

// Latest USD exchange rates; null when the backend hasn't got any (values then stay in USD).
async function fetchFx() {
  try {
    const fx = await apiFetch("/fx");
    return { rates: fx.rates || {}, asOf: fx.as_of, source: fx.source };
  } catch {
    return null;
  }
}

// Fetch the saved settings once per session; throws if the request fails so the caller can decide.
export async function loadAppPreferences() {
  const [s, fx] = await Promise.all([apiFetch("/settings"), fetchFx()]);
  set({
    loaded: true,
    dateFormat: s.preferences?.date_format ?? DEFAULTS.dateFormat,
    density: s.appearance?.density ?? DEFAULTS.density,
    theme: s.appearance?.theme ?? null,
    landingPage: s.preferences?.default_landing_page ?? DEFAULTS.landingPage,
    displayCurrency: s.preferences?.display_currency ?? DEFAULTS.displayCurrency,
    fx,
  });
  return state;
}

// Mirror a change the user just saved on the Settings page (frontend field names).
export function applySavedPreference(section, patch) {
  const next = {};
  if (section === "preferences") {
    if (patch.dateFormat !== undefined) next.dateFormat = patch.dateFormat;
    if (patch.defaultLandingPage !== undefined) next.landingPage = patch.defaultLandingPage;
    if (patch.displayCurrency !== undefined) {
      next.displayCurrency = patch.displayCurrency;
      // Rates may have been unavailable at sign-in; try again now that they're needed.
      if (!state.fx && patch.displayCurrency !== "USD") fetchFx().then((fx) => fx && set({ fx }));
    }
  }
  if (section === "appearance") {
    if (patch.density !== undefined) next.density = patch.density;
    if (patch.theme !== undefined) next.theme = patch.theme;
  }
  if (Object.keys(next).length) set(next);
}

export function resetAppPreferences() {
  set({ ...DEFAULTS });
}

/**
 * The currency values are actually shown in, and the USD→currency rate to apply.
 * Falls back to USD (rate 1) when there's no stored rate for the chosen currency, and says so via
 * `unavailable`, so nothing is ever shown converted with a made-up rate.
 */
export function getDisplayCurrency() {
  const wanted = state.displayCurrency || "USD";
  if (wanted === "USD") return { code: "USD", rate: 1, wanted, unavailable: false, asOf: state.fx?.asOf ?? null };
  const rate = state.fx?.rates?.[wanted];
  if (typeof rate === "number" && rate > 0) return { code: wanted, rate, wanted, unavailable: false, asOf: state.fx.asOf };
  return { code: "USD", rate: 1, wanted, unavailable: true, asOf: null };
}

const LANDING_PATHS = { Dashboard: "/dashboard", Portfolio: "/portfolio", Sentiment: "/sentiment" };

// Where to send the user after signing in; falls back to the dashboard if the settings can't be read.
export async function resolveLandingPath() {
  try {
    const { landingPage } = await loadAppPreferences();
    return LANDING_PATHS[landingPage] || "/dashboard";
  } catch {
    return "/dashboard";
  }
}

// Format a date (ISO string or Date) the way the user chose. Returns "" for a missing/invalid date.
export function formatDate(value) {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, "0");
  const day = String(d.getUTCDate()).padStart(2, "0");
  switch (state.dateFormat) {
    case "DD/MM/YYYY":
      return `${day}/${m}/${y}`;
    case "YYYY-MM-DD":
      return `${y}-${m}-${day}`;
    default:
      return `${m}/${day}/${y}`;
  }
}

// React hook: re-renders the component when the saved preferences change.
export function useAppPreferences() {
  return useSyncExternalStore(subscribeAppPreferences, getAppPreferences);
}
