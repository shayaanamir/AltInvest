import { useState } from "react";
import { motion } from "framer-motion";
import AuthLayout from "./AuthLayout";
import { AuthInput, AuthButton, OAuthButton, Divider, GoogleIcon } from "./AuthPrimitives";
import { authApi } from "../../services/authApi";
import { useLandingTheme } from "../../components/landingPage/landingTokens";
import { setSession } from "../../hooks/useAuth";

export default function SignupPage({ onNavigate }) {
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const T = useLandingTheme();

    const handleContinue = async () => {
        setError(null);
        setLoading(true);
        try {
            const response = await authApi.signup(name, email, password);
            console.log("Signed up successfully:", response);
            setSession({ token: response.token, user: response.user });
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
                    background: "var(--sv2-card-alt)",
                    border: `1px solid ${T.border2}`,
                    borderRadius: 16,
                    boxShadow: "0 24px 80px color-mix(in srgb, var(--sv2-bg) 45%, transparent), inset 0 1px 0 color-mix(in srgb, var(--sv2-text) 6%, transparent)",
                }}
            >
                <div style={{ marginBottom: 32 }}>
                    <h1 style={{
                        fontSize: 26, fontWeight: 700,
                        color: T.ink,
                        letterSpacing: "-0.65px",
                        margin: "0 0 10px", lineHeight: 1.2,
                    }}>
                        Create your account.
                    </h1>
                    <p style={{
                        fontSize: 13, lineHeight: 1.6,
                        color: T.ink2,
                        margin: 0,
                    }}>
                        Start exploring alternative markets in minutes.
                    </p>
                </div>

                <AuthInput
                    label="Full Name"
                    type="text"
                    placeholder="Enter Full Name"
                    value={name}
                    onChange={e => setName(e.target.value)}
                />
                <AuthInput
                    label="Email"
                    type="email"
                    placeholder="name@company.com"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                />
                <AuthInput
                    label="Password"
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                />

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
                    <AuthButton onClick={handleContinue} disabled={loading}>
                        {loading ? "Creating account..." : "Continue"}
                    </AuthButton>
                </div>

                <Divider label="or" />

                <OAuthButton icon={<GoogleIcon />} label="Google" disabled title="Google sign-in is coming soon" />

                <p style={{
                    textAlign: "center", fontSize: 11,
                    color: T.ink3,
                    marginTop: 14, marginBottom: 4, lineHeight: 1.6,
                }}>
                    By signing up, you agree to our{" "}
                    <span
                        style={{ color: T.ink2, cursor: "pointer", transition: "color 0.15s" }}
                        onMouseEnter={e => e.currentTarget.style.color = T.ink}
                        onMouseLeave={e => e.currentTarget.style.color = T.ink2}
                    >Terms</span>
                    {" & "}
                    <span
                        style={{ color: T.ink2, cursor: "pointer", transition: "color 0.15s" }}
                        onMouseEnter={e => e.currentTarget.style.color = T.ink}
                        onMouseLeave={e => e.currentTarget.style.color = T.ink2}
                    >Privacy Policy</span>.
                </p>

                <p style={{
                    textAlign: "center", fontSize: 12,
                    color: T.ink2,
                    marginTop: 12, marginBottom: 0,
                }}>
                    Have an account?{" "}
                    <button
                        onClick={() => onNavigate && onNavigate("Login")}
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
                        Sign in →
                    </button>
                </p>
            </motion.div>
        </AuthLayout>
    );
}