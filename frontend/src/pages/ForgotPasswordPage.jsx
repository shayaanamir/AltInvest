import { useState } from "react";
import { motion } from "framer-motion";
import AuthLayout from "../components/auth/AuthLayout";
import { AuthInput, AuthButton } from "../components/auth/AuthPrimitives";
import { authApi } from "../services/authApi";
import { useLandingTheme } from "../components/landingPage/landingTokens";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function ForgotPasswordPage({ onNavigate }) {
    const [email, setEmail] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [sent, setSent] = useState(false);

    const T = useLandingTheme();

    const handleSubmit = async () => {
        setError(null);
        if (!email.trim() || !EMAIL_RE.test(email.trim())) {
            setError("Enter a valid email address.");
            return;
        }
        setLoading(true);
        try {
            await authApi.forgotPassword(email.trim());
            setSent(true);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === "Enter") handleSubmit();
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
                {sent ? (
                    <>
                        <h1 style={{ fontSize: 24, fontWeight: 700, color: T.ink, letterSpacing: "-0.6px", margin: "0 0 12px", lineHeight: 1.25 }}>
                            Check your email.
                        </h1>
                        <p style={{ fontSize: 13, lineHeight: 1.65, color: T.ink2, margin: "0 0 28px" }}>
                            If an account exists for <strong style={{ color: T.ink }}>{email.trim()}</strong>,
                            we've sent instructions to reset your password. The link expires in 30 minutes.
                        </p>
                        <button
                            onClick={() => onNavigate && onNavigate("Login")}
                            style={{
                                background: "none", border: "none", padding: 0,
                                fontSize: 13, fontWeight: 600, color: "var(--sv2-accent)",
                                cursor: "pointer", fontFamily: "inherit",
                            }}
                        >
                            ← Back to sign in
                        </button>
                    </>
                ) : (
                    <>
                        <div style={{ marginBottom: 32 }}>
                            <h1 style={{ fontSize: 26, fontWeight: 700, color: T.ink, letterSpacing: "-0.65px", margin: "0 0 10px", lineHeight: 1.2 }}>
                                Reset your password.
                            </h1>
                            <p style={{ fontSize: 13, lineHeight: 1.6, color: T.ink2, margin: 0 }}>
                                Enter the email on your account and we'll send you a reset link.
                            </p>
                        </div>

                        <AuthInput
                            label="Email"
                            type="email"
                            placeholder="name@company.com"
                            value={email}
                            onChange={e => setEmail(e.target.value)}
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
                            <AuthButton onClick={handleSubmit} disabled={loading}>
                                {loading ? "Sending..." : "Send reset link"}
                            </AuthButton>
                        </div>

                        <p style={{ textAlign: "center", fontSize: 12, color: T.ink2, marginTop: 20, marginBottom: 0 }}>
                            <button
                                onClick={() => onNavigate && onNavigate("Login")}
                                style={{
                                    background: "none", border: "none", padding: 0,
                                    fontSize: 12, fontWeight: 600, color: "var(--sv2-accent)",
                                    cursor: "pointer", fontFamily: "inherit",
                                }}
                            >
                                ← Back to sign in
                            </button>
                        </p>
                    </>
                )}
            </motion.div>
        </AuthLayout>
    );
}