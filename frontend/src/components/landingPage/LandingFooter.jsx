import { L } from "./landingTokens";

export default function LandingFooter() {
    return (
        <footer style={{
            borderTop: `1px solid ${L.border}`,
            padding: "28px 48px",
            display: "flex", alignItems: "center", justifyContent: "space-between",
            background: L.bg0, fontFamily: L.font,
        }}>
            <div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                    <div style={{
                        width: 26, height: 26, borderRadius: 7,
                        background: `linear-gradient(135deg, ${L.blue}, ${L.purple})`,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 11, fontWeight: 800, color: "#fff",
                    }}>A</div>
                    <span style={{ fontSize: 13.5, fontWeight: 700, color: L.ink }}>AltInvest</span>
                </div>
                <div style={{ fontSize: 11.5, color: L.ink3 }}>© 2026 AltInvest Intelligence. All rights reserved.</div>
            </div>

            <div style={{ display: "flex", gap: 24 }}>
                {["Privacy Policy", "Terms of Service", "Contact"].map(label => (
                    <a
                        key={label}
                        href="#"
                        style={{ fontSize: 12.5, color: L.ink2, textDecoration: "none", transition: "color 0.15s" }}
                        onMouseEnter={e => e.target.style.color = L.ink}
                        onMouseLeave={e => e.target.style.color = L.ink2}
                    >
                        {label}
                    </a>
                ))}
            </div>
        </footer>
    );
}