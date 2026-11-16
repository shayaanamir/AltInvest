// frontend/src/hooks/useAuth.js
// Centralizes the "altinvest_token" / "altinvest_user" localStorage logic.
const TOKEN_KEY = "altinvest_token";
const USER_KEY = "altinvest_user";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser() {
  const raw = localStorage.getItem(USER_KEY);
  try { return raw ? JSON.parse(raw) : null; } catch { return null; }
}

export function setSession({ token, user }) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

/** The token's payload, or null if it isn't a readable JWT. Not verified — the server does that. */
export function readTokenPayload(token) {
  try {
    const part = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(part.padEnd(part.length + ((4 - (part.length % 4)) % 4), "=")));
  } catch {
    return null;
  }
}

// Treat a token as expired a little early so a request doesn't leave with one about to lapse.
const EXPIRY_SKEW_MS = 30_000;

/**
 * Whether there's a token that hasn't expired yet. An expired or unreadable token is cleared, so
 * route guards send the user to login instead of rendering a page whose requests will all 401.
 * The server still has the final say (a revoked session 401s and apiFetch signs the user out).
 */
export function isAuthenticated() {
  const token = getToken();
  if (!token) return false;
  const exp = readTokenPayload(token)?.exp;
  if (typeof exp !== "number" || exp * 1000 - EXPIRY_SKEW_MS <= Date.now()) {
    clearSession();
    return false;
  }
  return true;
}

export function useAuth() {
  return { getToken, getStoredUser, setSession, clearSession, isAuthenticated };
}