import { motion } from "framer-motion";
import { L } from "./landingTokens";
import { fadeUp, fadeIn } from "./landingAnimations";
import SoftAurora from "./motionEffects/SoftAurora";
import ShinyText from "./motionEffects/ShinyText";

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
            <span>Track crypto, commodities, NFTs, and tokenized assets</span>
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
            padding: "60px 48px 0", // Offset for fixed navbar
            boxSizing: "border-box",
            position: "relative", overflow: "hidden",
            textAlign: "center",
            fontFamily: L.font,
        }}>
            {/* SoftAurora Background */}
            <div style={{ position: "absolute", inset: 0, zIndex: 0, pointerEvents: "none" }}>
                <SoftAurora
                    speed={0.7}
                    scale={1.3}
                    brightness={1}
                    color1="#f7f7f7"
                    color2="#e100ff"
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
                {/* Glassmorphism Overlay */}
                <div style={{
                    position: "absolute", inset: 0,
                    background: "rgba(8, 9, 15, 0.3)",
                    backdropFilter: "blur(12px)",
                    WebkitBackdropFilter: "blur(12px)",
                }} />
            </div>

            {/* Ambient glows and rest of content needs a higher zIndex so they aren't hidden by Aurora if it acts weird, though Aurora is zIndex 0. To be safe, put a relative container. */}
            <div style={{ position: "relative", zIndex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}>

                <AnnouncementBar />

                <motion.div {...fadeUp(0.1)} style={{ marginBottom: 20 }}>
                    <h1 style={{
                        fontSize: "clamp(48px, 7vw, 80px)",
                        fontWeight: 800, lineHeight: 1.2,
                        letterSpacing: "-2.5px", color: L.ink, margin: 0,
                        paddingBottom: "10px", // Prevents clipping of text descenders
                    }}>
                        Modern Market Intelligence for<br />
                        <ShinyText
                            text="Alternative Assets"
                            speed={1}
                            delay={0}
                            color={L.purpleLight}
                            shineColor={L.purple}
                            spread={120}
                            direction="left"
                            yoyo={false}
                            pauseOnHover={false}
                            disabled={false}
                        />
                    </h1>
                </motion.div>

                <motion.p {...fadeUp(0.22)} style={{
                    fontSize: 18, color: L.ink2, lineHeight: 1.65, maxWidth: 560,
                    margin: "0 0 40px",
                }}>
                    Monitor sentiment, track market trends, and uncover predictive signals across crypto, commodities, NFTs, and tokenized assets.
                </motion.p>

                <motion.div {...fadeUp(0.32)} style={{ display: "flex", gap: 12, justifyContent: "center", marginBottom: 16 }}>
                    <motion.button
                        onClick={() => onNavigate && onNavigate("Signup")}
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
                        Enter Platform
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
                        Sign Up
                    </motion.button>
                </motion.div>

                <motion.p {...fadeIn(0.45)} style={{ fontSize: 12, color: L.ink3, marginBottom: 64 }}>
                    Crypto • NFTs • Commodities • Tokenized Assets
                </motion.p>

            </div>
        </section>
    );
}