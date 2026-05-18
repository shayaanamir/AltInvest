import { L } from "./landingTokens";
import { motion } from "framer-motion";

const PREDICTIONS = [
    { name: "Private Equity Alpha", conf: "94%", action: "BUY", color: L.green },
    { name: "Real Estate Trust", conf: "88%", action: "HOLD", color: L.amber },
    { name: "Venture Tech Q3", conf: "91%", action: "SELL", color: L.red },
    { name: "Infrastructure Debt", conf: "85%", action: "BUY", color: L.green },
];

const chartPoints = "M0,160 C40,155 80,140 120,100 C160,60 180,80 220,65 C260,50 280,72 320,55 C360,38 380,30 420,20";
const chartArea = chartPoints + " L420,200 L0,200 Z";

export default function DashboardMockup() {
    return (
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

            <div style={{
                background: L.bg1,
                border: `1px solid ${L.border2}`,
                borderRadius: 16,
                overflow: "hidden",
                width: "100%",
                boxShadow: "0 40px 120px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.05)",
            }}>
                {/* Window chrome */}
                <div style={{
                    background: "rgba(255,255,255,0.03)",
                    borderBottom: `1px solid ${L.border}`,
                    padding: "10px 16px",
                    display: "flex", alignItems: "center", gap: 12,
                }}>
                    <div style={{ display: "flex", gap: 6 }}>
                        {["#ff5f57", "#ffbd2e", "#28ca41"].map(c => (
                            <div key={c} style={{ width: 10, height: 10, borderRadius: "50%", background: c }} />
                        ))}
                    </div>
                    <div style={{
                        flex: 1, maxWidth: 260,
                        background: L.bg2,
                        border: `1px solid ${L.border}`,
                        borderRadius: 6, padding: "4px 10px",
                        display: "flex", alignItems: "center", gap: 7,
                        margin: "0 auto",
                    }}>
                        <span style={{ fontSize: 11, color: L.ink3 }}>⌕</span>
                        <span style={{ fontSize: 11, color: L.ink3 }}>Search assets, signals...</span>
                    </div>
                    <div style={{ marginLeft: "auto", display: "flex", gap: 8, alignItems: "center" }}>
                        <div style={{ fontSize: 14, color: L.ink2 }}>🔔</div>
                        <div style={{ width: 28, height: 28, borderRadius: "50%", background: `linear-gradient(135deg, ${L.blue}, ${L.purple})` }} />
                    </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "200px 1fr", minHeight: 420 }}>
                    {/* Sidebar */}
                    <div style={{ background: L.bg2, borderRight: `1px solid ${L.border}`, padding: "20px 0" }}>
                        {[
                            { icon: "↗", label: "Overview", active: true },
                            { icon: "◎", label: "AI Signals" },
                            { icon: "〜", label: "Markets" },
                            { icon: "▦", label: "Portfolio" },
                        ].map(item => (
                            <div key={item.label} style={{
                                display: "flex", alignItems: "center", gap: 10,
                                padding: "10px 20px", cursor: "pointer",
                                background: item.active ? "rgba(91,110,245,0.15)" : "transparent",
                                borderLeft: item.active ? `2px solid ${L.blue}` : "2px solid transparent",
                            }}>
                                <span style={{ fontSize: 14, color: item.active ? L.blue : L.ink3 }}>{item.icon}</span>
                                <span style={{ fontSize: 13, fontWeight: item.active ? 600 : 400, color: item.active ? L.ink : L.ink2 }}>
                                    {item.label}
                                </span>
                            </div>
                        ))}
                    </div>

                    {/* Main content */}
                    <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
                        {/* Stat cards */}
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 10 }}>
                            {[
                                { label: "Total AUM Tracked", val: "$1.24B", chg: "+2.4%", col: L.green },
                                { label: "Active Signals", val: "1,247", chg: "+12", col: L.blue },
                                { label: "Prediction Accuracy", val: "94.2%", chg: "+0.8%", col: L.purple },
                            ].map(s => (
                                <div key={s.label} style={{
                                    background: L.bg3, border: `1px solid ${L.border}`,
                                    borderRadius: 10, padding: "14px 16px",
                                }}>
                                    <div style={{ fontSize: 10, color: L.ink3, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>
                                        {s.label}
                                    </div>
                                    <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                                        <span style={{ fontSize: 22, fontWeight: 700, color: L.ink, letterSpacing: "-0.5px" }}>{s.val}</span>
                                        <span style={{ fontSize: 11, fontWeight: 600, color: s.col }}>{s.chg}</span>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Chart + predictions */}
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 260px", gap: 10, flex: 1 }}>
                            {/* Chart */}
                            <div style={{
                                background: L.bg3, border: `1px solid ${L.border}`,
                                borderRadius: 10, padding: "14px 16px", overflow: "hidden",
                            }}>
                                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
                                    <span style={{ fontSize: 12.5, fontWeight: 600, color: L.ink }}>Market Sentiment Index</span>
                                    <div style={{ display: "flex", gap: 4 }}>
                                        {["1D", "1W", "1M", "YTD"].map((t, i) => (
                                            <button key={t} style={{
                                                background: i === 2 ? L.blue : "none",
                                                border: "none", borderRadius: 5,
                                                padding: "3px 8px", fontSize: 10, fontWeight: 600,
                                                color: i === 2 ? "#fff" : L.ink3,
                                                cursor: "pointer", fontFamily: "inherit",
                                            }}>{t}</button>
                                        ))}
                                    </div>
                                </div>
                                <svg width="100%" height="160" viewBox="0 0 420 200" preserveAspectRatio="none">
                                    <defs>
                                        <linearGradient id="dmcg" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="0%" stopColor={L.blue} stopOpacity="0.35" />
                                            <stop offset="100%" stopColor={L.blue} stopOpacity="0" />
                                        </linearGradient>
                                    </defs>
                                    <path d={chartArea} fill="url(#dmcg)" />
                                    <path d={chartPoints} fill="none" stroke={L.blue} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                                    <circle cx="220" cy="65" r="5" fill={L.blue} stroke={L.bg3} strokeWidth="2" />
                                    <rect x="170" y="40" width="80" height="22" rx="5" fill="rgba(0,0,0,0.75)" stroke={L.border2} />
                                    <text x="210" y="55" textAnchor="middle" fontSize="9" fill={L.ink} fontFamily="inherit">Buy Signal</text>
                                </svg>
                            </div>

                            {/* Live predictions */}
                            <div style={{
                                background: L.bg3, border: `1px solid ${L.border}`,
                                borderRadius: 10, padding: "14px 16px",
                            }}>
                                <div style={{ fontSize: 12.5, fontWeight: 600, color: L.ink, marginBottom: 12 }}>Live Predictions</div>
                                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                                    {PREDICTIONS.map(p => (
                                        <div key={p.name} style={{
                                            display: "flex", alignItems: "center", justifyContent: "space-between",
                                            background: L.bg4, borderRadius: 8, padding: "10px 12px",
                                        }}>
                                            <div>
                                                <div style={{ fontSize: 11.5, fontWeight: 600, color: L.ink }}>{p.name}</div>
                                                <div style={{ fontSize: 10, color: L.ink3, marginTop: 2 }}>Confidence: {p.conf}</div>
                                            </div>
                                            <span style={{
                                                fontSize: 9, fontWeight: 800, padding: "3px 8px", borderRadius: 5,
                                                background: `${p.color}22`, color: p.color,
                                                border: `1px solid ${p.color}44`,
                                                letterSpacing: "0.05em",
                                            }}>{p.action}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </motion.div>
    );
}