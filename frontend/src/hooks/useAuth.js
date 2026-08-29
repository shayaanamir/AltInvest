// frontend/src/hooks/useAuth.js
// Centralizes the "altinvest_token" / "altinvest_user" localStorage logic
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

export function useAuth() {
  return { getToken, getStoredUser, setSession, clearSession, isAuthenticated };
}

