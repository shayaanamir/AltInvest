import { useState } from "react";
import { useLandingTheme } from "../landingPage/landingTokens";

export function AuthInput({ label, type = "text", placeholder, value, onChange }) {
    const [focused, setFocused] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    const isPassword = type === "password";
    const currentType = isPassword ? (showPassword ? "text" : "password") : type;

    const T = useLandingTheme();

    return (
        <div style={{ marginBottom: 14 }}>
            <label style={{
                display: "block", fontSize: 11.5, fontWeight: 500,
                color: T.ink2, marginBottom: 6,
            }}>
                {label}
            </label>
            <div style={{ position: "relative" }}>
                <input
                    type={currentType}
                    placeholder={placeholder}
                    value={value}
                    onChange={onChange}
                    onFocus={() => setFocused(true)}
                    onBlur={() => setFocused(false)}
                    style={{
                        width: "100%", boxSizing: "border-box",
                        background: "var(--sv2-input, var(--sv2-card-alt))",
                        border: `1px solid ${focused ? "color-mix(in srgb, var(--sv2-accent) 50%, transparent)" : T.border2}`,
                        borderRadius: 8, padding: "11px 14px",
                        paddingLeft: 14,
                        paddingRight: isPassword ? 38 : 14,
                        fontSize: 13.5, color: T.ink,
                        outline: "none", fontFamily: "inherit",
                        transition: "border-color 0.2s, box-shadow 0.2s",
                        boxShadow: focused ? "0 0 0 3px color-mix(in srgb, var(--sv2-accent) 12%, transparent)" : "none",
                    }}
                />
                {isPassword && (
                    <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        style={{
                            position: "absolute",
                            right: 14,
                            top: "50%",
                            transform: "translateY(-50%)",
                            background: "none",
                            border: "none",
                            padding: 0,
                            color: T.ink3,
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                        }}
                    >
                        {showPassword ? (
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                                <path d="M16 8s-3-5.5-8-5.5S0 8 0 8s3 5.5 8 5.5S16 8 16 8M1.173 8a13 13 0 0 1 1.66-2.043C4.12 4.668 5.88 3.5 8 3.5s3.879 1.168 5.168 2.457A13 13 0 0 1 14.828 8q-.086.13-.195.288c-.335.48-.83 1.12-1.465 1.755C11.879 11.332 10.119 12.5 8 12.5s-3.879-1.168-5.168-2.457A13 13 0 0 1 1.172 8z" />
                                <path d="M8 5.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5M4.5 8a3.5 3.5 0 1 1 7 0 3.5 3.5 0 0 1-7 0" />
                            </svg>
                        ) : (
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                                <path d="M13.359 11.238C15.06 9.72 16 8 16 8s-3-5.5-8-5.5a7 7 0 0 0-2.79.588l.77.771A6 6 0 0 1 8 3.5c2.12 0 3.879 1.168 5.168 2.457A13 13 0 0 1 14.828 8q-.086.13-.195.288c-.335.48-.83 1.12-1.465 1.755q-.247.248-.517.486z" />
                                <path d="M11.297 9.176a3.5 3.5 0 0 0-4.474-4.474l.823.823a2.5 2.5 0 0 1 2.829 2.829zm-2.943 1.299.822.822a3.5 3.5 0 0 1-4.474-4.474l.823.823a2.5 2.5 0 0 0 2.829 2.829" />
                                <path d="M3.35 5.47q-.27.24-.518.487A13 13 0 0 0 1.172 8l.195.288c.335.48.83 1.12 1.465 1.755C4.121 11.332 5.881 12.5 8 12.5c.716 0 1.39-.133 2.02-.36l.77.772A7 7 0 0 1 8 13.5C3 13.5 0 8 0 8s.939-1.721 2.641-3.238l.708.709zm10.296 8.884-12-12 .708-.708 12 12z" />
                            </svg>
                        )}
                    </button>
                )}
            </div>
        </div>
    );
}

export function AuthButton({ children, onClick, disabled = false, style: extra }) {
    return (
        <button
            onClick={disabled ? undefined : onClick}
            disabled={disabled}
            style={{
                width: "100%", padding: "12px",
                background: "linear-gradient(135deg, var(--sv2-accent), color-mix(in srgb, var(--sv2-accent) 70%, black))",
                border: "none", borderRadius: 8,
                fontSize: 14, fontWeight: 700, color: "#fff",
                cursor: disabled ? "not-allowed" : "pointer",
                opacity: disabled ? 0.65 : 1,
                fontFamily: "inherit",
                transition: "opacity 0.15s, transform 0.1s",
                ...extra,
            }}
            onMouseEnter={e => { if (!disabled) e.currentTarget.style.opacity = "0.9"; }}
            onMouseLeave={e => { if (!disabled) e.currentTarget.style.opacity = "1"; }}
            onMouseDown={e => { if (!disabled) e.currentTarget.style.transform = "scale(0.985)"; }}
            onMouseUp={e => { if (!disabled) e.currentTarget.style.transform = "scale(1)"; }}
        >
            {children}
        </button>
    );
}

export function OAuthButton({ icon, label, onClick, disabled = false, title }) {
    const [hov, setHov] = useState(false);
    const T = useLandingTheme();
    return (
        <button
            onClick={disabled ? undefined : onClick}
            disabled={disabled}
            title={title}
            onMouseEnter={() => !disabled && setHov(true)}
            onMouseLeave={() => setHov(false)}
            style={{
                width: "100%", padding: "11px",
                background: hov && !disabled ? "var(--sv2-chip)" : "var(--sv2-card-alt)",
                border: `1px solid ${T.border}`,
                borderRadius: 8, fontSize: 13, fontWeight: 500, color: T.ink,
                cursor: disabled ? "not-allowed" : "pointer",
                opacity: disabled ? 0.5 : 1,
                display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
                transition: "background 0.15s",
                marginBottom: 10,
                fontFamily: "inherit",
            }}
        >
            {icon}
            {label}
        </button>
    );
}

export function Divider({ label = "Or continue with" }) {
    const T = useLandingTheme();
    return (
        <div style={{
            display: "flex", alignItems: "center", gap: 12,
            margin: "20px 0 16px",
        }}>
            <div style={{ flex: 1, height: 1, background: T.border }} />
            <span style={{ fontSize: 11.5, color: T.ink3, whiteSpace: "nowrap" }}>{label}</span>
            <div style={{ flex: 1, height: 1, background: T.border }} />
        </div>
    );
}

export function GoogleIcon() {
    return (
        <svg width="16" height="16" viewBox="0 0 18 18">
            <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4" />
            <path d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.258c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332C2.438 15.983 5.482 18 9 18z" fill="#34A853" />
            <path d="M3.964 10.707c-.18-.54-.282-1.117-.282-1.707s.102-1.167.282-1.707V4.961H.957C.347 6.173 0 7.548 0 9s.348 2.827.957 4.039l3.007-2.332z" fill="#FBBC05" />
            <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0 5.482 0 2.438 2.017.957 4.961L3.964 6.293C4.672 4.166 6.656 3.58 9 3.58z" fill="#EA4335" />
        </svg>
    );
}

export function GitHubIcon() {
    const T = useLandingTheme();
    return (
        <svg width="16" height="16" viewBox="0 0 24 24" fill={T.ink}>
            <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z" />
        </svg>
    );
}