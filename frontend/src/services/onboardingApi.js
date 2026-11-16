import { apiFetch } from "./apiClient";

export const onboardingApi = {
  /**
   * Saves the onboarding result: PUT /profile/onboarding with a body from answersToPayload().
   * The server stores the answers, fills the profile (risk, goal, layout) and starts a watchlist
   * from the coins picked. Calling it again after onboarding is complete changes nothing.
   * Resolves to the updated profile (backend ProfileOut).
   */
  save: (payload) =>
    apiFetch("/profile/onboarding", { method: "PUT", body: JSON.stringify(payload) }),
};
