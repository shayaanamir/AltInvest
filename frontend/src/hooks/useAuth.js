// frontend/src/hooks/useAuth.js
// Centralizes the "altinvest_token" / "altinvest_user" localStorage logic,
// plus a temporary dev auto-login until a real login flow is in place.
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

export function isAuthenticated() {
  return !!getToken();
}

// ── TEMPORARY: dev auto-login ────────────────────────────────────────────
// Real login screens (LoginPage/SignupPage) already work end-to-end against
// /auth/login and /auth/signup. This just triggers that same real flow
// automatically on app boot, using the demo user seeded by db/seed_users.py,
// so every user-scoped route (portfolio/watchlists/alerts/notifications/
// profile/settings) has a real JWT to resolve user_id from.
//
// Remove ensureDevSession() and its call site in App.jsx once a real login
// screen is the actual entry point.
const DEV_EMAIL = "demo@altinvest.com";
const DEV_PASSWORD = "Demo1234!";

let _devLoginPromise = null;

export async function ensureDevSession() {
  if (isAuthenticated()) return getToken();

  // Guard against multiple components triggering login concurrently on boot
  if (_devLoginPromise) return _devLoginPromise;

  _devLoginPromise = (async () => {
    // Lazy import to avoid a circular import (authApi -> config, no cycle,
    // but keeps this hook file dependency-light for consumers that only
    // need getToken/isAuthenticated).
    const { authApi } = await import("../services/authApi");
    try {
      const { token, user } = await authApi.login(DEV_EMAIL, DEV_PASSWORD);
      setSession({ token, user });
      return token;
    } catch (e) {
      console.error("Dev auto-login failed — is the demo user seeded? (python db/seed_users.py)", e);
      throw e;
    } finally {
      _devLoginPromise = null;
    }
  })();

  return _devLoginPromise;
}

export function useAuth() {
  return { getToken, getStoredUser, setSession, clearSession, isAuthenticated, ensureDevSession };
}