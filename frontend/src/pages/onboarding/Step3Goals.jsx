import { useState } from "react";
import { motion } from "framer-motion";
import { L } from "../../components/landingPage/landingTokens";

const GOALS = [
    { key: "longterm", icon: "↗", title: "Long-term investing", desc: "Build wealth steadily over years" },
    { key: "trading", icon: "", title: "Active trading", desc: "Capitalize on short-term movements" },
    { key: "research", icon: "⌕", title: "Deep research", desc: "Analyze fundamentals and on-chain data" },
    { key: "discovery", icon: "◎", title: "Market discovery", desc: "Find new narratives and early trends" },
    { key: "portfolio", icon: "⊞", title: "Portfolio optimization", desc: "Balance risk across multiple assets" },
];

export default function Step3Goals({ answers, setAnswer }) {
    const selected = answers.goals || [];

    const toggle = (key) => {
        const next = selected.includes(key)
            ? selected.filter(k => k !== key)
            : [...selected, key];
        setAnswer("goals", next);
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
                transition={{ duration: 0.55 }}
                style={{ fontSize: "clamp(28px,4vw,44px)", fontWeight: 800, color: L.ink, margin: "0 0 12px", textAlign: "center", letterSpacing: "-1px" }}
            >
                What are you here for?
            </motion.h1>
            <motion.p
                initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.08, duration: 0.5 }}
                style={{ fontSize: 15, color: L.ink2, margin: "0 0 40px", textAlign: "center" }}
            >
                Choose what matters most. You can change this anytime.
            </motion.p>

            <div style={{ width: "100%", maxWidth: 640 }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginBottom: 10 }}>
                    {GOALS.slice(0, 3).map((g, i) => <GoalCard key={g.key} g={g} i={i} selected={selected} toggle={toggle} />)}
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                    {GOALS.slice(3).map((g, i) => <GoalCard key={g.key} g={g} i={i + 3} selected={selected} toggle={toggle} />)}
                </div>
            </div>
        </div>
    );
}

function GoalCard({ g, i, selected, toggle }) {
    const active = selected.includes(g.key);
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + i * 0.06, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            onClick={() => toggle(g.key)}
            style={{
                background: active ? "color-mix(in srgb, var(--sv2-accent) 10%, transparent)" : "var(--sv2-card-alt)",
                border: `1px solid ${active ? "color-mix(in srgb, var(--sv2-accent) 45%, transparent)" : "var(--sv2-border)"}`,
                borderRadius: 12, padding: "16px 16px",
                cursor: "pointer", display: "flex", alignItems: "flex-start", gap: 12,
                transition: "all 0.2s",
                boxShadow: active ? "0 0 0 1px color-mix(in srgb, var(--sv2-accent) 25%, transparent), 0 4px 16px color-mix(in srgb, var(--sv2-accent) 12%, transparent)" : "none",
            }}
        >
            <div style={{
                width: 34, height: 34, borderRadius: 8, flexShrink: 0,
                background: active ? "color-mix(in srgb, var(--sv2-accent) 20%, transparent)" : "var(--sv2-chip)",
                border: `1px solid ${active ? "color-mix(in srgb, var(--sv2-accent) 30%, transparent)" : "var(--sv2-border)"}`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 15, color: active ? L.blue : L.ink2,
                transition: "all 0.2s",
            }}>
                {g.icon}
            </div>
            <div>
                <div style={{ fontSize: 13.5, fontWeight: 700, color: L.ink, marginBottom: 3 }}>{g.title}</div>
                <div style={{ fontSize: 11.5, color: L.ink2, lineHeight: 1.45 }}>{g.desc}</div>
            </div>
        </motion.div>
    );
}