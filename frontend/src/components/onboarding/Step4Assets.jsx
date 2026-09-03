import { useState } from "react";
import { motion } from "framer-motion";
import { L } from "../landingPage/landingTokens";
import { IconCheck2 } from "../icons";

const ALL_ASSETS = [
    // ── Crypto: Layer 1 ────────────────────────────────────────
    { sym: "BTC",   name: "Bitcoin",       chg: "+2.14%",  pos: true,  aiPick: true,  cat: "Layer 1",        spark: "M0,12 C5,10 10,6 15,4 C20,2 25,8 30,6 C35,4 38,2 42,1" },
    { sym: "ETH",   name: "Ethereum",      chg: "-0.85%",  pos: false, aiPick: true,  cat: "Layer 1",        spark: "M0,10 C5,8 10,5 15,5 C20,5 25,9 30,7 C35,5 38,4 42,2" },
    { sym: "SOL",   name: "Solana",        chg: "+1.83%",  pos: true,  aiPick: false, cat: "Layer 1",        spark: "M0,4 C5,6 10,8 15,10 C20,12 25,10 30,12 C35,13 38,13 42,14" },
    { sym: "ADA",   name: "Cardano",       chg: "+0.88%",  pos: true,  aiPick: false, cat: "Layer 1",        spark: "M0,10 C5,9 10,9 15,10 C20,10 25,9 30,9 C35,8 38,8 42,9" },
    { sym: "AVAX",  name: "Avalanche",     chg: "+2.70%",  pos: true,  aiPick: false, cat: "Layer 1",        spark: "M0,10 C5,8 10,7 15,6 C20,5 25,6 30,5 C35,4 38,3 42,3" },
    { sym: "NEAR",  name: "NEAR Protocol", chg: "+3.20%",  pos: true,  aiPick: false, cat: "Layer 1",        spark: "M0,12 C5,10 10,8 15,7 C20,6 25,5 30,4 C35,3 38,3 42,2" },
    // ── Crypto: Layer 2 / Infrastructure ──────────────────────────────
    { sym: "MATIC", name: "Polygon",       chg: "+1.40%",  pos: true,  aiPick: false, cat: "Layer 2",        spark: "M0,10 C5,9 10,9 15,9 C20,8 25,8 30,7 C35,7 38,7 42,7" },
    { sym: "ARB",   name: "Arbitrum",      chg: "+3.87%",  pos: true,  aiPick: false, cat: "Layer 2",        spark: "M0,10 C5,8 10,7 15,7 C20,6 25,6 30,5 C35,5 38,4 42,4" },
    { sym: "DOT",   name: "Polkadot",      chg: "-2.10%",  pos: false, aiPick: false, cat: "Layer 0",        spark: "M0,4 C5,6 10,8 15,10 C20,11 25,12 30,13 C35,13 38,14 42,14" },
    { sym: "LINK",  name: "Chainlink",     chg: "+1.10%",  pos: true,  aiPick: true,  cat: "Infrastructure", spark: "M0,8 C5,7 10,6 15,6 C20,5 25,6 30,5 C35,5 38,4 42,4" },
    { sym: "ATOM",  name: "Cosmos",        chg: "-1.80%",  pos: false, aiPick: false, cat: "Infrastructure", spark: "M0,5 C5,7 10,9 15,10 C20,11 25,10 30,11 C35,12 38,12 42,13" },
    // ── Crypto: Exchange / Payments ─────────────────────────────────────
    { sym: "BNB",   name: "BNB",           chg: "+1.55%",  pos: true,  aiPick: false, cat: "Exchange Token", spark: "M0,9 C5,8 10,7 15,7 C20,6 25,7 30,6 C35,6 38,5 42,5" },
    { sym: "XRP",   name: "XRP",           chg: "-1.20%",  pos: false, aiPick: false, cat: "Payments",       spark: "M0,6 C5,7 10,9 15,10 C20,10 25,11 30,10 C35,11 38,11 42,12" },
    { sym: "LTC",   name: "Litecoin",      chg: "+0.60%",  pos: true,  aiPick: false, cat: "Payments",       spark: "M0,10 C5,9 10,9 15,9 C20,8 25,8 30,8 C35,7 38,7 42,7" },
    // ── Crypto: DeFi / Community ───────────────────────────────────────────
    { sym: "UNI",   name: "Uniswap",       chg: "-4.06%",  pos: false, aiPick: false, cat: "DeFi",           spark: "M0,3 C5,5 10,7 15,9 C20,11 25,12 30,13 C35,14 38,14 42,15" },
    { sym: "DOGE",  name: "Dogecoin",      chg: "+11.62%", pos: true,  aiPick: true,  cat: "Meme/Community", spark: "M0,14 C5,12 10,9 15,7 C20,5 25,4 30,3 C35,2 38,1 42,0" },
    // ── Commodities ────────────────────────────────────────────────────────
    { sym: "GOLD",   name: "Gold",         chg: "+0.2%",   pos: true,  aiPick: false, cat: "Commodity",      spark: "M0,10 C5,9 10,8 15,8 C20,8 25,7 30,7 C35,6 38,6 42,5" },
    { sym: "SILVER", name: "Silver",       chg: "-1.1%",   pos: false, aiPick: false, cat: "Commodity",      spark: "M0,6 C5,8 10,10 15,11 C20,12 25,10 30,12 C35,13 38,13 42,14" },
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
                        background: "var(--sv2-card-alt)",
                        border: "1px solid var(--sv2-border)",
                        borderRadius: 10, padding: "11px 14px 11px 38px",
                        fontSize: 13.5, color: L.ink, outline: "none", fontFamily: "inherit",
                        transition: "border-color 0.2s",
                    }}
                    onFocus={e => e.target.style.borderColor = "color-mix(in srgb, var(--sv2-accent) 50%, transparent)"}
                    onBlur={e => e.target.style.borderColor = "var(--sv2-border)"}
                />
            </motion.div>

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
                                    background: active ? "color-mix(in srgb, var(--sv2-accent) 10%, transparent)" : "var(--sv2-card-alt)",
                                    border: `1px solid ${active ? "color-mix(in srgb, var(--sv2-accent) 40%, transparent)" : "var(--sv2-border)"}`,
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
                                                background: "color-mix(in srgb, var(--sv2-accent) 20%, transparent)", color: L.blue,
                                                border: "1px solid color-mix(in srgb, var(--sv2-accent) 30%, transparent)", letterSpacing: "0.03em",
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
                                        background: active ? L.blue : "var(--sv2-chip)",
                                        border: `1px solid ${active ? L.blue : "var(--sv2-border-strong)"}`,
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