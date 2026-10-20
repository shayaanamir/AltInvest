// Sliding sessions: once the current token is past half its lifetime, trade it for a fresh one
// (POST /auth/refresh) so an active user is never signed out mid-use. Runs in the background after
// successful API calls; idle users are left alone and their token lapses as issued.
import { API_BASE_URL } from "../config";
import { getToken, setSession, readTokenPayload } from "../hooks/useAuth";

let inFlight = null;
let lastTried = null; // one attempt per token: no retry storm on failure or at the 30-day cap

export function maybeRefreshSession() {
  const token = getToken();
  if (!token || inFlight || token === lastTried) return;

  const { iat, exp } = readTokenPayload(token) || {};
  if (typeof iat !== "number" || typeof exp !== "number") return;
  const nowSec = Date.now() / 1000;
  if (exp - nowSec > (exp - iat) / 2) return; // still in its first half

  lastTried = token;
  inFlight = fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  })
    .then((res) => (res.ok ? res.json() : null))
    .then((data) => {
      // Skip if the user signed out or in as someone else while this was running.
      if (data?.token && getToken() === token) setSession({ token: data.token });
    })
    // Failures are left to the next normal request: a dead session 401s there and signs the user out.
    .catch(() => {})
    .finally(() => { inFlight = null; });
}
