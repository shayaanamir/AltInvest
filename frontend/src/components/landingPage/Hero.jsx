import { motion } from "framer-motion";
import { L } from "./landingTokens";
import { fadeUp, fadeIn } from "./landingAnimations";
import DashboardMockup from "./DashboardMockup";

function AnnouncementBar() {
    return (
        <motion.div
            {...fadeIn(0.3)}
            style={{
                display: "inline-flex", alignItems: "center", gap: 8,
                background: "rgba(91,110,245,0.1)",
                border: `1px solid rgba(91,110,245,0.25)`,
                borderRadius: 24, padding: "7px 16px",
                fontSize: 13, fontWeight: 500, color: L.ink,
                cursor: "pointer", marginBottom: 32,
            }}
        >
            <span style={{ fontSize: 14 }}>✦</span>
            <span>Introducing AltInvest 2.0 — AI signals for private markets</span>
            <span style={{ color: L.ink2 }}>→</span>
        </motion.div>
    );
}

export default function Hero({ onNavigate }) {
    return (
        <section style={{
            minHeight: "100vh",
            display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center",
            padding: "120px 48px 80px",
            position: "relative", overflow: "hidden",
            textAlign: "center",
            fontFamily: L.font,
        }}>
            {/* Ambient glows */}
            <div style={{
                position: "absolute", top: "20%", left: "50%", transform: "translateX(-50%)",
                width: 700, height: 400, borderRadius: "50%",
                background: `radial-gradient(ellipse, rgba(91,110,245,0.18) 0%, rgba(155,109,255,0.08) 50%, transparent 80%)`,
                pointerEvents: "none",
            }} />
            <div style={{
                position: "absolute", top: "10%", left: "30%",
                width: 300, height: 300, borderRadius: "50%",
                background: `radial-gradient(ellipse, rgba(155,109,255,0.08) 0%, transparent 70%)`,
                pointerEvents: "none",
            }} />

            <AnnouncementBar />

            <motion.div {...fadeUp(0.1)} style={{ marginBottom: 20 }}>
                <h1 style={{
                    fontSize: "clamp(48px, 7vw, 80px)",
                    fontWeight: 800, lineHeight: 1.05,
                    letterSpacing: "-2.5px", color: L.ink, margin: 0,
                }}>
                    AI Intelligence for<br />
                    <span style={{
                        background: `linear-gradient(135deg, ${L.blue} 0%, ${L.purple} 50%, ${L.purpleLight} 100%)`,
                        WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
                    }}>
                        Alternative Markets
                    </span>
                </h1>
            </motion.div>

            <motion.p {...fadeUp(0.22)} style={{
                fontSize: 18, color: L.ink2, lineHeight: 1.65, maxWidth: 560,
                margin: "0 0 40px",
            }}>
                Automate operations, connect your data, and eliminate blind spots
                using intelligent AI agents — built for fast-moving allocators.
            </motion.p>

            <motion.div {...fadeUp(0.32)} style={{ display: "flex", gap: 12, justifyContent: "center", marginBottom: 16 }}>
                <motion.button
                    onClick={() => onNavigate && onNavigate("Dashboard")}
                    whileHover={{ scale: 1.04, boxShadow: `0 0 28px rgba(91,110,245,0.5)` }}
                    whileTap={{ scale: 0.97 }}
                    style={{
                        background: `linear-gradient(135deg, ${L.blue}, ${L.blueDim})`,
                        border: "none", borderRadius: 12,
                        padding: "13px 28px", fontSize: 15, fontWeight: 700, color: "#fff",
                        cursor: "pointer", fontFamily: L.font,
                        boxShadow: `0 4px 24px rgba(91,110,245,0.35)`,
                    }}
                >
                    Start Free Trial →
                </motion.button>
                <motion.button
                    whileHover={{ scale: 1.03 }}
                    whileTap={{ scale: 0.97 }}
                    style={{
                        background: "rgba(255,255,255,0.05)",
                        border: `1px solid ${L.border2}`,
                        borderRadius: 12, padding: "13px 24px",
                        fontSize: 15, fontWeight: 600, color: L.ink,
                        cursor: "pointer", fontFamily: L.font,
                    }}
                >
                    ▷ Watch Demo
                </motion.button>
            </motion.div>

            <motion.p {...fadeIn(0.45)} style={{ fontSize: 12, color: L.ink3, marginBottom: 64 }}>
                No credit card required · 14-day free trial · Cancel anytime
            </motion.p>

            {/* Dashboard mockup with floating pills */}
            <motion.div
                initial={{ opacity: 0, y: 60, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1], delay: 0.5 }}
                style={{ width: "100%", maxWidth: 900, position: "relative" }}
            >
                {/* Top-left floating pill */}
                <motion.div
                    animate={{ y: [0, -6, 0] }}
                    transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                    style={{
                        position: "absolute", top: -20, left: 20, zIndex: 10,
                        background: L.bg2, border: `1px solid ${L.border2}`,
                        borderRadius: 10, padding: "10px 14px",
                        display: "flex", alignItems: "center", gap: 8,
                        boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
                    }}
                >
                    <div style={{ width: 8, height: 8, borderRadius: "50%", background: L.blue, boxShadow: `0 0 8px ${L.blue}` }} />
                    <div>
                        <div style={{ fontSize: 9.5, color: L.ink3, fontWeight: 600 }}>Active workflows</div>
                        <div style={{ fontSize: 14, fontWeight: 700, color: L.ink }}>2,431 running</div>
                    </div>
                </motion.div>

                {/* Bottom-right floating pill */}
                <motion.div
                    animate={{ y: [0, 5, 0] }}
                    transition={{ duration: 3.5, repeat: Infinity, ease: "easeInOut", delay: 0.8 }}
                    style={{
                        position: "absolute", bottom: -20, right: 20, zIndex: 10,
                        background: L.bg2, border: `1px solid ${L.border2}`,
                        borderRadius: 10, padding: "10px 16px",
                        boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
                    }}
                >
                    <div style={{ fontSize: 9.5, color: L.ink3, fontWeight: 600, marginBottom: 2 }}>Tasks automated today</div>
                    <div style={{ fontSize: 18, fontWeight: 800, color: L.green }}>+18,294</div>
                </motion.div>

                <DashboardMockup />
            </motion.div>
        </section>
    );
}