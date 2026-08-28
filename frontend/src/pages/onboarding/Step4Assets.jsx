import { useState } from "react";
import { motion } from "framer-motion";
import { L } from "../../components/landingPage/landingTokens";
import { IconCheck2 } from "../../components/icons";

const ALL_ASSETS = [
    { sym: "BTC", name: "Bitcoin", chg: "+2.4%", pos: true, aiPick: true, spark: "M0,12 C5,10 10,6 15,4 C20,2 25,8 30,6 C35,4 38,2 42,1" },
    { sym: "ETH", name: "Ethereum", chg: "+1.8%", pos: true, aiPick: true, spark: "M0,10 C5,8 10,5 15,5 C20,5 25,9 30,7 C35,5 38,4 42,2" },
    { sym: "SOL", name: "Solana", chg: "-0.5%", pos: false, aiPick: false, spark: "M0,4 C5,6 10,8 15,10 C20,12 25,10 30,12 C35,13 38,13 42,14" },
    { sym: "GOLD", name: "Gold", chg: "+0.2%", pos: true, aiPick: false, spark: "M0,10 C5,9 10,8 15,8 C20,8 25,7 30,7 C35,6 38,6 42,5" },
    { sym: "SILVER", name: "Silver", chg: "-1.1%", pos: false, aiPick: false, spark: "M0,6 C5,8 10,10 15,11 C20,12 25,10 30,12 C35,13 38,13 42,14" },
    { sym: "ETH-NFT", name: "NFT Index", chg: "+5.4%", pos: true, aiPick: true, spark: "M0,14 C5,12 10,9 15,7 C20,5 25,4 30,3 C35,2 38,1 42,0" },
    { sym: "RWA-TKN", name: "Real World Assets", chg: "+0.9%", pos: true, aiPick: true, spark: "M0,10 C5,9 10,7 15,7 C20,7 25,6 30,5 C35,4 38,4 42,3" },
    { sym: "COPPER", name: "Copper", chg: "+1.2%", pos: true, aiPick: false, spark: "M0,12 C5,10 10,8 15,7 C20,6 25,5 30,5 C35,4 38,3 42,3" },
    { sym: "OIL", name: "Crude Oil", chg: "-2.3%", pos: false, aiPick: false, spark: "M0,4 C5,6 10,9 15,11 C20,13 25,12 30,13 C35,14 38,14 42,15" },
    { sym: "PLAT", name: "Platinum", chg: "+0.4%", pos: true, aiPick: false, spark: "M0,10 C5,9 10,8 15,8 C20,7 25,7 30,6 C35,6 38,5 42,5" },
];

function Spark({ path, pos }) {
    return (
        <svg width="42" height="16" viewBox="0 0 42 16" preserveAspectRatio="none">
            <path d={path} fill="none"
                stroke={pos ? L.green : L.red}
                strokeWidth="1.8" strokeLinecap="round" />
        </svg>
    );
}

