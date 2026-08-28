import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useTheme } from "../../context/ThemeContext";
import { useLandingTheme } from "./landingTokens";

export default function LandingNav({ onNavigate }) {
    const [scrolled, setScrolled] = useState(false);
    const { isDark, toggle } = useTheme();
    const T = useLandingTheme();

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
                background: scrolled
                    ? (isDark ? "rgba(8,9,15,0.92)" : "rgba(250,247,241,0.92)")
                    : "transparent",
                backdropFilter: scrolled ? "blur(18px)" : "none",
                borderBottom: scrolled ? `1px solid ${T.border}` : "1px solid transparent",
                transition: "background 0.4s, backdrop-filter 0.4s, border-color 0.4s",
                fontFamily: T.font,
            }}
        >
            {/* Logo */}
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <img src="/altinvest_logo.png" alt="AltInvest Logo" style={{ height: 32, borderRadius: 8, objectFit: "contain" }} />
                <span style={{ fontSize: 15, fontWeight: 700, color: T.ink, letterSpacing: "-0.3px" }}>AltInvest</span>
            </div>

            {/* Links */}
            <div style={{ display: "flex", gap: 32 }}>
                {[
                    { label: "Home", id: "home" },
                    { label: "Platform", id: "platform" },
                    { label: "Analytics", id: "analytics" },
                    { label: "Capabilities", id: "capabilities" },
                    { label: "Access", id: "access" }
                ].map(item => (
                    <a
                        key={item.label}
                        href={`#${item.id}`}
                        onClick={(e) => {
                            e.preventDefault();
                            document.getElementById(item.id)?.scrollIntoView({ behavior: "smooth" });
                        }}
                        style={{ fontSize: 13.5, color: T.ink2, textDecoration: "none", fontWeight: 500, transition: "color 0.15s" }}
                        onMouseEnter={e => e.target.style.color = T.ink}
                        onMouseLeave={e => e.target.style.color = T.ink2}
                    >
                        {item.label}
                    </a>
                ))}
            </div>

            {/* CTA */}
            <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
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
                <a
                    href="#"
                    onClick={(e) => { e.preventDefault(); onNavigate && onNavigate("Login"); }}
                    style={{ fontSize: 13.5, color: T.ink2, textDecoration: "none", fontWeight: 500 }}
                >
                    Sign In
                </a>
                <motion.button
                    onClick={() => onNavigate && onNavigate("Signup")}
                    whileHover={{ scale: 1.03 }}
                    whileTap={{ scale: 0.97 }}
                    style={{
                        background: isDark ? "#fff" : T.ink,
                        border: "none", borderRadius: 24,
                        padding: "8px 20px", fontSize: 13.5, fontWeight: 700,
                        color: isDark ? T.bg0 : "#fff",
                        cursor: "pointer", fontFamily: T.font,
                    }}
                >
                    Get Access
                </motion.button>
            </div>
        </motion.nav>
    );
}