import { useState } from "react";
import { motion } from "framer-motion";
import AuthLayout from "./AuthLayout";
import { AuthInput, AuthButton, OAuthButton, Divider, GoogleIcon, GitHubIcon } from "./AuthPrimitives";
import { authApi } from "../../services/authApi";

export default function LoginPage({ onNavigate }) {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleSignIn = async () => {
        setError(null);
        setLoading(true);
        try {
            const response = await authApi.login(email, password);
            console.log("Logged in successfully:", response);
            // Here you might typically save the token to localStorage/context
            onNavigate && onNavigate("Dashboard");
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <AuthLayout onNavigate={onNavigate}>
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
                style={{
                    width: "100%", maxWidth: 420,
                    padding: "40px 32px",
                    background: "rgba(255,255,255,0.022)",
                    border: "1px solid rgba(255,255,255,0.065)",
                    borderRadius: 16,
                    boxShadow: "0 24px 80px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.06)",
                }}
            >
                {/* Header */}
                <div style={{ marginBottom: 32 }}>
                    <h1 style={{
                        fontSize: 26, fontWeight: 700,
                        color: "rgba(228,232,247,0.95)",
                        letterSpacing: "-0.65px",
                        margin: "0 0 10px", lineHeight: 1.2,
                    }}>
                        Welcome back.
                    </h1>
                    <p style={{
                        fontSize: 13, lineHeight: 1.6,
                        color: "rgba(255,255,255,0.32)",
                        margin: 0,
                    }}>
                        Access your investment intelligence workspace.
                    </p>
                </div>

                {/* Fields */}
                <AuthInput
                    label="Email"
                    type="email"
                    placeholder="name@company.com"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                />
                <div style={{ position: "relative" }}>
                    <AuthInput
                        label="Password"
                        type="password"
                        placeholder="••••••••"
                        value={password}
                        onChange={e => setPassword(e.target.value)}
                    />
                    <button
                        style={{
                            position: "absolute", right: 0, top: 0,
                            background: "none", border: "none",
                            fontSize: 11, color: "rgba(255,255,255,0.28)",
                            cursor: "pointer", fontFamily: "inherit", padding: 0,
                            transition: "color 0.15s",
                        }}
                        onMouseEnter={e => e.currentTarget.style.color = "rgba(255,255,255,0.6)"}
                        onMouseLeave={e => e.currentTarget.style.color = "rgba(255,255,255,0.28)"}
                    >
                        Forgot?
                    </button>
                </div>

                <div style={{ marginTop: 8 }}>
                    {error && (
                        <div style={{
                            color: "#ff5064", fontSize: 12, marginBottom: 12,
                            background: "rgba(255,80,100,0.1)", padding: "8px 12px",
                            borderRadius: 6, border: "1px solid rgba(255,80,100,0.2)"
                        }}>
                            {error}
                        </div>
                    )}
                    <AuthButton onClick={handleSignIn} disabled={loading}>
                        {loading ? "Authenticating..." : "Sign In"}
                    </AuthButton>
                </div>

                <Divider label="or" />

                <div style={{ display: "flex", gap: 8 }}>
                    <OAuthButton icon={<GoogleIcon />} label="Google" />
                    <OAuthButton icon={<GitHubIcon />} label="GitHub" />
                </div>

                <p style={{
                    textAlign: "center", fontSize: 12,
                    color: "rgba(255,255,255,0.22)",
                    marginTop: 24, marginBottom: 0,
                }}>
                    No account?{" "}
                    <button
                        onClick={() => onNavigate && onNavigate("Signup")}
                        style={{
                            background: "none", border: "none", padding: 0,
                            fontSize: 12, fontWeight: 600,
                            color: "rgba(140,158,255,0.75)",
                            cursor: "pointer", fontFamily: "inherit",
                            transition: "color 0.15s",
                        }}
                        onMouseEnter={e => e.currentTarget.style.color = "rgba(180,195,255,0.95)"}
                        onMouseLeave={e => e.currentTarget.style.color = "rgba(140,158,255,0.75)"}
                    >
                        Create account →
                    </button>
                </p>
            </motion.div>
        </AuthLayout>
    );
}