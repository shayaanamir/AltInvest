import { useState } from "react";
import { motion } from "framer-motion";
import { L } from "../../components/landingPage/landingTokens";
import { IconCheck2 } from "../../components/icons";

const MARKETS = [
    {
        key: "crypto",
        icon: "◎",
        title: "Crypto",
        desc: "Layer 1s, DeFi, and major tokens",
        visual: (
            <svg width="100%" height="36" viewBox="0 0 120 36" preserveAspectRatio="none">
                <path d="M0,28 C15,26 25,18 40,20 C55,22 65,30 80,24 C95,18 105,12 120,8"
                    fill="none" stroke={`rgba(91,110,245,0.7)`} strokeWidth="2" strokeLinecap="round" />
            </svg>
        ),
    },
    {
        key: "nfts",
        icon: "◈",
        title: "NFTs",
        desc: "Blue-chip collections and gaming",
        visual: (
            <div style={{ display: "flex", gap: 6, alignItems: "flex-end" }}>
                <div style={{ width: 36, height: 36, borderRadius: 6, background: "linear-gradient(135deg,#c06ef5,#7c3aed)" }} />
                <div style={{ width: 36, height: 36, borderRadius: 6, background: "linear-gradient(135deg,#3b82f6,#1d4ed8)" }} />
                <div style={{ width: 36, height: 36, borderRadius: 6, background: "linear-gradient(135deg,#10b981,#065f46)" }} />
            </div>
        ),
    },
    {
        key: "commodities",
        icon: "⬡",
        title: "Commodities",
        desc: "Metals, energy, and agriculture",
        visual: (
            <div style={{ display: "flex", gap: 4, alignItems: "flex-end", height: 36 }}>
                {[22, 32, 26, 38, 28, 36, 30].map((h, i) => (
                    <div key={i} style={{
                        width: 10, height: h, borderRadius: 3,
                        background: `rgba(245,183,49,${0.4 + i * 0.08})`,
                    }} />
                ))}
            </div>
        ),
    },
    {
        key: "tokenized",
        icon: "⊕",
        title: "Tokenized Assets",
        desc: "Real-world assets and private credit",
        visual: (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
                <div style={{
                    width: 28, height: 28, borderRadius: "50%",
                    background: `linear-gradient(135deg, ${L.blue}, ${L.purple})`,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    boxShadow: `0 0 12px rgba(91,110,245,0.4)`,
                }}>
                    <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#fff", opacity: 0.9 }} />
                </div>
            </div>
        ),
    },
];

export default function Step1Markets({ answers, setAnswer }) {
    const selected = answers.markets || [];

    const toggle = (key) => {
        const next = selected.includes(key)
            ? selected.filter(k => k !== key)
            : [...selected, key];
        setAnswer("markets", next);
    };

    return (
        <div style={{
            flex: 1, display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center",
            padding: "40px 48px",
            fontFamily: "'DM Sans', 'Segoe UI', sans-serif",
        }}>
            <motion.h1
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
                style={{ fontSize: "clamp(28px,4vw,44px)", fontWeight: 800, color: L.ink, margin: "0 0 12px", textAlign: "center", letterSpacing: "-1px" }}
            >
                What markets are you interested in?
            </motion.h1>
            <motion.p
                initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.08, duration: 0.5 }}
                style={{ fontSize: 15, color: L.ink2, margin: "0 0 40px", textAlign: "center" }}
            >
                Select all that apply. We'll personalize your intelligence feed.
            </motion.p>

            <div style={{
                display: "grid", gridTemplateColumns: "repeat(4, 1fr)",
                gap: 12, width: "100%", maxWidth: 780,
            }}>
                {MARKETS.map((m, i) => {
                    const active = selected.includes(m.key);
                    return (
                        <motion.div
                            key={m.key}
                            initial={{ opacity: 0, y: 24 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.1 + i * 0.07, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                            onClick={() => toggle(m.key)}
                            style={{
                                background: active ? "rgba(91,110,245,0.12)" : "rgba(255,255,255,0.04)",
                                border: `1px solid ${active ? "rgba(91,110,245,0.5)" : "rgba(255,255,255,0.09)"}`,
                                borderRadius: 14,
                                padding: "20px 18px 16px",
                                cursor: "pointer",
                                transition: "all 0.2s",
                                position: "relative",
                                boxShadow: active ? `0 0 0 1px rgba(91,110,245,0.3), 0 8px 24px rgba(91,110,245,0.15)` : "none",
                            }}
                        >
                            {/* Selected indicator */}
                            {active && (
                                <div style={{
                                    position: "absolute", top: 12, right: 12,
                                    width: 18, height: 18, borderRadius: "50%",
                                    background: L.blue,
                                    display: "flex", alignItems: "center", justifyContent: "center",
                                }}>
                                    <IconCheck2 size={12} style={{ color: "#fff" }} />
                                </div>
                            )}

                            <div style={{ fontSize: 20, marginBottom: 10, color: active ? L.blue : L.ink2 }}>{m.icon}</div>
                            <div style={{ fontSize: 14, fontWeight: 700, color: L.ink, marginBottom: 4 }}>{m.title}</div>
                            <div style={{ fontSize: 11.5, color: L.ink2, lineHeight: 1.5, marginBottom: 16 }}>{m.desc}</div>
                            <div>{m.visual}</div>
                        </motion.div>
                    );
                })}
            </div>
        </div>
    );
}