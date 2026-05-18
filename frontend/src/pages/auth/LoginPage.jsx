import { useState } from "react";
import { motion } from "framer-motion";
import { L } from "../../components/landingPage/landingTokens";
import AuthLayout from "./AuthLayout";
import { AuthInput, AuthButton, OAuthButton, Divider, GoogleIcon, GitHubIcon } from "./AuthPrimitives";

export default function LoginPage({ onNavigate }) {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");

    const handleSignIn = () => {
        // Navigate to dashboard on sign in
        onNavigate && onNavigate("Dashboard");
    };

    return (
        <AuthLayout onNavigate={onNavigate}>
            <motion.div
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
                style={{
                    width: "100%", maxWidth: 320,
                    padding: "32px 28px",
                    background: "rgba(255,255,255,0.03)",
                    border: "1px solid rgba(255,255,255,0.07)",
                    borderRadius: 16,
                    boxShadow: "0 24px 64px rgba(0,0,0,0.4)",
                }}
            >
                {/* Header */}
                <div style={{ marginBottom: 24 }}>
                    <h1 style={{
                        fontSize: 26, fontWeight: 800, color: L.ink,
                        letterSpacing: "-0.6px", margin: "0 0 6px",
                    }}>
                        Welcome back.
                    </h1>
                    <p style={{ fontSize: 13, color: L.ink2, margin: 0 }}>
                        Sign in to access your intelligence workspace.
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
                            fontSize: 11.5, color: L.ink2, cursor: "pointer",
                            fontFamily: "inherit", padding: 0,
                        }}
                        onMouseEnter={e => e.currentTarget.style.color = L.ink}
                        onMouseLeave={e => e.currentTarget.style.color = L.ink2}
                    >
                        Forgot password?
                    </button>
                </div>

                {/* Sign in */}
                <div style={{ marginTop: 6 }}>
                    <AuthButton onClick={handleSignIn}>Sign In</AuthButton>
                </div>

                <Divider label="Or continue with" />

                <OAuthButton icon={<GoogleIcon />} label="Google" />
                <OAuthButton icon={<GitHubIcon />} label="GitHub" />

                {/* Footer link */}
                <p style={{
                    textAlign: "center", fontSize: 12.5, color: L.ink2, marginTop: 16, marginBottom: 0,
                }}>
                    Don't have an account?{" "}
                    <button
                        onClick={() => onNavigate && onNavigate("Signup")}
                        style={{
                            background: "none", border: "none", padding: 0,
                            fontSize: 12.5, fontWeight: 700, color: L.blue,
                            cursor: "pointer", fontFamily: "inherit",
                            textDecoration: "none",
                        }}
                    >
                        Sign up
                    </button>
                </p>
            </motion.div>
        </AuthLayout>
    );
}