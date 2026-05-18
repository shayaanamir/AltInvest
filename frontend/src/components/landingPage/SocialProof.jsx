import { motion } from "framer-motion";
import { L } from "./landingTokens";
import { useScrollReveal } from "./landingAnimations";

const FIRMS = ["NEXUS", "MERIDIAN", "ASCEND CAPITAL", "ORBIT", "HELIX", "NORTHWIND"];

export default function SocialProof() {
    const { ref, inView } = useScrollReveal();

    return (
        <motion.section
            ref={ref}
            initial={{ opacity: 0 }}
            animate={inView ? { opacity: 1 } : {}}
            transition={{ duration: 0.6 }}
            style={{
                borderTop: `1px solid ${L.border}`,
                borderBottom: `1px solid ${L.border}`,
                padding: "32px 48px",
                textAlign: "center",
                background: L.bg1,
                fontFamily: L.font,
            }}
        >
            <p style={{
                fontSize: 11, fontWeight: 600, color: L.ink3,
                textTransform: "uppercase", letterSpacing: "0.12em", marginBottom: 20,
            }}>
                Trusted by leading allocators · $2.4B+ tracked
            </p>
            <div style={{
                display: "flex", alignItems: "center",
                justifyContent: "center", gap: 48, flexWrap: "wrap",
            }}>
                {FIRMS.map((f, i) => (
                    <motion.span
                        key={f}
                        initial={{ opacity: 0, y: 10 }}
                        animate={inView ? { opacity: 1, y: 0 } : {}}
                        transition={{ delay: i * 0.07, duration: 0.5 }}
                        style={{
                            fontSize: 14, fontWeight: 700, color: L.ink3,
                            letterSpacing: "0.1em", cursor: "default",
                            transition: "color 0.2s",
                        }}
                        onMouseEnter={e => e.currentTarget.style.color = L.ink2}
                        onMouseLeave={e => e.currentTarget.style.color = L.ink3}
                    >
                        {f}
                    </motion.span>
                ))}
            </div>
        </motion.section>
    );
}