export default function Step4Assets({ answers, setAnswer }) {
    const [query, setQuery] = useState("");
    const selected = answers.assets || [];

    const toggle = (sym) => {
        const next = selected.includes(sym)
            ? selected.filter(s => s !== sym)
            : [...selected, sym];
        setAnswer("assets", next);
    };

    const filtered = ALL_ASSETS.filter(a =>
        a.sym.toLowerCase().includes(query.toLowerCase()) ||
        a.name.toLowerCase().includes(query.toLowerCase())
    );

    return (
        <div style={{
            flex: 1, display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "flex-start",
            padding: "44px 48px 24px",
            fontFamily: "'DM Sans', 'Segoe UI', sans-serif",
        }}>
            <motion.h1
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.55 }}
                style={{ fontSize: "clamp(26px,3.5vw,40px)", fontWeight: 800, color: L.ink, margin: "0 0 10px", textAlign: "center", letterSpacing: "-1px" }}
            >
                Build your intelligence feed.
            </motion.h1>
            <motion.p
                initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.08, duration: 0.5 }}
                style={{ fontSize: 14.5, color: L.ink2, margin: "0 0 28px", textAlign: "center" }}
            >
                Add assets to track. AI will surface signals on what matters.
            </motion.p>

            {/* Search */}
            <motion.div
                initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.14, duration: 0.5 }}
                style={{ width: "100%", maxWidth: 560, marginBottom: 18, position: "relative" }}
            >
                <span style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)", color: L.ink3, fontSize: 14 }}>⌕</span>
                <input
                    type="text"
                    placeholder="Search assets..."
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    style={{
                        width: "100%", boxSizing: "border-box",
                        background: "rgba(255,255,255,0.04)",
                        border: "1px solid rgba(255,255,255,0.1)",
                        borderRadius: 10, padding: "11px 14px 11px 38px",
                        fontSize: 13.5, color: L.ink, outline: "none", fontFamily: "inherit",
                        transition: "border-color 0.2s",
                    }}
                    onFocus={e => e.target.style.borderColor = "rgba(91,110,245,0.5)"}
                    onBlur={e => e.target.style.borderColor = "rgba(255,255,255,0.1)"}
                />
            </motion.div>

            {/* Grid */}
            <motion.div
                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                transition={{ delay: 0.2, duration: 0.5 }}
                style={{ width: "100%", maxWidth: 560 }}
            >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                    <span style={{ fontSize: 11, fontWeight: 600, color: L.ink3, textTransform: "uppercase", letterSpacing: "0.07em" }}>Trending Assets</span>
                    <span style={{ fontSize: 11, color: L.ink2 }}>{selected.length} asset{selected.length !== 1 ? "s" : ""} selected</span>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
                    {filtered.map((a, i) => {
                        const active = selected.includes(a.sym);
                        return (
                            <motion.div
                                key={a.sym}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.03, duration: 0.35 }}
                                onClick={() => toggle(a.sym)}
                                style={{
                                    background: active ? "rgba(91,110,245,0.1)" : "rgba(255,255,255,0.04)",
                                    border: `1px solid ${active ? "rgba(91,110,245,0.4)" : "rgba(255,255,255,0.08)"}`,
                                    borderRadius: 10, padding: "11px 12px",
                                    cursor: "pointer", display: "flex", alignItems: "center",
                                    justifyContent: "space-between", gap: 8,
                                    transition: "all 0.18s",
                                }}
                            >
                                <div style={{ minWidth: 0 }}>
                                    <div style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: 2 }}>
                                        <span style={{ fontSize: 12, fontWeight: 700, color: L.ink }}>{a.sym}</span>
                                        {a.aiPick && (
                                            <span style={{
                                                fontSize: 8, fontWeight: 700, padding: "1px 5px", borderRadius: 4,
                                                background: "rgba(91,110,245,0.2)", color: L.blue,
                                                border: "1px solid rgba(91,110,245,0.3)", letterSpacing: "0.03em",
                                            }}>AI Pick</span>
                                        )}
                                    </div>
                                    <div style={{ fontSize: 10, color: L.ink3 }}>{a.name}</div>
                                </div>
                                <div style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
                                    <div>
                                        <Spark path={a.spark} pos={a.pos} />
                                        <div style={{ fontSize: 10, fontWeight: 600, color: a.pos ? L.green : L.red, textAlign: "right" }}>{a.chg}</div>
                                    </div>
                                    <div style={{
                                        width: 20, height: 20, borderRadius: "50%", flexShrink: 0,
                                        background: active ? L.blue : "rgba(255,255,255,0.08)",
                                        border: `1px solid ${active ? L.blue : "rgba(255,255,255,0.15)"}`,
                                        display: "flex", alignItems: "center", justifyContent: "center",
                                        fontSize: 11, color: active ? "#fff" : L.ink3,
                                        transition: "all 0.18s",
                                    }}>
                                        {active ? <IconCheck2 size={13} style={{ color: "#fff" }} /> : "+"}
                                    </div>
                                </div>
                            </motion.div>
                        );
                    })}
                </div>
            </motion.div>
        </div>
    );
}