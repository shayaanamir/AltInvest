import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import AuthLayout from "../components/auth/AuthLayout";
import { AuthButton } from "../components/auth/AuthPrimitives";
import { authApi } from "../services/authApi";
import { describeError } from "../errors/errorCatalog";
import { isAuthenticated } from "../hooks/useAuth";
import { useLandingTheme } from "../components/landingPage/landingTokens";

// Landing page for the link in the verification email: /verify-email?token=...
export default function VerifyEmailPage({ onNavigate }) {
    const [searchParams] = useSearchParams();
    const token = searchParams.get("token");
    const [status, setStatus] = useState(token ? "working" : "error");
    const [message, setMessage] = useState(token ? "" : "This link is missing its token.");
    const T = useLandingTheme();

    useEffect(() => {
        if (!token) return;
        let cancelled = false;
        authApi
            .verifyEmail(token)
            .then(() => !cancelled && setStatus("done"))
            .catch((err) => {
                if (cancelled) return;
                setStatus("error");
                setMessage(describeError(err).message);
            });
        return () => { cancelled = true; };
    }, [token]);

    const signedIn = isAuthenticated();
    const title = status === "working" ? "Verifying your email…" : status === "done" ? "Email verified." : "Couldn't verify your email";
    const body =
        status === "working" ? "One moment."
        : status === "done" ? "Thanks — your email address is confirmed."
        : `${message} ${signedIn ? "You can send a new link from your profile." : "Sign in and send a new link from your profile."}`;

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
                <h1 style={{ fontSize: 22, fontWeight: 700, color: T.ink, margin: "0 0 10px" }}>{title}</h1>
                <p style={{ fontSize: 13, color: T.ink2, lineHeight: 1.6, margin: "0 0 24px" }}>{body}</p>
                {status !== "working" && (
                    <AuthButton onClick={() => onNavigate && onNavigate(signedIn ? "Profile" : "Login")}>
                        {signedIn ? "Go to your profile" : "Sign in"}
                    </AuthButton>
                )}
            </motion.div>
        </AuthLayout>
    );
}
