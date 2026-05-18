import { motion } from "framer-motion";
import { L } from "../../components/landingPage/landingTokens";

function AlphaCard() {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
            style={{
                background: "rgba(20,18,35,0.95)",
                border: `1px solid rgba(155,109,255,0.2)`,
                borderRadius: 16,
                padding: "20px 20px 0",
                width: 200,
                overflow: "hidden",
                boxShadow: "0 24px 64px rgba(0,0,0,0.5)",
                position: "relative",
            }}
        >
            {/* Glow ring */}
            <svg width="120" height="120" viewBox="0 0 120 120" style={{ display: "block", margin: "0 auto 0" }}>
                <defs>
                    <linearGradient id="ringGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor={L.purple} />
                        <stop offset="100%" stopColor={L.blue} />
                    </linearGradient>
                    <filter id="glow">
                        <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                        <feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge>
                    </filter>
                </defs>
                {/* Track */}
                <circle cx="60" cy="60" r="44" fill="none" stroke="rgba(155,109,255,0.12)" strokeWidth="8" />
                {/* Arc */}
                <motion.circle
                    cx="60" cy="60" r="44"
                    fill="none"
                    stroke="url(#ringGrad)"
                    strokeWidth="8"
                    strokeLinecap="round"
                    strokeDasharray="220 57"
                    transform="rotate(-90 60 60)"
                    filter="url(#glow)"
                    initial={{ strokeDashoffset: 277 }}
                    animate={{ strokeDashoffset: 0 }}
                    transition={{ delay: 0.9, duration: 1.4, ease: [0.22, 1, 0.36, 1] }}
                />
                {/* Inner dot */}
                <circle cx="60" cy="60" r="28" fill="rgba(155,109,255,0.06)" />
                <circle cx="60" cy="60" r="16" fill="rgba(91,110,245,0.1)" />
            </svg>

            {/* Label row */}
            <div style={{ padding: "8px 0 4px", textAlign: "center" }}>
                <span style={{ fontSize: 11, fontWeight: 600, color: L.ink2 }}>Alpha Generation</span>
            </div>

            {/* Mini chart wave */}
            <svg width="100%" height="48" viewBox="0 0 200 48" preserveAspectRatio="none">
                <defs>
                    <linearGradient id="waveGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={L.purple} stopOpacity="0.4" />
                        <stop offset="100%" stopColor={L.purple} stopOpacity="0" />
                    </linearGradient>
                </defs>
                <path d="M0,38 C30,34 50,20 80,22 C110,24 130,36 160,28 C180,22 190,14 200,10 L200,48 L0,48 Z"
                    fill="url(#waveGrad)" />
                <path d="M0,38 C30,34 50,20 80,22 C110,24 130,36 160,28 C180,22 190,14 200,10"
                    fill="none" stroke={L.purple} strokeWidth="2" strokeLinecap="round" />
            </svg>
        </motion.div>
    );
}

function BtcPill() {
    return (
        <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.8, duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
            style={{
                background: "rgba(20,18,35,0.97)",
                border: `1px solid rgba(255,255,255,0.1)`,
                borderRadius: 10,
                padding: "8px 12px",
                display: "flex", alignItems: "center", gap: 8,
                boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
                alignSelf: "flex-start",
                position: "absolute",
                top: -28, right: -24,
            }}
        >
            <div style={{ width: 7, height: 7, borderRadius: "50%", background: L.green, boxShadow: `0 0 6px ${L.green}` }} />
            <div>
                <div style={{ fontSize: 10.5, fontWeight: 700, color: L.ink, letterSpacing: "0.04em" }}>BTC · BUY</div>
                <div style={{ fontSize: 9, color: L.ink3, marginTop: 1 }}>94% Confidence</div>
            </div>
        </motion.div>
    );
}

export default function AuthRightPanel() {
    return (
        <div style={{
            flex: 1,
            background: `radial-gradient(ellipse at 60% 40%, rgba(91,110,245,0.18) 0%, rgba(155,109,255,0.1) 30%, transparent 70%), #0a0b14`,
            display: "flex", alignItems: "center", justifyContent: "center",
            position: "relative", overflow: "hidden",
        }}>
            {/* Background glow blobs */}
            <div style={{
                position: "absolute", top: "30%", left: "40%",
                width: 320, height: 320, borderRadius: "50%",
                background: `radial-gradient(ellipse, rgba(155,109,255,0.15) 0%, transparent 70%)`,
                pointerEvents: "none",
            }} />
            <div style={{
                position: "absolute", bottom: "20%", right: "20%",
                width: 200, height: 200, borderRadius: "50%",
                background: `radial-gradient(ellipse, rgba(91,110,245,0.1) 0%, transparent 70%)`,
                pointerEvents: "none",
            }} />

            {/* Card + pill wrapper */}
            <div style={{ position: "relative" }}>
                <BtcPill />
                <AlphaCard />
            </div>
        </div>
    );
}