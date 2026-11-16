// Google sign-in (AUTH-11): opens Google's consent popup and resolves with a one-time authorization
// code, which the backend trades for the user's identity (POST /auth/google, /auth/google/link).
//
// The client ID comes from the backend (GET /auth/providers), so GOOGLE_CLIENT_ID is set in one place.
// Uses Google Identity Services' code flow so our own styled button can trigger it.
import { API_BASE_URL } from "../config";

const GIS_SRC = "https://accounts.google.com/gsi/client";

let _providers = null;
let _gisLoading = null;

/** { enabled, clientId } for Google. Never rejects: an unreachable backend reads as "not enabled". */
export function getGoogleConfig() {
  if (!_providers) {
    _providers = fetch(`${API_BASE_URL}/auth/providers`)
      .then((r) => (r.ok ? r.json() : {}))
      .then((p) => ({ enabled: !!p.google?.enabled && !!p.google?.client_id, clientId: p.google?.client_id || null }))
      .catch(() => {
        _providers = null; // try again next time
        return { enabled: false, clientId: null };
      });
  }
  return _providers;
}

function loadGis() {
  if (window.google?.accounts?.oauth2) return Promise.resolve();
  if (!_gisLoading) {
    _gisLoading = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = GIS_SRC;
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => {
        _gisLoading = null;
        script.remove();
        reject(new Error("Couldn't load Google sign-in. Check your connection or any content blockers."));
      };
      document.head.appendChild(script);
    });
  }
  return _gisLoading;
}

/** Start loading Google's script early (e.g. when the sign-in page mounts) so the popup opens at once. */
export function preloadGoogle() {
  getGoogleConfig().then((c) => c.enabled && loadGis().catch(() => {}));
}

export class GoogleCancelled extends Error {}

/**
 * Opens Google's popup. Resolves with the authorization code; rejects with GoogleCancelled when the
 * user closes the popup, or an Error for anything else. Call it straight from a click handler —
 * browsers block popups that open later.
 */
export async function requestGoogleCode() {
  const { enabled, clientId } = await getGoogleConfig();
  if (!enabled) throw new Error("Google sign-in isn't set up on this server.");
  await loadGis();

  return new Promise((resolve, reject) => {
    const client = window.google.accounts.oauth2.initCodeClient({
      client_id: clientId,
      scope: "openid email profile",
      ux_mode: "popup",
      select_account: true,
      callback: (res) => {
        if (res.code) resolve(res.code);
        else if (res.error === "access_denied") reject(new GoogleCancelled("Google sign-in was cancelled."));
        else reject(new Error(res.error_description || "Google sign-in didn't complete. Try again."));
      },
      error_callback: (err) => {
        if (err?.type === "popup_closed") reject(new GoogleCancelled("Google sign-in was cancelled."));
        else if (err?.type === "popup_failed_to_open") reject(new Error("Your browser blocked the Google sign-in popup. Allow popups for this site and try again."));
        else reject(new Error("Google sign-in didn't complete. Try again."));
      },
    });
    client.requestCode();
  });
}
