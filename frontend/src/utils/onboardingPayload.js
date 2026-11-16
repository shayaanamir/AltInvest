// What the onboarding screens send to PUT /profile/onboarding, and how the saved markets read back.
// Pure functions (no React) so they can be unit-tested with `node --test`.

export const DEFAULT_RISK = 50;           // the slider's resting position (Step2RiskStyle)
export const DEFAULT_LAYOUT = "ai-first"; // the layout card that shows as selected (Step5Layout)

const MARKET_LABELS = {
  crypto: "Crypto",
  nfts: "NFTs",
  commodities: "Commodities",
  tokenized: "Tokenized assets",
};

const list = (v) => (Array.isArray(v) ? v.filter((x) => typeof x === "string") : []);

/**
 * The request body. The steps only write an answer when the user touches a control, so the
 * values the screens *show* by default (risk 50, layout "ai-first") are filled in here; a person who
 * clicked Continue through every step still ends up with the profile they saw.
 * A skip sends no answers.
 */
export function answersToPayload(answers = {}, { skipped = false } = {}) {
  if (skipped) return { skipped: true, answers: {} };
  const risk = Number.isFinite(answers.risk) ? Math.min(100, Math.max(0, Math.round(answers.risk))) : DEFAULT_RISK;
  return {
    skipped: false,
    answers: {
      markets: list(answers.markets),
      risk,
      goals: list(answers.goals),
      assets: list(answers.assets),
      layout: typeof answers.layout === "string" && answers.layout ? answers.layout : DEFAULT_LAYOUT,
    },
  };
}

/** ["crypto","nfts"] -> "Crypto, NFTs" for the profile header; "" when nothing was chosen. */
export function marketsLabel(markets) {
  return list(markets).map((m) => MARKET_LABELS[m] || m).join(", ");
}
