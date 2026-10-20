// frontend/src/services/apiClient.js
import { API_BASE_URL } from "../config";
import { getToken, clearSession } from "../hooks/useAuth";
import { emitSessionExpired } from "../hooks/sessionEvents";
import { ApiError, kindFromStatus } from "../errors/errorCatalog";
import { reportApiReachable } from "../errors/connectionStatus";

const REQUEST_TIMEOUT_MS = 20000;

// options.withHeaders: resolve to { data, headers } instead of just the parsed body.
export async function apiFetch(path, options = {}) {
  const token = getToken();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let res;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      signal: controller.signal,
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });
  } catch (e) {
    // fetch only rejects when no HTTP response arrived at all.
    reportApiReachable(false);
    throw new ApiError(
      e?.name === "AbortError" ? "Request timed out" : "Network request failed",
      { kind: e?.name === "AbortError" ? "timeout" : "network" }
    );
  } finally {
    clearTimeout(timer);
  }
  reportApiReachable(true);

  if (res.status === 401) {
    const hadToken = !!token; // only a real "session expired" if they were logged in
    clearSession();
    if (hadToken) emitSessionExpired();
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    // FastAPI sends `detail` as a string for HTTPException but as an array of
    // objects for 422 validation errors.
    const detail = typeof body.detail === "string" ? body.detail : null;
    throw new ApiError(detail || `Request failed: ${res.status}`, {
      status: res.status,
      kind: kindFromStatus(res.status),
      detail,
    });
  }
  if (options.withHeaders) {
    // { data, headers } for callers that need a response header (e.g. Discover's X-Total-Count).
    return { data: res.status === 204 ? null : await res.json(), headers: res.headers };
  }
  return res.status === 204 ? null : res.json();
}
