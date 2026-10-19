import { apiFetch } from "./apiClient";

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
    investmentGoal: p.investment_goal || "", // "" = not chosen yet
    emailVerified: !!p.email_verified,
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
  getProfile: async () => {
    const p = await apiFetch("/profile");
    return mapBackendProfile(p);
  },

  updateProfile: (patch) => {
    // Only forward fields the backend actually accepts
    // (see backend/models/schemas.py::ProfileUpdate)
    const allowed = ["name", "bio", "avatar_initials", "avatar_color", "risk_profile", "investment_goal", "layout_preference", "display_currency"];
    const backendPatch = {};
    if (patch.name !== undefined) backendPatch.name = patch.name.trim();
    if (patch.investmentGoal) backendPatch.investment_goal = patch.investmentGoal;
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