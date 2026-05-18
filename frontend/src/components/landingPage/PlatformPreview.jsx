import { motion } from "framer-motion";
import { L } from "./landingTokens";
import { useScrollReveal } from "./landingAnimations";

const CAPABILITIES = [
    { icon: "⛓", title: "Asset Analytics", desc: "Track wallet activity, market movement, and asset behavior across modern investment ecosystems." },
    { icon: "⚠", title: "Risk Analytics", desc: "Analyze volatility, liquidity, and market exposure across different asset classes." },
    { icon: "✦", title: "Alternative Asset Scoring", desc: "Compare alternative assets through unified scoring based on sentiment, momentum, and market activity." },
    { icon: "₿", title: "Market Discovery", desc: "Discover emerging assets and market trends across crypto, commodities, NFTs, and tokenized markets." },
    { icon: "◎", title: "Portfolio Optimizer", desc: "Track allocation, diversification, and portfolio performance across multiple asset categories." },
    { icon: "〜", title: "Market Sentiment", desc: "Track discussions, sentiment trends, and market mood across socials, news, and media." },
];

export default function PlatformPreview() {
    const { ref, inView } = useScrollReveal();

    return (
        <section style={{ padding: "100px 48px", background: L.bg0, fontFamily: L.font }}>
            <div style={{ maxWidth: 1100, margin: "0 auto" }}>
                <motion.div
                    ref={ref}
                    initial={{ opacity: 0, y: 24 }}
                    animate={inView ? { opacity: 1, y: 0 } : {}}
                    transition={{ duration: 0.6 }}
                    style={{ marginBottom: 56 }}
                >
                    <div style={{
                        fontSize: 11, fontWeight: 700, letterSpacing: "0.1em",
                        textTransform: "uppercase", color: L.ink3, marginBottom: 12,
                    }}>
                        What AltInvest Tracks
                    </div>
                    <h2 style={{
                        fontSize: "clamp(30px, 3.5vw, 44px)", fontWeight: 800,
                        letterSpacing: "-1.2px", color: L.ink, maxWidth: 500, lineHeight: 1.1,
                    }}>
                        Every edge,<br />engineered.
                    </h2>
                </motion.div>

                <div style={{
                    display: "grid", gridTemplateColumns: "repeat(3,1fr)",
                    gap: 2, border: `1px solid ${L.border}`,
                    borderRadius: 16, overflow: "hidden",
                }}>
                    {CAPABILITIES.map((c, i) => (
                        <motion.div
                            key={c.title}
                            initial={{ opacity: 0 }}
                            animate={inView ? { opacity: 1 } : {}}
                            transition={{ delay: 0.1 + i * 0.07, duration: 0.55 }}
                            whileHover={{ background: L.bg3 }}
                            style={{
                                background: L.bg2, padding: "28px 28px",
                                borderRight: (i % 3 !== 2) ? `1px solid ${L.border}` : "none",
                                borderBottom: i < 3 ? `1px solid ${L.border}` : "none",
                                transition: "background 0.2s",
                            }}
                        >
                            <div style={{ fontSize: 20, marginBottom: 12, color: L.ink }}>{c.icon}</div>
                            <div style={{ fontSize: 14.5, fontWeight: 700, color: L.ink, marginBottom: 8 }}>{c.title}</div>
                            <div style={{ fontSize: 12.5, color: L.ink2, lineHeight: 1.65 }}>{c.desc}</div>
                        </motion.div>
                    ))}
                </div>
            </div>
        </section>
    );
}