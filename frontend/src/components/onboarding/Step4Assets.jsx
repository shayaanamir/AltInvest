import { useState } from "react";
import { motion } from "framer-motion";
import { L } from "../landingPage/landingTokens";
import { IconCheck2 } from "../icons";
import { useAsync } from "../../hooks/useAsync";
import { fetchUniverse } from "../../services/assetRepository";
import { formatPct } from "../../utils/formatters";
import { ErrorState } from "../../errors";

// Draws a sparkline path from real price points (scaled into the 42x16 box).
function sparkPath(values) {
    if (!values || values.length < 2) return "";
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min || 1;
    return values
        .map((v, i) => `${i === 0 ? "M" : "L"}${((i / (values.length - 1)) * 42).toFixed(1)},${(15 - ((v - min) / span) * 14).toFixed(1)}`)
        .join(" ");
}

function Spark({ values, pos }) {
    const path = sparkPath(values);
    if (!path) return <div style={{ width: 42, height: 16 }} />;
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

    // The crypto assets the platform covers, best AAI score first, with their real 24h move and price trail.
    const { data: universe, loading, error, refetch } = useAsync(
        () => fetchUniverse({ category: "crypto", sort: "aai_score", order: "desc" }),
        []
    );
    const assets = (universe || []).map((a) => ({
        sym: a.symbol,
        name: a.name,
        chg: formatPct(a.changePct ?? 0, { withSign: true }),
        pos: (a.changePct ?? 0) >= 0,
        aiPick: a.signal === "BUY", // the platform's own BUY read
        spark: a.sparkline,
    }));

    const toggle = (sym) => {
        const next = selected.includes(sym)
            ? selected.filter(s => s !== sym)
            : [...selected, sym];
        setAnswer("assets", next);
    };

    const filtered = assets.filter(a =>
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
                    <span style={{ fontSize: 11, fontWeight: 600, color: L.ink3, textTransform: "uppercase", letterSpacing: "0.07em" }}>Covered assets</span>
                    <span style={{ fontSize: 11, color: L.ink2 }}>{selected.length} asset{selected.length !== 1 ? "s" : ""} selected</span>
                </div>

                {error ? (
                    <ErrorState error={error} onRetry={refetch} title="Couldn't load assets" />
                ) : loading ? (
                    <div style={{ fontSize: 12, color: L.ink3 }}>Loading assets…</div>
                ) : filtered.length === 0 ? (
                    <div style={{ fontSize: 12, color: L.ink3 }}>{query ? "No assets match your search." : "No assets are covered yet."}</div>
                ) : null}

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
                                        <Spark values={a.spark} pos={a.pos} />
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