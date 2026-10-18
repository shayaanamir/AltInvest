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
    // FastAPI sends `detail` as a string for HTTPException but as an array of
    // objects for 422 validation errors.
    const err = new Error(typeof body.detail === "string" ? body.detail : `Request failed: ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return res.status === 204 ? null : res.json();
}