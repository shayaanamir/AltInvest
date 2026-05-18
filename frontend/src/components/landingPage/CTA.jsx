import { motion } from "framer-motion";
import { L } from "./landingTokens";
import { useScrollReveal } from "./landingAnimations";

export default function CTA({ onNavigate }) {
    const { ref, inView } = useScrollReveal();

    return (
        <section style={{ padding: "80px 48px 120px", background: L.bg0, fontFamily: L.font }}>
            <motion.div
                ref={ref}
                initial={{ opacity: 0, scale: 0.97, y: 24 }}
                animate={inView ? { opacity: 1, scale: 1, y: 0 } : {}}
                transition={{ duration: 0.75, ease: [0.22, 1, 0.36, 1] }}
                style={{
                    maxWidth: 860, margin: "0 auto",
                    background: `linear-gradient(135deg, ${L.bg3} 0%, rgba(30,32,56,0.9) 100%)`,
                    border: `1px solid rgba(91,110,245,0.2)`,
                    borderRadius: 24, padding: "72px 60px",
                    textAlign: "center", position: "relative", overflow: "hidden",
                }}
            >
                {/* Inner glow */}
                <div style={{
                    position: "absolute", top: "50%", left: "50%",
                    transform: "translate(-50%,-50%)",
                    width: 500, height: 300,
                    background: `radial-gradient(ellipse, rgba(91,110,245,0.14) 0%, transparent 70%)`,
                    pointerEvents: "none",
                }} />

                <div style={{ position: "relative" }}>
                    <h2 style={{
                        fontSize: "clamp(36px, 5vw, 60px)", fontWeight: 800,
                        letterSpacing: "-2px", lineHeight: 1.05, marginBottom: 16,
                    }}>
                        <span style={{ color: L.ink }}>Predict markets</span><br />
                        <span style={{
                            background: `linear-gradient(135deg, ${L.blue}, ${L.purple}, ${L.purpleLight})`,
                            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
                        }}>
                            before they move.
                        </span>
                    </h2>
                    <p style={{
                        fontSize: 16, color: L.ink2, marginBottom: 36,
                        maxWidth: 460, margin: "0 auto 36px", lineHeight: 1.65,
                    }}>
                        Join leading allocators using AltInvest to uncover hidden signals
                        and automate their intelligence workflows.
                    </p>
                    <motion.button
                        onClick={() => onNavigate && onNavigate("Dashboard")}
                        whileHover={{ scale: 1.04, boxShadow: "0 0 0 1px rgba(255,255,255,0.15)" }}
                        whileTap={{ scale: 0.97 }}
                        style={{
                            background: "#fff", border: "none", borderRadius: 30,
                            padding: "14px 32px", fontSize: 15, fontWeight: 700, color: L.bg0,
                            cursor: "pointer", fontFamily: L.font,
                        }}
                    >
                        Start Your Free Trial →
                    </motion.button>
                </div>
            </motion.div>
        </section>
    );
}