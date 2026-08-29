import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import AuthLayout from "../components/auth/AuthLayout";
import { AuthInput, AuthButton } from "../components/auth/AuthPrimitives";
import { authApi } from "../services/authApi";
import { useLandingTheme } from "../components/landingPage/landingTokens";

export default function ResetPasswordPage({ onNavigate }) {
    const [searchParams] = useSearchParams();
    const token = searchParams.get("token");

    const [password, setPassword] = useState("");
    const [confirm, setConfirm] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [done, setDone] = useState(false);

    const T = useLandingTheme();

    const handleSubmit = async () => {
        setError(null);
        if (!token) {
            setError("This reset link is invalid or has expired.");
            return;
        }
        if (password.length < 8) {
            setError("Password must be at least 8 characters.");
            return;
        }
        if (password !== confirm) {
            setError("Passwords don't match.");
            return;
        }
        setLoading(true);
        try {
            await authApi.resetPassword(token, password);
            setDone(true);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === "Enter") handleSubmit();
    };

    // No token at all in the URL — don't bother rendering the form.
    if (!token) {
        return (
            <AuthLayout onNavigate={onNavigate}>
                <motion.div
                    initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                    style={{
                        width: "100%", maxWidth: 420, padding: "40px 32px",
                        background: "var(--sv2-card-alt)", border: `1px solid ${T.border2}`, borderRadius: 16,
                    }}
                >
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: T.ink, margin: "0 0 10px" }}>Invalid reset link</h1>
                    <p style={{ fontSize: 13, color: T.ink2, lineHeight: 1.6, margin: "0 0 24px" }}>
                        This link is missing its token. Request a new one below.
                    </p>
                    <AuthButton onClick={() => onNavigate && onNavigate("ForgotPassword")}>
                        Request a new link
                    </AuthButton>
                </motion.div>
            </AuthLayout>
        );
    }

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
                {done ? (
                    <>
                        <h1 style={{ fontSize: 24, fontWeight: 700, color: T.ink, letterSpacing: "-0.6px", margin: "0 0 12px", lineHeight: 1.25 }}>
                            Password updated.
                        </h1>
                        <p style={{ fontSize: 13, lineHeight: 1.65, color: T.ink2, margin: "0 0 28px" }}>
                            You can now sign in with your new password.
                        </p>
                        <AuthButton onClick={() => onNavigate && onNavigate("Login")}>
                            Sign in
                        </AuthButton>
                    </>
                ) : (
                    <>
                        <div style={{ marginBottom: 32 }}>
                            <h1 style={{ fontSize: 26, fontWeight: 700, color: T.ink, letterSpacing: "-0.65px", margin: "0 0 10px", lineHeight: 1.2 }}>
                                Choose a new password.
                            </h1>
                            <p style={{ fontSize: 13, lineHeight: 1.6, color: T.ink2, margin: 0 }}>
                                Must be at least 8 characters.
                            </p>
                        </div>

                        <AuthInput
                            label="New password"
                            type="password"
                            placeholder="••••••••"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                        />
                        <AuthInput
                            label="Confirm new password"
                            type="password"
                            placeholder="••••••••"
                            value={confirm}
                            onChange={e => setConfirm(e.target.value)}
                        />

                        <div style={{ marginTop: 8 }}>
                            {error && (
                                <div style={{
                                    color: "var(--sv2-red)", fontSize: 12, marginBottom: 12,
                                    background: "var(--sv2-red-soft)", padding: "8px 12px",
                                    borderRadius: 6, border: "1px solid color-mix(in srgb, var(--sv2-red) 20%, transparent)"
                                }}>
                                    {error}
                                    {/expired|invalid/i.test(error) && (
                                        <>
                                            {" "}
                                            <button
                                                onClick={() => onNavigate && onNavigate("ForgotPassword")}
                                                style={{ background: "none", border: "none", padding: 0, color: "inherit", textDecoration: "underline", cursor: "pointer", fontFamily: "inherit", fontSize: "inherit" }}
                                            >
                                                Request a new link
                                            </button>
                                        </>
                                    )}
                                </div>
                            )}
                            <AuthButton onClick={handleSubmit} disabled={loading}>
                                {loading ? "Updating..." : "Update password"}
                            </AuthButton>
                        </div>
                    </>
                )}
            </motion.div>
        </AuthLayout>
    );
}