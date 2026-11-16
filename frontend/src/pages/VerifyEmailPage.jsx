import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import AuthLayout from "../components/auth/AuthLayout";
import { AuthButton } from "../components/auth/AuthPrimitives";
import { authApi } from "../services/authApi";
import { describeError } from "../errors/errorCatalog";
import { isAuthenticated, setSession } from "../hooks/useAuth";
import { useLandingTheme } from "../components/landingPage/landingTokens";

// Only the first use of a link signs in, so a remount (React StrictMode runs effects twice) must
// share the first request rather than send a second one that would come back without the session.
const _verifying = new Map();
function verifyOnce(token) {
    if (!_verifying.has(token)) _verifying.set(token, authApi.verifyEmail(token));
    return _verifying.get(token);
}

// Landing page for the link in the verification email: /verify-email?token=...
export default function VerifyEmailPage({ onNavigate }) {
    const [searchParams] = useSearchParams();
    const token = searchParams.get("token");
    const [status, setStatus] = useState(token ? "working" : "error");
    const [message, setMessage] = useState(token ? "" : "This link is missing its token.");
    const T = useLandingTheme();
    const navigate = useNavigate();

    useEffect(() => {
        if (!token) return;
        let cancelled = false;
        verifyOnce(token)
            .then((res) => {
                if (cancelled) return;
                // The first use of a new account's link signs it in: straight on to onboarding.
                if (res?.token) {
                    setSession({ token: res.token, user: res.user });
                    navigate("/onboarding", { replace: true });
                    return;
                }
                setStatus("done");
            })
            .catch((err) => {
                if (cancelled) return;
                setStatus("error");
                setMessage(describeError(err).message);
            });
        return () => { cancelled = true; };
    }, [token, navigate]);

    const signedIn = isAuthenticated();
    const title = status === "working" ? "Verifying your email…" : status === "done" ? "Email verified." : "Couldn't verify your email";
    const body =
        status === "working" ? "One moment."
        : status === "done" ? "Thanks — your email address is confirmed."
        : `${message} ${signedIn ? "You can send a new link from your profile." : "Try signing in: if your email still needs confirming, we'll send you a new link."}`;

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
