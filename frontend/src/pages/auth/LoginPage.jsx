import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import AuthLayout from "./AuthLayout";
import { AuthInput, AuthButton, OAuthButton, Divider, GoogleIcon, GitHubIcon } from "./AuthPrimitives";
import { authApi } from "../../services/authApi";
import { useTheme } from "../../context/ThemeContext";
import { useLandingTheme } from "../../components/landingPage/landingTokens";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function LoginPage({ onNavigate }) {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const { isDark } = useTheme();
    const T = useLandingTheme();

    useEffect(() => {
        const existingToken = localStorage.getItem("altinvest_token");
        if (existingToken) {
            onNavigate && onNavigate("Dashboard");
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const validate = () => {
        if (!email.trim() || !password) {
            return "Email and password are required.";
        }
        if (!EMAIL_RE.test(email.trim())) {
            return "Enter a valid email address.";
        }
        return null;
    };

    const handleSignIn = async () => {
        const validationError = validate();
        if (validationError) {
            setError(validationError);
            return;
        }

        setError(null);
        setLoading(true);
        try {
            const response = await authApi.login(email.trim(), password);
            if (response.token) {
                localStorage.setItem("altinvest_token", response.token);
            }
            if (response.user) {
                localStorage.setItem("altinvest_user", JSON.stringify(response.user));
            }
            onNavigate && onNavigate("Dashboard");
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === "Enter") handleSignIn();
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
                    background: isDark ? "rgba(255,255,255,0.022)" : "rgba(36,33,28,0.015)",
                    border: `1px solid ${T.border2}`,
                    borderRadius: 16,
                    boxShadow: isDark 
                        ? "0 24px 80px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.06)"
                        : "0 24px 80px rgba(36,33,28,0.05), inset 0 1px 0 rgba(255,255,255,0.8)",
                }}
                onKeyDown={handleKeyDown}
            >
                {/* Header */}
                <div style={{ marginBottom: 32 }}>
                    <h1 style={{
                        fontSize: 26, fontWeight: 700,
                        color: T.ink,
                        letterSpacing: "-0.65px",
                        margin: "0 0 10px", lineHeight: 1.2,
                    }}>
                        Welcome back.
                    </h1>
                    <p style={{
                        fontSize: 13, lineHeight: 1.6,
                        color: T.ink2,
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
                        type="button"
                        title="Password reset isn't available yet"
                        disabled
                        style={{
                            position: "absolute", right: 0, top: 0,
                            background: "none", border: "none",
                            fontSize: 11, color: T.ink3,
                            cursor: "not-allowed", fontFamily: "inherit", padding: 0,
                        }}
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
                    <OAuthButton
                        icon={<GoogleIcon />}
                        label="Google"
                        disabled
                        title="Google sign-in is coming soon"
                    />
                    <OAuthButton
                        icon={<GitHubIcon />}
                        label="GitHub"
                        disabled
                        title="GitHub sign-in is coming soon"
                    />
                </div>

                <p style={{
                    textAlign: "center", fontSize: 12,
                    color: T.ink2,
                    marginTop: 24, marginBottom: 0,
                }}>
                    No account?{" "}
                    <button
                        onClick={() => onNavigate && onNavigate("Signup")}
                        style={{
                            background: "none", border: "none", padding: 0,
                            fontSize: 12, fontWeight: 600,
                            color: isDark ? "rgba(140,158,255,0.75)" : "rgba(91,110,245,0.85)",
                            cursor: "pointer", fontFamily: "inherit",
                            transition: "color 0.15s",
                        }}
                        onMouseEnter={e => e.currentTarget.style.color = isDark ? "rgba(180,195,255,0.95)" : "rgba(91,110,245,1.0)"}
                        onMouseLeave={e => e.currentTarget.style.color = isDark ? "rgba(140,158,255,0.75)" : "rgba(91,110,245,0.85)"}
                    >
                        Create account →
                    </button>
                </p>
            </motion.div>
        </AuthLayout>
    );
}