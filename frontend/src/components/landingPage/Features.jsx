import { motion } from "framer-motion";
import { L } from "./landingTokens";
import { useScrollReveal } from "./landingAnimations";

function BuySignalVisual() {
    return (
        <div style={{
            background: L.bg4, borderRadius: 7, padding: "7px 14px",
            display: "flex", alignItems: "center", gap: 8, width: "100%",
        }}>
            <div style={{ width: 7, height: 7, borderRadius: "50%", background: L.green, boxShadow: `0 0 8px ${L.green}` }} />
            <span style={{ fontSize: 10.5, fontWeight: 700, color: L.green, fontFamily: "monospace", letterSpacing: "0.06em" }}>
                BUY SIGNAL DETECTED
            </span>
        </div>
    );
}

function SentimentBarsVisual() {
    const heights = [40, 60, 50, 75, 45, 65, 55];
    return (
        <div style={{ display: "flex", alignItems: "flex-end", gap: 5, height: 60, width: "100%" }}>
            {heights.map((h, i) => (
                <div key={i} style={{
                    flex: 1, height: `${h}%`, borderRadius: 3,
                    background: i % 2 === 0 ? `rgba(91,110,245,0.6)` : `rgba(155,109,255,0.5)`,
                }} />
            ))}
        </div>
    );
}

function PortfolioRingVisual() {
    return (
        <svg width="56" height="56" viewBox="0 0 56 56">
            <circle cx="28" cy="28" r="22" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" />
            <circle cx="28" cy="28" r="22" fill="none" stroke={L.blue} strokeWidth="8"
                strokeDasharray="87 51" strokeLinecap="round" transform="rotate(-90 28 28)" />
            <circle cx="28" cy="28" r="22" fill="none" stroke={L.purple} strokeWidth="8"
                strokeDasharray="28 110" strokeDashoffset="-89" strokeLinecap="round" transform="rotate(-90 28 28)" />
        </svg>
    );
}

function MarketLineVisual() {
    return (
        <svg width="100%" height="48" viewBox="0 0 200 48" preserveAspectRatio="none">
            <path d="M0,38 C20,35 40,28 60,22 C80,16 100,24 120,18 C140,12 160,8 200,4"
                fill="none" stroke={L.blue} strokeWidth="2.5" strokeLinecap="round" />
        </svg>
    );
}

const FEATURES = [
    {
        icon: "🧠", title: "AI Predictions",
        body: "Predictive signals across private markets powered by deep learning models trained on 10+ years of alternative asset data.",
        visual: <BuySignalVisual />,
    },
    {
        icon: "〜", title: "Sentiment Intelligence",
        body: "Real-time sentiment analysis from filings, news, and alternative data sources. 40M+ signals processed daily.",
        visual: <SentimentBarsVisual />,
    },
    {
        icon: "▦", title: "Portfolio Analytics",
        body: "Multi-asset visibility and risk assessment in one unified dashboard. AI-driven rebalancing recommendations.",
        visual: <PortfolioRingVisual />,
    },
    {
        icon: "↗", title: "Market Signals",
        body: "Early movement detection to position your portfolio ahead of the curve with conviction-scored entry points.",
        visual: <MarketLineVisual />,
    },
];

function FeatureCard({ icon, title, body, visual, delay }) {
    const { ref, inView } = useScrollReveal();
    return (
        <motion.div
            ref={ref}
            initial={{ opacity: 0, y: 36 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1], delay }}
            whileHover={{ y: -4, borderColor: "rgba(255,255,255,0.14)" }}
            style={{
                background: L.bg2, border: `1px solid ${L.border}`,
                borderRadius: 16, padding: "24px 24px 0",
                overflow: "hidden", display: "flex", flexDirection: "column",
                cursor: "default", transition: "border-color 0.25s",
            }}
        >
            <div style={{
                width: 40, height: 40, borderRadius: 10,
                background: "rgba(91,110,245,0.12)",
                border: `1px solid rgba(91,110,245,0.2)`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 18, marginBottom: 16,
            }}>{icon}</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: L.ink, marginBottom: 8 }}>{title}</div>
            <div style={{ fontSize: 13, color: L.ink2, lineHeight: 1.65, marginBottom: 20, flex: 1 }}>{body}</div>
            <div style={{
                height: 80, borderRadius: "8px 8px 0 0",
                background: L.bg3, border: `1px solid ${L.border}`,
                borderBottom: "none",
                display: "flex", alignItems: "center", justifyContent: "center",
                padding: "12px 16px",
            }}>
                {visual}
            </div>
        </motion.div>
    );
}

export default function Features() {
    const { ref, inView } = useScrollReveal();

    return (
        <section style={{ padding: "100px 48px", background: L.bg0, fontFamily: L.font }}>
            <motion.div
                ref={ref}
                initial={{ opacity: 0, y: 24 }}
                animate={inView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.6 }}
                style={{ textAlign: "center", marginBottom: 56 }}
            >
                <h2 style={{
                    fontSize: "clamp(32px, 4vw, 48px)", fontWeight: 800,
                    letterSpacing: "-1.5px", color: L.ink, marginBottom: 14,
                }}>
                    Intelligence at scale.
                </h2>
                <p style={{ fontSize: 16, color: L.ink2, maxWidth: 520, margin: "0 auto", lineHeight: 1.65 }}>
                    Everything you need to analyze, predict, and execute in alternative markets with unprecedented clarity.
                </p>
            </motion.div>

            <div style={{
                display: "grid", gridTemplateColumns: "repeat(4,1fr)",
                gap: 12, maxWidth: 1100, margin: "0 auto",
            }}>
                {FEATURES.map((f, i) => (
                    <FeatureCard key={f.title} {...f} delay={i * 0.08} />
                ))}
            </div>
        </section>
    );
}