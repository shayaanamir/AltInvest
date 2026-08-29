import { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import AuthLayout from "../components/auth/AuthLayout";
import { AuthInput, AuthButton, OAuthButton, Divider, GoogleIcon, GitHubIcon } from "../components/auth/AuthPrimitives";
import { authApi } from "../services/authApi";
import { useLandingTheme } from "../components/landingPage/landingTokens";
import { setSession, isAuthenticated } from "../hooks/useAuth";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function LoginPage({ onNavigate }) {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const returnPath = searchParams.get("return");

    const T = useLandingTheme();

    useEffect(() => {
        if (isAuthenticated()) {
            if (returnPath) navigate(returnPath, { replace: true });
            else onNavigate && onNavigate("Dashboard");
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
            setSession({ token: response.token, user: response.user });
            if (returnPath) navigate(returnPath, { replace: true });
            else onNavigate && onNavigate("Dashboard");
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
                    background: "var(--sv2-card-alt)",
                    border: `1px solid ${T.border2}`,
                    borderRadius: 16,
                    boxShadow: "0 24px 80px color-mix(in srgb, var(--sv2-bg) 45%, transparent), inset 0 1px 0 color-mix(in srgb, var(--sv2-text) 6%, transparent)",
                }}
                onKeyDown={handleKeyDown}
            >
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
                        onClick={() => onNavigate && onNavigate("ForgotPassword")}
                        style={{
                            position: "absolute", right: 0, top: 0,
                            background: "none", border: "none",
                            fontSize: 11, color: "var(--sv2-accent)",
                            cursor: "pointer", fontFamily: "inherit", padding: 0,
                        }}
                    >
                        Forgot?
                    </button>
                </div>

                <div style={{ marginTop: 8 }}>
                    {error && (
                        <div style={{
                            color: "var(--sv2-red)", fontSize: 12, marginBottom: 12,
                            background: "var(--sv2-red-soft)", padding: "8px 12px",
                            borderRadius: 6, border: "1px solid color-mix(in srgb, var(--sv2-red) 20%, transparent)"
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
                            color: "var(--sv2-accent)",
                            cursor: "pointer", fontFamily: "inherit",
                            transition: "opacity 0.15s",
                        }}
                        onMouseEnter={e => e.currentTarget.style.opacity = "0.8"}
                        onMouseLeave={e => e.currentTarget.style.opacity = "1"}
                    >
                        Create account →
                    </button>
                </p>
            </motion.div>
        </AuthLayout>
    );
}