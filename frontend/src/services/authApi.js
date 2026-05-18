// Mock Authentication API Service
// TODO: Replace these mock functions with actual fetch/axios calls to your backend when it's ready.

const API_BASE_URL = "http://localhost:5000/api"; // Update this to your real backend URL

export const authApi = {
    /**
     * Authenticate a user
     * @param {string} email 
     * @param {string} password 
     * @returns {Promise<{ user: any, token: string }>}
     */
    login: async (email, password) => {
        // SIMULATED BACKEND CALL
        return new Promise((resolve, reject) => {
            setTimeout(() => {
                // Mock validation
                if (!email || !password) {
                    return reject(new Error("Email and password are required."));
                }
                
                // Mock success response
                resolve({
                    user: { id: 1, name: "Test User", email },
                    token: "mock-jwt-token-12345"
                });

                // --- REAL IMPLEMENTATION EXAMPLE ---
                /*
                fetch(`${API_BASE_URL}/auth/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                })
                .then(res => {
                    if (!res.ok) throw new Error("Invalid credentials");
                    return res.json();
                })
                .then(data => resolve(data))
                .catch(err => reject(err));
                */
            }, 800); // simulate network delay
        });
    },

    /**
     * Register a new user
     * @param {string} name 
     * @param {string} email 
     * @param {string} password 
     * @returns {Promise<{ user: any, token: string }>}
     */
    signup: async (name, email, password) => {
        // SIMULATED BACKEND CALL
        return new Promise((resolve, reject) => {
            setTimeout(() => {
                // Mock validation
                if (!name || !email || !password) {
                    return reject(new Error("All fields are required."));
                }
                
                // Mock success response
                resolve({
                    user: { id: 2, name, email },
                    token: "mock-jwt-token-67890"
                });

                // --- REAL IMPLEMENTATION EXAMPLE ---
                /*
                fetch(`${API_BASE_URL}/auth/signup`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, email, password })
                })
                .then(res => {
                    if (!res.ok) throw new Error("Error creating account");
                    return res.json();
                })
                .then(data => resolve(data))
                .catch(err => reject(err));
                */
            }, 800); // simulate network delay
        });
    }
};
