import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { OAuthButton, GoogleIcon } from "./AuthPrimitives";
import { authApi } from "../../services/authApi";
import { getGoogleConfig, preloadGoogle, requestGoogleCode, GoogleCancelled } from "../../services/googleAuth";
import { resolveLandingPath } from "../../services/appPreferences";
import { setSession } from "../../hooks/useAuth";
import { describeError } from "../../errors/errorCatalog";

/**
 * "Continue with Google" for the login and signup pages. Signs in, or creates the account on first
 * use; a new account goes to onboarding, an existing one to `returnPath` or the user's landing page.
 * Errors are reported through `onError` so each page shows them in its own error box.
 */
export default function GoogleSignInButton({ returnPath, onError, label = "Google" }) {
    const [enabled, setEnabled] = useState(null); // null while checking the server's config
    const [busy, setBusy] = useState(false);
    const navigate = useNavigate();

    useEffect(() => {
        let live = true;
        getGoogleConfig().then((c) => live && setEnabled(c.enabled));
        preloadGoogle();
        return () => { live = false; };
    }, []);

    const handleClick = async () => {
        if (busy) return;
        onError?.(null);
        setBusy(true);
        try {
            const code = await requestGoogleCode();
            const response = await authApi.googleSignIn(code);
            setSession({ token: response.token, user: response.user });
            if (response.created) navigate("/onboarding", { replace: true });
            else navigate(returnPath || (await resolveLandingPath()), { replace: true });
        } catch (err) {
            if (!(err instanceof GoogleCancelled)) {
                onError?.(err?.kind ? describeError(err).message : err.message);
            }
        } finally {
            setBusy(false);
        }
    };

    return (
        <OAuthButton
            icon={<GoogleIcon />}
            label={busy ? "Connecting…" : label}
            onClick={handleClick}
            disabled={enabled !== true || busy}
            title={enabled === false ? "Google sign-in isn't set up on this server" : undefined}
        />
    );
}
