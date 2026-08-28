import { motion } from "framer-motion";
import { useTheme } from "../../context/ThemeContext";
import { useLandingTheme } from "./landingTokens";
import { fadeUp, fadeIn } from "./landingAnimations";
import SoftAurora from "./motionEffects/SoftAurora";
import ShinyText from "./motionEffects/ShinyText";


function AnnouncementBar({ T }) {
    return (
        <motion.div
            {...fadeIn(0.3)}
            style={{
                display: "inline-flex", alignItems: "center", gap: 8,
                background: "color-mix(in srgb, var(--sv2-accent) 10%, transparent)",
                border: "1px solid color-mix(in srgb, var(--sv2-accent) 25%, transparent)",
                borderRadius: 24, padding: "7px 16px",
                fontSize: 13, fontWeight: 500, color: T.ink,
                marginBottom: 32,
            }}
        >
            <span style={{ fontSize: 14 }}>✦</span>
            <span>Track crypto, commodities, NFTs, and tokenized assets</span>
            <span style={{ color: T.ink2 }}>→</span>
        </motion.div>
    );
}

export default function Hero({ onNavigate }) {
    const { isDark } = useTheme();
    const T = useLandingTheme();

    return (

        <section style={{
            minHeight: "100vh",
            display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center",
            padding: "60px 48px 0",
            boxSizing: "border-box",
            position: "relative", overflow: "hidden",
            textAlign: "center",
            fontFamily: T.font,
            background: T.bg0,
        }}>
            <div style={{ position: "absolute", inset: 0, zIndex: 0, pointerEvents: "none" }}>
                <SoftAurora
                    speed={0.7}
                    scale={1.3}
                    brightness={isDark ? 1 : 0.85}
                    color1={isDark ? "#f7f7f7" : "#ffb37e"}
                    color2={isDark ? "#e100ff" : "#bfa3ff"}
                    noiseFrequency={2.5}
                    noiseAmplitude={10}
                    bandHeight={0.55}
                    bandSpread={0.5}
                    octaveDecay={0}
                    layerOffset={1}
                    colorSpeed={0.5}
                    enableMouseInteraction
                    mouseInfluence={0.1}
                />
                <div style={{
                    position: "absolute", inset: 0,
                    background: isDark ? "rgba(8, 9, 15, 0.3)" : "rgba(250, 247, 241, 0.55)",
                    backdropFilter: "blur(12px)",
                    WebkitBackdropFilter: "blur(12px)",
                }} />
            </div>

            <div style={{ position: "relative", zIndex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}>

                <AnnouncementBar T={T} />

                <motion.div {...fadeUp(0.1)} style={{ marginBottom: 20 }}>
                    <h1 style={{
                        fontSize: "clamp(48px, 7vw, 80px)",
                        fontWeight: 800, lineHeight: 1.2,
                        letterSpacing: "-2.5px", color: T.ink, margin: 0,
                        paddingBottom: "10px",
                    }}>
                        Modern Market Intelligence for<br />
                        <ShinyText
                            text="Alternative Assets"
                            speed={2}
                            delay={0}
                            color={isDark ? "#c4a0ff" : "#6d28d9"}
                            shineColor={isDark ? "#9b6dff" : "#4c1d95"}
                            spread={120}
                            direction="left"
                            yoyo={false}
                            pauseOnHover={false}
                            disabled={false}
                        />
                    </h1>

                </motion.div>

                <motion.p {...fadeUp(0.22)} style={{
                    fontSize: 18, color: T.ink2, lineHeight: 1.65, maxWidth: 560,
                    margin: "0 0 40px",
                }}>
                    Monitor sentiment, track market trends, and uncover predictive signals across crypto, commodities, NFTs, and tokenized assets.
                </motion.p>

                <motion.div {...fadeUp(0.32)} style={{ display: "flex", gap: 12, justifyContent: "center", marginBottom: 16 }}>
                    <motion.button
                        onClick={() => onNavigate && onNavigate("Login")}
                        whileHover={{ scale: 1.04, boxShadow: "0 0 28px color-mix(in srgb, var(--sv2-accent) 50%, transparent)" }}
                        whileTap={{ scale: 0.97 }}
                        style={{
                            background: "linear-gradient(135deg, var(--sv2-accent), color-mix(in srgb, var(--sv2-accent) 70%, black))",
                            border: "none", borderRadius: 12,
                            padding: "13px 28px", fontSize: 15, fontWeight: 700, color: "#fff",
                            cursor: "pointer", fontFamily: T.font,
                            boxShadow: "0 4px 24px color-mix(in srgb, var(--sv2-accent) 35%, transparent)",
                        }}
                    >
                        Enter Platform
                    </motion.button>
                    <motion.button
                        onClick={() => onNavigate && onNavigate("Signup")}
                        whileHover={{ scale: 1.03 }}
                        whileTap={{ scale: 0.97 }}
                        style={{
                            background: "var(--sv2-card-alt)",
                            border: `1px solid ${T.border2}`,
                            borderRadius: 12, padding: "13px 24px",
                            fontSize: 15, fontWeight: 600, color: T.ink,
                            cursor: "pointer", fontFamily: T.font,
                        }}
                    >
                        Sign Up
                    </motion.button>
                </motion.div>

                <motion.p {...fadeIn(0.45)} style={{ fontSize: 12, color: T.ink3, marginBottom: 64 }}>
                    Crypto • NFTs • Commodities • Tokenized Assets
                </motion.p>

            </div>
        </section>
    );
}