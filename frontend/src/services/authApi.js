// Authentication API Service
import { USE_MOCK, API_BASE_URL } from "../config";

export const authApi = {
    /**
     * Authenticate a user
     * @param {string} email 
     * @param {string} password 
     * @returns {Promise<{ user: any, token: string }>}
     */
    login: async (email, password) => {
        if (USE_MOCK) {
            return new Promise((resolve, reject) => {
                setTimeout(() => {
                    if (!email || !password) return reject(new Error("Email and password are required."));
                    resolve({ user: { id: 1, name: "Test User", email }, token: "mock-jwt-token-12345" });
                }, 800);
            });
        }

        const res = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await res.json().catch(() => ({})); // Handle cases where response isn't JSON

        if (!res.ok) {
            throw new Error(data.message || data.error || "Invalid credentials");
        }

        return data; // Expected to contain { user, token }
    },

    /**
     * Register a new user
     * @param {string} name 
     * @param {string} email 
     * @param {string} password 
     * @returns {Promise<{ user: any, token: string }>}
     */
    signup: async (name, email, password) => {
        if (USE_MOCK) {
            return new Promise((resolve, reject) => {
                setTimeout(() => {
                    if (!name || !email || !password) return reject(new Error("All fields are required."));
                    resolve({ user: { id: 2, name, email }, token: "mock-jwt-token-67890" });
                }, 800);
            });
        }

        const res = await fetch(`${API_BASE_URL}/auth/signup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password })
        });

        const data = await res.json().catch(() => ({})); // Handle cases where response isn't JSON

        if (!res.ok) {
            throw new Error(data.detail || data.message || data.error || "Invalid credentials");
        }

        return data; // Expected to contain { user, token }
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

        const res = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || "Something went wrong. Try again.");
        return data;
    },

    /**
     * Complete a password reset using the token from the emailed link.
     */
    resetPassword: async (token, newPassword) => {
        if (USE_MOCK) {
            return new Promise((resolve, reject) => {
                setTimeout(() => {
                    if (!token) return reject(new Error("This reset link is invalid or has expired."));
                    if (!newPassword || newPassword.length < 8) return reject(new Error("Password must be at least 8 characters."));
                    resolve({ message: "Password updated. You can now sign in with your new password." });
                }, 600);
            });
        }

        const res = await fetch(`${API_BASE_URL}/auth/reset-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token, new_password: newPassword })
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || "Something went wrong. Try again.");
        return data;
    }
};
