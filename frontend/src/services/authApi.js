// Authentication API Service
import { USE_MOCK, API_BASE_URL } from "../config";
import { ApiError, kindFromStatus } from "../errors/errorCatalog";
import { reportApiReachable } from "../errors/connectionStatus";

// Rejection for the mock paths: the message is meant for the person, like a server 4xx detail.
const rejectWith = (message) => new ApiError(message, { kind: "validation", detail: message });

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
        if (USE_MOCK) {
            return new Promise((resolve, reject) => {
                setTimeout(() => {
                    if (!email || !password) return reject(rejectWith("Email and password are required."));
                    resolve({ user: { id: 1, name: "Test User", email }, token: "mock-jwt-token-12345" });
                }, 800);
            });
        }
        return authPost("/auth/login", { email, password }, "Invalid email or password.");
    },

    /**
     * Register a new user
     * @returns {Promise<{ user: any, token: string }>}
     */
    signup: async (name, email, password) => {
        if (USE_MOCK) {
            return new Promise((resolve, reject) => {
                setTimeout(() => {
                    if (!name || !email || !password) return reject(rejectWith("All fields are required."));
                    resolve({ user: { id: 2, name, email }, token: "mock-jwt-token-67890" });
                }, 800);
            });
        }
        return authPost("/auth/signup", { name, email, password }, "We couldn't create that account. Check the details and try again.");
    },

    /**
    * Request a password reset email. Always resolves with a generic
    * message — never reveals whether the account exists.
    */
    forgotPassword: async (email) => {
        if (USE_MOCK) {
            return new Promise((resolve) => {
                setTimeout(() => {
                    resolve({ message: "If an account exists for that email, we've sent password reset instructions." });
                }, 600);
            });
        }
        return authPost("/auth/forgot-password", { email }, "Something went wrong. Try again.");
    },

    /**
     * Complete a password reset using the token from the emailed link.
     */
    resetPassword: async (token, newPassword) => {
        if (USE_MOCK) {
            return new Promise((resolve, reject) => {
                setTimeout(() => {
                    if (!token) return reject(rejectWith("This reset link is invalid or has expired."));
                    if (!newPassword || newPassword.length < 8) return reject(rejectWith("Password must be at least 8 characters."));
                    resolve({ message: "Password updated. You can now sign in with your new password." });
                }, 600);
            });
        }
        return authPost("/auth/reset-password", { token, new_password: newPassword }, "This reset link is invalid or has expired.");
    }
};
