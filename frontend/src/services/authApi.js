// Authentication API Service
import { API_BASE_URL } from "../config";
import { ApiError, kindFromStatus } from "../errors/errorCatalog";
import { reportApiReachable } from "../errors/connectionStatus";
import { apiFetch } from "./apiClient";
import { getToken, clearSession } from "../hooks/useAuth";

/**
 * POST JSON to an auth endpoint. Throws ApiError:
 *  - no response at all  -> kind "network"
 *  - 4xx the server explained (wrong password, account exists, bad reset link) -> kind "validation",
 *    carrying the server's own message. A 401 here means "wrong credentials", not "session expired".
 *  - anything else       -> the kind for that status (rateLimit, server, unavailable…)
 */
async function authPost(path, body, fallbackMessage) {
    let res;
    try {
        res = await fetch(`${API_BASE_URL}${path}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
    } catch {
        reportApiReachable(false);
        throw new ApiError("Network request failed", { kind: "network" });
    }
    reportApiReachable(true);

    const data = await res.json().catch(() => ({})); // Handle cases where response isn't JSON
    if (!res.ok) {
        const detail = typeof data.detail === "string" ? data.detail : null;
        const clientError = res.status >= 400 && res.status < 500 && res.status !== 429;
        throw new ApiError(detail || fallbackMessage, {
            status: res.status,
            kind: clientError ? "validation" : kindFromStatus(res.status),
            detail: detail || (clientError ? fallbackMessage : null),
        });
    }
    return data;
}

export const authApi = {
    /**
     * Authenticate a user
     * @returns {Promise<{ user: any, token: string }>}
     */
    login: async (email, password) => {
        return authPost("/auth/login", { email, password }, "Invalid email or password.");
    },

    /**
     * Register a new user
     * @returns {Promise<{ user: any, token: string }>}
     */
    signup: async (name, email, password) => {
        return authPost("/auth/signup", { name, email, password }, "We couldn't create that account. Check the details and try again.");
    },

    /**
    * Request a password reset email. Always resolves with a generic
    * message — never reveals whether the account exists.
    */
    forgotPassword: async (email) => {
        return authPost("/auth/forgot-password", { email }, "Something went wrong. Try again.");
    },

    /**
     * Complete a password reset using the token from the emailed link.
     */
    resetPassword: async (token, newPassword) => {
        return authPost("/auth/reset-password", { token, new_password: newPassword }, "This reset link is invalid or has expired.");
    },

    /** Confirm an email address with the token from the verification link. */
    verifyEmail: async (token) => {
        return authPost("/auth/verify-email", { token }, "This verification link is invalid or has expired.");
    },

    /** Email the signed-in user a new verification link. Resolves with { message, sent }. */
    resendVerification: () => apiFetch("/auth/resend-verification", { method: "POST" }),

    /** Change the signed-in user's password. A wrong current password comes back as a 400. */
    changePassword: (currentPassword, newPassword) =>
        apiFetch("/auth/change-password", {
            method: "POST",
            body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
        }),

    /** Signed-in sessions for this account: [{ id, device, ip, created_at, last_active, current }]. */
    listSessions: () => apiFetch("/auth/sessions"),

    /** Sign out every session except this one. Resolves with { revoked }. */
    revokeOtherSessions: () => apiFetch("/auth/sessions/revoke-others", { method: "POST" }),

    /** Sign out one other session. */
    revokeSession: (sessionId) => apiFetch(`/auth/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" }),

    /**
     * End this session on the server and forget it locally. The server call is best-effort and not
     * awaited (it always answers 204), so logging out never waits on, or fails because of, the network.
     */
    logout: () => {
        const token = getToken();
        clearSession();
        if (!token) return;
        fetch(`${API_BASE_URL}/auth/logout`, {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` },
            keepalive: true,
        }).catch(() => {});
    },
};
