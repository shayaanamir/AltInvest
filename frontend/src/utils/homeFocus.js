// The "home focus": what the user wants to see first. One value, stored as
// preferences.default_dashboard_layout, that decides
//   - which dashboard widgets show, and in what order (DashboardPage), and
//   - which page opens after sign-in (resolveLandingPath in services/appPreferences.js).
// The onboarding cards, the Settings dropdown and the dashboard all read this file, so what a card
// previews is exactly what the dashboard renders. Pure data and functions: no React.
//
// The keys and landing pages must match FOCUS_LANDING in backend/routes/profile.py
// (homeFocus.test.js reads that file to check).

export const DEFAULT_FOCUS = "everything";

/** Dashboard widgets a focus can show, with short labels for previews. */
export const WIDGET_LABELS = {
  stats: "Market stats",
  performance: "Portfolio performance",
  insights: "Market insights",
  assets: "Trending coins",
  collections: "Trending NFTs",
};

/**
 * Each preset's dashboard is a list of rows; a row is one or two widget ids shown side by side.
 * The hero header and the get-started banner are always shown and aren't listed.
 * `landing` is a name from LANDING_PAGE_OPTIONS.
 */
export const FOCUS_PRESETS = [
  {
    key: "everything",
    label: "Everything",
    blurb: "The full overview",
    description: "Portfolio, market insights and what's trending, all on one dashboard.",
    landing: "Dashboard",
    rows: [["stats"], ["performance", "insights"], ["assets", "collections"]],
  },
  {
    key: "portfolio",
    label: "Portfolio",
    blurb: "Track what I own",
    description: "Your portfolio's value and performance come first, with trending coins below.",
    landing: "Portfolio",
    rows: [["stats"], ["performance"], ["assets"]],
  },
  {
    key: "markets",
    label: "Markets",
    blurb: "Spot what's moving",
    description: "Trending coins and NFT collections lead, with market insights underneath.",
    landing: "Discover",
    rows: [["stats"], ["assets", "collections"], ["insights"]],
  },
  {
    key: "sentiment",
    label: "Sentiment",
    blurb: "Follow mood and news",
    description: "Market insights and sentiment lead, with trending coins below.",
    landing: "Sentiment",
    rows: [["stats"], ["insights"], ["assets"]],
  },
];

const BY_KEY = Object.fromEntries(FOCUS_PRESETS.map((p) => [p.key, p]));

/** Any stored value (including the old minimal / analyst / trader / ai-first, or nothing) -> a valid key. */
export function normalizeFocus(value) {
  return typeof value === "string" && Object.hasOwn(BY_KEY, value) ? value : DEFAULT_FOCUS;
}

export function getFocus(value) {
  return BY_KEY[normalizeFocus(value)];
}

export function focusLandingPage(value) {
  return getFocus(value).landing;
}

export function dashboardRows(value) {
  return getFocus(value).rows;
}

/** How a row is laid out on the dashboard: the stats band, the chart/insights grid, or the trending blocks. */
export function rowKind(row) {
  if (row.includes("stats")) return "stats";
  if (row.includes("performance") || row.includes("insights")) return "main";
  return "bottom";
}
