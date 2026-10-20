import { useState } from "react";
import { useLandingTheme } from "../landingPage/landingTokens";
import { IconEye, IconEyeOff, GoogleIcon, GitHubIcon } from "../icons";

export { GoogleIcon, GitHubIcon };

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
                        {showPassword ? <IconEyeOff size={16} /> : <IconEye size={16} />}
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