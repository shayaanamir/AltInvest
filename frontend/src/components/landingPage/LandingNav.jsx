import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { L } from "./landingTokens";

export default function LandingNav({ onNavigate }) {
    const [scrolled, setScrolled] = useState(false);

    useEffect(() => {
        const h = () => setScrolled(window.scrollY > 40);
        window.addEventListener("scroll", h);
        return () => window.removeEventListener("scroll", h);
    }, []);

    return (
        <motion.nav
            initial={{ y: -56, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            style={{
                position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
                height: 60,
                display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "0 48px",
                background: scrolled ? "rgba(8,9,15,0.92)" : "transparent",
                backdropFilter: scrolled ? "blur(18px)" : "none",
                borderBottom: scrolled ? `1px solid ${L.border}` : "1px solid transparent",
                transition: "background 0.4s, backdrop-filter 0.4s, border-color 0.4s",
                fontFamily: L.font,
            }}
        >
            {/* Logo */}
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <img src="/altinvest_logo.png" alt="AltInvest Logo" style={{ height: 32, borderRadius: 8, objectFit: "contain" }} />
                <span style={{ fontSize: 15, fontWeight: 700, color: L.ink, letterSpacing: "-0.3px" }}>AltInvest</span>
            </div>

            {/* Links */}
            <div style={{ display: "flex", gap: 32 }}>
                {["Platform", "Signals", "Analytics", "Portfolio"].map(label => (
                    <a
                        key={label}
                        href="#"
                        style={{ fontSize: 13.5, color: L.ink2, textDecoration: "none", fontWeight: 500, transition: "color 0.15s" }}
                        onMouseEnter={e => e.target.style.color = L.ink}
                        onMouseLeave={e => e.target.style.color = L.ink2}
                    >
                        {label}
                    </a>
                ))}
            </div>

            {/* CTA */}
            <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                <a
                    href="#"
                    onClick={(e) => { e.preventDefault(); onNavigate && onNavigate("Login"); }}
                    style={{ fontSize: 13.5, color: L.ink2, textDecoration: "none", fontWeight: 500 }}
                >
                    Sign In
                </a>
                <motion.button
                    onClick={() => onNavigate && onNavigate("Signup")}
                    whileHover={{ scale: 1.03 }}
                    whileTap={{ scale: 0.97 }}
                    style={{
                        background: "#fff", border: "none", borderRadius: 24,
                        padding: "8px 20px", fontSize: 13.5, fontWeight: 700, color: L.bg0,
                        cursor: "pointer", fontFamily: L.font,
                    }}
                >
                    Get Access
                </motion.button>
            </div>
        </motion.nav>
    );
}