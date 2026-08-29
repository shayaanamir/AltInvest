// frontend/src/services/apiClient.js
import { API_BASE_URL } from "../config";
import { getToken, clearSession } from "../hooks/useAuth";
import { emitSessionExpired } from "../hooks/sessionEvents";

export async function apiFetch(path, options = {}) {
  const token = getToken();
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (res.status === 401) {
    const hadToken = !!token; // only a real "session expired" if they were logged in
    clearSession();
    if (hadToken) emitSessionExpired();
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.status === 204 ? null : res.json();
}