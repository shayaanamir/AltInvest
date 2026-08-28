import { useTheme } from "../../context/ThemeContext";
import { useLandingTheme } from "../../components/landingPage/landingTokens";
import AuthRightPanel from "./AuthRightPanel";
import { IconThemeToggle } from "../../components/icons";

function AuthHeader({ onNavigate }) {
    const { isDark, toggle } = useTheme();
    const T = useLandingTheme();
    return (
        <div
            style={{
                position: "fixed", top: 0, left: 0, right: 0, zIndex: 10,
                height: 52,
                display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "0 28px",
            }}
        >
            <div
                onClick={() => onNavigate && onNavigate("Landing")}
                style={{
                    display: "flex", alignItems: "center", gap: 10,
                    cursor: "pointer",
                }}
            >
                <div style={{
                    width: 28, height: 28, borderRadius: 8,
                    background: "var(--sv2-accent)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 12, fontWeight: 800, color: "#fff",
                }}>A</div>
                <span style={{ fontSize: 14, fontWeight: 700, color: T.ink, letterSpacing: "-0.3px" }}>AltInvest</span>
            </div>

            <button
                onClick={toggle}
                style={{
                    background: "none", border: "none", cursor: "pointer",
                    color: T.ink2, display: "flex", alignItems: "center", justifyContent: "center",
                    padding: 8, borderRadius: "50%",
                    transition: "background 0.15s, color 0.15s",
                }}
                onMouseEnter={e => {
                    e.currentTarget.style.color = T.ink;
                    e.currentTarget.style.background = "var(--sv2-chip)";
                }}
                onMouseLeave={e => {
                    e.currentTarget.style.color = T.ink2;
                    e.currentTarget.style.background = "none";
                }}
                title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
            >
                <IconThemeToggle isDark={isDark} variant="outline" size={16} />
            </button>
        </div>
    );
}

export default function AuthLayout({ children, onNavigate }) {
    const T = useLandingTheme();
    return (
        <div className="sv2" style={{
            display: "flex", height: "100vh", width: "100vw",
            background: "var(--sv2-bg)",
            fontFamily: T.font,
            overflow: "hidden",
        }}>
            <AuthHeader onNavigate={onNavigate} />

            <div style={{
                flex: 1,
                display: "flex", alignItems: "center", justifyContent: "center",
                background: "var(--sv2-bg)",
                borderRight: `1px solid ${T.border}`,
                paddingTop: 52,
            }}>
                {children}
            </div>

            <AuthRightPanel />
        </div>
    );
}