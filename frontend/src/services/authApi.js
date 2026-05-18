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
            throw new Error(data.message || data.error || "Error creating account");
        }
        
        return data; // Expected to contain { user, token }
    }
};
