import { motion } from "framer-motion";
import { L } from "../../components/landingPage/landingTokens";
import { IconCheck2 } from "../../components/icons";

const LAYOUTS = [
    {
        key: "minimal",
        title: "Minimal",
        desc: "Clean focus on core metrics",
        preview: (
            <div style={{ display: "flex", flexDirection: "column", gap: 6, height: "100%" }}>
                <div style={{ height: "45%", background: "rgba(255,255,255,0.07)", borderRadius: 5 }} />
                <div style={{ display: "flex", gap: 6, flex: 1 }}>
                    <div style={{ flex: 1, background: "rgba(255,255,255,0.05)", borderRadius: 5 }} />
                    <div style={{ flex: 1, background: "rgba(255,255,255,0.05)", borderRadius: 5 }} />
                </div>
            </div>
        ),
    },
    {
        key: "analyst",
        title: "Analyst",
        desc: "Dense data and multiple panels",
        preview: (
            <div style={{ display: "flex", gap: 6, height: "100%" }}>
                <div style={{ width: "35%", display: "flex", flexDirection: "column", gap: 6 }}>
                    <div style={{ flex: 1, background: "rgba(255,255,255,0.07)", borderRadius: 5 }} />
                    <div style={{ flex: 1, background: "rgba(255,255,255,0.05)", borderRadius: 5 }} />
                    <div style={{ flex: 1, background: "rgba(255,255,255,0.05)", borderRadius: 5 }} />
                </div>
                <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
                    <div style={{ flex: 2, background: "rgba(255,255,255,0.07)", borderRadius: 5 }} />
                    <div style={{ flex: 1, background: "rgba(255,255,255,0.05)", borderRadius: 5 }} />
                </div>
            </div>
        ),
    },
    {
        key: "trader",
        title: "Trader",
        desc: "Order books and fast execution",
        preview: (
            <div style={{ display: "flex", flexDirection: "column", gap: 6, height: "100%" }}>
                <div style={{ flex: 2, background: "rgba(255,255,255,0.07)", borderRadius: 5 }} />
                <div style={{ display: "flex", gap: 6, flex: 1 }}>
                    <div style={{ flex: 1, background: "rgba(232,48,74,0.25)", borderRadius: 5 }} />
                    <div style={{ flex: 1, background: "rgba(0,212,139,0.2)", borderRadius: 5 }} />
                </div>
            </div>
        ),
    },
    {
        key: "ai-first",
        title: "AI-First",
        desc: "Signal-driven intelligence feed",
        preview: (
            <div style={{ display: "flex", gap: 6, height: "100%" }}>
                <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
                    <div style={{ flex: 1, background: "rgba(91,110,245,0.2)", borderRadius: 5 }} />
                    <div style={{ flex: 1, background: "rgba(255,255,255,0.06)", borderRadius: 5 }} />
                </div>
                <div style={{ width: "40%", display: "flex", flexDirection: "column", gap: 6 }}>
                    <div style={{ flex: 2, background: "rgba(91,110,245,0.15)", borderRadius: 5, position: "relative", overflow: "hidden" }}>
                        <div style={{
                            position: "absolute", top: 8, left: 10,
                            width: 8, height: 8, borderRadius: "50%",
                            background: L.blue, boxShadow: `0 0 8px ${L.blue}`,
                        }} />
                    </div>
                    <div style={{ flex: 1, background: "rgba(255,255,255,0.06)", borderRadius: 5 }} />
                    <div style={{ flex: 1, background: "rgba(255,255,255,0.06)", borderRadius: 5 }} />
                </div>
            </div>
        ),
        default: true,
    },
];

export default function Step5Layout({ answers, setAnswer }) {
    const selected = answers.layout || "ai-first";

    return (
        <div style={{
            flex: 1, display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center",
            padding: "40px 48px",
            fontFamily: "'DM Sans', 'Segoe UI', sans-serif",
        }}>
            <motion.h1
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.55 }}
                style={{ fontSize: "clamp(26px,3.5vw,40px)", fontWeight: 800, color: L.ink, margin: "0 0 10px", textAlign: "center", letterSpacing: "-1px" }}
            >
                How should AltInvest work for you?
            </motion.h1>
            <motion.p
                initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.08, duration: 0.5 }}
                style={{ fontSize: 14.5, color: L.ink2, margin: "0 0 36px", textAlign: "center" }}
            >
                Choose a layout. You can switch anytime.
            </motion.p>

            <div style={{
                display: "grid", gridTemplateColumns: "1fr 1fr",
                gap: 12, width: "100%", maxWidth: 620,
            }}>
                {LAYOUTS.map((layout, i) => {
                    const active = selected === layout.key;
                    return (
                        <motion.div
                            key={layout.key}
                            initial={{ opacity: 0, y: 24 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.1 + i * 0.07, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                            onClick={() => setAnswer("layout", layout.key)}
                            style={{
                                background: active ? "rgba(91,110,245,0.1)" : "rgba(255,255,255,0.03)",
                                border: `1px solid ${active ? "rgba(91,110,245,0.45)" : "rgba(255,255,255,0.08)"}`,
                                borderRadius: 14, padding: "16px",
                                cursor: "pointer", transition: "all 0.2s",
                                boxShadow: active ? `0 0 0 1px rgba(91,110,245,0.25), 0 8px 24px rgba(91,110,245,0.15)` : "none",
                                position: "relative",
                            }}
                        >
                            {/* Preview box */}
                            <div style={{
                                height: 140,
                                background: "rgba(8,9,18,0.7)",
                                borderRadius: 8, padding: 10, marginBottom: 12,
                                border: "1px solid rgba(255,255,255,0.06)",
                            }}>
                                {layout.preview}
                            </div>

                            {/* Label row */}
                            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                                <div>
                                    <div style={{ fontSize: 13.5, fontWeight: 700, color: L.ink }}>{layout.title}</div>
                                    <div style={{ fontSize: 11.5, color: L.ink3, marginTop: 2 }}>{layout.desc}</div>
                                </div>
                                <div style={{
                                    width: 20, height: 20, borderRadius: "50%", flexShrink: 0,
                                    background: active ? L.blue : "rgba(255,255,255,0.08)",
                                    border: `1px solid ${active ? L.blue : "rgba(255,255,255,0.15)"}`,
                                    display: "flex", alignItems: "center", justifyContent: "center",
                                    fontSize: 10, color: "#fff",
                                    transition: "all 0.2s",
                                }}>
                                    {active && <IconCheck2 size={13} style={{ color: "#fff" }} />}
                                </div>
                            </div>
                        </motion.div>
                    );
                })}
            </div>
        </div>
    );
}