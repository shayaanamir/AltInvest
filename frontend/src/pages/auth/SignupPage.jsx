import { useState } from "react";
import { motion } from "framer-motion";
import { L } from "../../components/landingPage/landingTokens";
import AuthLayout from "./AuthLayout";
import { AuthInput, AuthButton, OAuthButton, Divider, GoogleIcon } from "./AuthPrimitives";

export default function SignupPage({ onNavigate }) {
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");

    const handleContinue = () => {
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
                        fontSize: 24, fontWeight: 800, color: L.ink,
                        letterSpacing: "-0.6px", margin: "0 0 6px",
                    }}>
                        Create your account.
                    </h1>
                    <p style={{ fontSize: 13, color: L.ink2, margin: 0 }}>
                        Start exploring alternative markets in minutes.
                    </p>
                </div>

                {/* Fields */}
                <AuthInput
                    label="Full Name"
                    type="text"
                    placeholder="Jane Doe"
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

                <div style={{ marginTop: 6 }}>
                    <AuthButton onClick={handleContinue}>Continue</AuthButton>
                </div>

                <Divider label="Or continue with" />

                <OAuthButton icon={<GoogleIcon />} label="Google" />

                {/* Terms */}
                <p style={{
                    textAlign: "center", fontSize: 11, color: L.ink3,
                    marginTop: 12, marginBottom: 4, lineHeight: 1.5,
                }}>
                    By signing up, you agree to our{" "}
                    <span style={{ color: L.ink2, cursor: "pointer" }}>Terms</span>
                    {" "}and{" "}
                    <span style={{ color: L.ink2, cursor: "pointer" }}>Privacy Policy</span>.
                </p>

                {/* Footer link */}
                <p style={{
                    textAlign: "center", fontSize: 12.5, color: L.ink2, marginTop: 10, marginBottom: 0,
                }}>
                    Already have an account?{" "}
                    <button
                        onClick={() => onNavigate && onNavigate("Login")}
                        style={{
                            background: "none", border: "none", padding: 0,
                            fontSize: 12.5, fontWeight: 700, color: L.blue,
                            cursor: "pointer", fontFamily: "inherit",
                        }}
                    >
                        Sign in
                    </button>
                </p>
            </motion.div>
        </AuthLayout>
    );
}