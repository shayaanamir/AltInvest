// What the onboarding screens send to PUT /profile/onboarding, and how the saved markets read back.
// Pure functions (no React) so they can be unit-tested with `node --test`.
import { DEFAULT_FOCUS, normalizeFocus } from "./homeFocus.js";

export const DEFAULT_RISK = 50;               // the slider's resting position (Step2RiskStyle)
export const DEFAULT_DENSITY = "comfortable"; // the app's own default
export const MAX_PICKS = 50;                  // per kind (coins, NFT collections); the backend enforces the same

const MARKET_LABELS = {
  crypto: "Crypto",
  nfts: "NFTs",
};

const list = (v) => (Array.isArray(v) ? v.filter((x) => typeof x === "string") : []);

/**
 * The request body. The steps only write an answer when the user touches a control, so the values
 * the screens *show* by default (risk 50, the Everything focus, comfortable density) are filled in
 * here; a person who clicked Continue through every step still ends up with what they saw.
 * `theme` is the theme in use right now ("dark" | "light"), so a change made with the top-bar toggle
 * is saved too. A skip sends no answers.
 */
export function answersToPayload(answers = {}, { skipped = false, theme } = {}) {
  if (skipped) return { skipped: true, answers: {} };
  const risk = Number.isFinite(answers.risk) ? Math.min(100, Math.max(0, Math.round(answers.risk))) : DEFAULT_RISK;
  const out = {
    markets: list(answers.markets),
    risk,
    goals: list(answers.goals),
    assets: list(answers.assets).slice(0, MAX_PICKS),
    nfts: list(answers.nfts).slice(0, MAX_PICKS),
    focus: normalizeFocus(answers.focus ?? DEFAULT_FOCUS),
    density: answers.density === "compact" ? "compact" : DEFAULT_DENSITY,
  };
  if (theme === "dark" || theme === "light") out.theme = theme;
  return { skipped: false, answers: out };
}

/** ["crypto","nfts"] -> "Crypto, NFTs" for the profile header; "" when nothing was chosen. */
export function marketsLabel(markets) {
  return list(markets).map((m) => MARKET_LABELS[m] || m).join(", ");
}

/** Adds or removes `value` from a list answer, keeping it unique and within `max`. */
export function togglePick(current, value, max = MAX_PICKS) {
  const have = list(current);
  if (have.includes(value)) return have.filter((v) => v !== value);
  return have.length >= max ? have : [...have, value];
}
