import profileData from "../data/sample_data/profile.json";
import userData from "../data/sample_data/user.json";

const SIM_DELAY = 300;
const delay = (fn) => new Promise((resolve) => setTimeout(() => resolve(fn()), SIM_DELAY));

function capitalize(s) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

export const profileApi = {
  getProfile: () =>
    delay(() => {
      const markets = userData.onboarding?.answers?.markets || [];
      return {
        ...profileData,
        emailVerified: userData.accountSummary?.emailVerified ?? false,
        marketsFollowed: markets.map(capitalize).join(", "),
      };
    }),

  // No backend persistence endpoint exists for profile edits yet — this
  // mirrors the shape of a real update call so the UI can be wired up
  // for real once one exists.
  updateProfile: (patch) => delay(() => ({ ...profileData, ...patch })),
};