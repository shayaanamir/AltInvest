import { USE_MOCK } from "../config";
import { apiFetch } from "./apiClient";
import profileData from "../data/sample_data/profile.json";
import userData from "../data/sample_data/user.json";

const SIM_DELAY = 300;
const delay = (fn) => new Promise((resolve) => setTimeout(() => resolve(fn()), SIM_DELAY));

function capitalize(s) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

function mapBackendProfile(p) {
  return {
    id: p.id,
    name: p.name,
    email: p.email,
    avatarInitials: p.avatar_initials || (p.name ? p.name.slice(0, 2).toUpperCase() : "?"),
    avatarColor: p.avatar_color || "#5b6ef5",
    bio: p.bio || "",
    memberSince: p.created_at,
    riskProfile: p.risk_profile || "balanced",
    // investmentGoal isn't part of backend ProfileOut yet — no server field
    // to read it from, so it's left undefined until the schema grows one.
    investmentGoal: undefined,
    marketsFollowed: "", // same — onboarding answers aren't persisted server-side yet
    activitySummary: {
      holdingsCount: p.activity_summary?.holdings_count ?? 0,
      watchlistsCount: p.activity_summary?.watchlists_count ?? 0,
      alertsCount: p.activity_summary?.alerts_count ?? 0,
      portfolioValueUsd: null, // requires a join with /portfolio/summary if wanted here
    },
    editableFields: ["name", "avatar", "bio"],
    riskProfileOptions: ["conservative", "balanced", "aggressive"],
    investmentGoalOptions: ["longterm", "trading", "research", "discovery", "portfolio"],
  };
}

export const profileApi = {
  getProfile: () => {
    if (USE_MOCK) {
      return delay(() => {
        const markets = userData.onboarding?.answers?.markets || [];
        return {
          ...profileData,
          emailVerified: userData.accountSummary?.emailVerified ?? false,
          marketsFollowed: markets.map(capitalize).join(", "),
        };
      });
    }
    return (async () => {
      const p = await apiFetch("/profile");
      return { ...mapBackendProfile(p), emailVerified: !!p.email_verified };
    })();
  },

  updateProfile: (patch) => {
    if (USE_MOCK) return delay(() => ({ ...profileData, ...patch }));
    // Only forward fields the backend actually accepts
    // (see backend/models/schemas.py::ProfileUpdate)
    const allowed = ["name", "bio", "avatar_initials", "avatar_color", "risk_profile", "layout_preference", "display_currency"];
    const backendPatch = {};
    if (patch.name !== undefined) backendPatch.name = patch.name;
    if (patch.bio !== undefined) backendPatch.bio = patch.bio;
    if (patch.avatarInitials !== undefined) backendPatch.avatar_initials = patch.avatarInitials;
    if (patch.avatarColor !== undefined) backendPatch.avatar_color = patch.avatarColor;
    if (patch.riskProfile !== undefined) backendPatch.risk_profile = patch.riskProfile;
    Object.keys(backendPatch).forEach((k) => {
      if (!allowed.includes(k)) delete backendPatch[k];
    });

    return apiFetch("/profile", {
      method: "PATCH",
      body: JSON.stringify(backendPatch),
    }).then(mapBackendProfile);
  },
};