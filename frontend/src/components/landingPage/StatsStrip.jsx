import { motion } from "framer-motion";
import { L } from "./landingTokens";
import { useScrollReveal } from "./landingAnimations";

const STATS = [
    { val: "$2.4B+", label: "AUM tracked" },
    { val: "94.2%", label: "Signal accuracy" },
    { val: "40M+", label: "Daily signals" },
    { val: "12K+", label: "Active allocators" },
    { val: "0.3ms", label: "Latency" },
];

export default function StatsStrip() {
    const { ref, inView } = useScrollReveal();

    return (
        <section style={{
            borderTop: `1px solid ${L.border}`,
            borderBottom: `1px solid ${L.border}`,
            padding: "48px",
            background: L.bg1,
            fontFamily: L.font,
        }}>
            <div style={{
                display: "flex", justifyContent: "space-between", alignItems: "center",
                maxWidth: 1000, margin: "0 auto", gap: 32, flexWrap: "wrap",
            }}>
                {STATS.map((s, i) => (
                    <motion.div
                        key={s.val}
                        ref={ref}
                        initial={{ opacity: 0, y: 20 }}
                        animate={inView ? { opacity: 1, y: 0 } : {}}
                        transition={{ delay: i * 0.08, duration: 0.55 }}
                        style={{ textAlign: "center" }}
                    >
                        <div style={{ fontSize: 32, fontWeight: 800, letterSpacing: "-1px", color: L.ink }}>{s.val}</div>
                        <div style={{ fontSize: 12, color: L.ink3, marginTop: 3, fontWeight: 500 }}>{s.label}</div>
                    </motion.div>
                ))}
            </div>
        </section>
    );
}