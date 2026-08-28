import { useTheme } from "../../context/ThemeContext";
import { useLandingTheme } from "../../components/landingPage/landingTokens";
import AuthRightPanel from "./AuthRightPanel";

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
            {/* Logo on Left */}
            <div
                onClick={() => onNavigate && onNavigate("Landing")}
                style={{
                    display: "flex", alignItems: "center", gap: 10,
                    cursor: "pointer",
                }}
            >
                <div style={{
                    width: 28, height: 28, borderRadius: 8,
                    background: `linear-gradient(135deg, ${T.blue}, ${T.purple})`,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 12, fontWeight: 800, color: "#fff",
                }}>A</div>
                <span style={{ fontSize: 14, fontWeight: 700, color: T.ink, letterSpacing: "-0.3px" }}>AltInvest</span>
            </div>

            {/* Toggle on Right */}
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
                    e.currentTarget.style.background = isDark ? "rgba(255,255,255,0.06)" : "rgba(36,33,28,0.04)";
                }}
                onMouseLeave={e => {
                    e.currentTarget.style.color = T.ink2;
                    e.currentTarget.style.background = "none";
                }}
                title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
            >
                {isDark ? (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="12" cy="12" r="5" />
                        <line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" />
                        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                        <line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" />
                        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                    </svg>
                ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                    </svg>
                )}
            </button>
        </div>
    );
}

export default function AuthLayout({ children, onNavigate }) {
    const { isDark } = useTheme();
    const T = useLandingTheme();
    return (
        <div style={{
            display: "flex", height: "100vh", width: "100vw",
            background: isDark ? "#09091a" : "#f7f3ea",
            fontFamily: T.font,
            overflow: "hidden",
        }}>
            <AuthHeader onNavigate={onNavigate} />

            {/* Left panel — form */}
            <div style={{
                flex: 1,
                display: "flex", alignItems: "center", justifyContent: "center",
                background: T.bg0,
                borderRight: `1px solid ${T.border}`,
                paddingTop: 52,
            }}>
                {children}
            </div>

            {/* Right panel — decorative */}
            <AuthRightPanel />
        </div>
    );
}