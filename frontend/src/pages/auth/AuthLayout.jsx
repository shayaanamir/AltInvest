import { L } from "../../components/landingPage/landingTokens";
import AuthRightPanel from "./AuthRightPanel";

function AuthLogo({ onNavigate }) {
    return (
        <div
            onClick={() => onNavigate && onNavigate("Landing")}
            style={{
                position: "fixed", top: 0, left: 0, right: 0, zIndex: 10,
                height: 52,
                display: "flex", alignItems: "center",
                padding: "0 28px", gap: 10,
                cursor: "pointer",
            }}
        >
            <div style={{
                width: 28, height: 28, borderRadius: 8,
                background: `linear-gradient(135deg, ${L.blue}, ${L.purple})`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 12, fontWeight: 800, color: "#fff",
            }}>A</div>
            <span style={{ fontSize: 14, fontWeight: 700, color: L.ink, letterSpacing: "-0.3px" }}>AltInvest</span>
        </div>
    );
}

export default function AuthLayout({ children, onNavigate }) {
    return (
        <div style={{
            display: "flex", height: "100vh", width: "100vw",
            background: "#09091a",
            fontFamily: "'DM Sans', 'Segoe UI', sans-serif",
            overflow: "hidden",
        }}>
            <AuthLogo onNavigate={onNavigate} />

            {/* Left panel — form */}
            <div style={{
                flex: 1,
                display: "flex", alignItems: "center", justifyContent: "center",
                background: "#08090F",
                borderRight: `1px solid rgba(255,255,255,0.06)`,
                paddingTop: 52,
            }}>
                {children}
            </div>

            {/* Right panel — decorative */}
            <AuthRightPanel />
        </div>
    );
}