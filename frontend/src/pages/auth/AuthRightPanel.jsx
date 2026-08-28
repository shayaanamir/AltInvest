import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { useTheme } from "../../context/ThemeContext";
import { useLandingTheme, ACCENT_HEX } from "../../components/landingPage/landingTokens";

function hexToRgba(hex, alpha) {
    const h = hex.replace("#", "");
    const r = parseInt(h.slice(0, 2), 16);
    const g = parseInt(h.slice(2, 4), 16);
    const b = parseInt(h.slice(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function MarketLine() {
    const canvasRef = useRef(null);
    const rafRef = useRef(null);
    const offsetRef = useRef(0);
    const { isDark } = useTheme();
    const accentHex = isDark ? ACCENT_HEX.dark : ACCENT_HEX.light;

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");

        const seed = [
            0.50, 0.52, 0.48, 0.53, 0.50, 0.45, 0.47, 0.44, 0.46, 0.41,
            0.43, 0.40, 0.38, 0.42, 0.39, 0.36, 0.34, 0.37, 0.33, 0.30,
            0.32, 0.28, 0.31, 0.27, 0.24, 0.26, 0.22, 0.25, 0.21, 0.18,
            0.20, 0.16, 0.19, 0.14, 0.17, 0.13, 0.15, 0.11, 0.14, 0.10,
        ];

        const draw = () => {
            const W = canvas.width;
            const H = canvas.height;
            ctx.clearRect(0, 0, W, H);
            offsetRef.current += 0.003;
            const t = offsetRef.current;

            const pts = seed.map((v, i) => ({
                x: (i / (seed.length - 1)) * W,
                y: (v + Math.sin(t + i * 0.4) * 0.018 + Math.cos(t * 0.7 + i * 0.3) * 0.012) * H,
            }));

            const grad = ctx.createLinearGradient(0, 0, 0, H);
            grad.addColorStop(0, hexToRgba(accentHex, isDark ? 0.10 : 0.08));
            grad.addColorStop(0.7, hexToRgba(accentHex, isDark ? 0.02 : 0.01));
            grad.addColorStop(1, hexToRgba(accentHex, 0));

            ctx.beginPath();
            ctx.moveTo(pts[0].x, pts[0].y);
            for (let i = 1; i < pts.length - 1; i++) {
                const mx = (pts[i].x + pts[i + 1].x) / 2;
                const my = (pts[i].y + pts[i + 1].y) / 2;
                ctx.quadraticCurveTo(pts[i].x, pts[i].y, mx, my);
            }
            ctx.lineTo(pts[pts.length - 1].x, pts[pts.length - 1].y);
            ctx.lineTo(W, H); ctx.lineTo(0, H); ctx.closePath();
            ctx.fillStyle = grad;
            ctx.fill();

            ctx.beginPath();
            ctx.moveTo(pts[0].x, pts[0].y);
            for (let i = 1; i < pts.length - 1; i++) {
                const mx = (pts[i].x + pts[i + 1].x) / 2;
                const my = (pts[i].y + pts[i + 1].y) / 2;
                ctx.quadraticCurveTo(pts[i].x, pts[i].y, mx, my);
            }
            ctx.lineTo(pts[pts.length - 1].x, pts[pts.length - 1].y);
            ctx.strokeStyle = hexToRgba(accentHex, isDark ? 0.5 : 0.65);
            ctx.lineWidth = 1.2;
            ctx.lineJoin = "round";
            ctx.stroke();

            const lx = pts[pts.length - 1].x, ly = pts[pts.length - 1].y;
            ctx.beginPath(); ctx.arc(lx, ly, 2.8, 0, Math.PI * 2);
            ctx.fillStyle = hexToRgba(accentHex, 0.95); ctx.fill();
            ctx.beginPath(); ctx.arc(lx, ly, 6, 0, Math.PI * 2);
            ctx.strokeStyle = hexToRgba(accentHex, 0.22); ctx.lineWidth = 1; ctx.stroke();

            rafRef.current = requestAnimationFrame(draw);
        };

        draw();
        return () => cancelAnimationFrame(rafRef.current);
    }, [isDark, accentHex]);

    return (
        <canvas
            ref={canvasRef}
            width={560} height={180}
            style={{ display: "block", width: "100%", maxWidth: 560, height: 180 }}
        />
    );
}

function Ticker() {
    const T = useLandingTheme();
    const items = [
        { label: "BTC", value: "+4.2%", up: true },
        { label: "ETH", value: "+2.8%", up: true },
        { label: "SPX", value: "−0.4%", up: false },
        { label: "GOLD", value: "+0.9%", up: true },
        { label: "VIX", value: "18.4", up: null },
    ];
    return (
        <div style={{ display: "flex", gap: 24, alignItems: "center" }}>
            {items.map(({ label, value, up }) => (
                <div key={label} style={{ display: "flex", gap: 5, alignItems: "baseline" }}>
                    <span style={{ fontSize: 9.5, fontWeight: 600, color: T.ink3, letterSpacing: "0.12em" }}>
                        {label}
                    </span>
                    <span style={{
                        fontSize: 10.5, fontWeight: 600,
                        color: up === true ? T.green
                            : up === false ? T.red
                                : T.ink2,
                    }}>
                        {value}
                    </span>
                </div>
            ))}
        </div>
    );
}

export default function AuthRightPanel() {
    const { isDark } = useTheme();
    const T = useLandingTheme();

    return (
        <div style={{
            flex: 1, position: "relative", overflow: "hidden",
            background: "var(--sv2-bg)",
            display: "flex", alignItems: "center",
            justifyContent: "center",
        }}>
            <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: isDark ? 0.022 : 0.06 }} xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <pattern id="grid" width="48" height="48" patternUnits="userSpaceOnUse">
                        <path d="M48 0H0V48" fill="none" stroke={isDark ? "white" : "rgba(36,33,28,0.2)"} strokeWidth="0.5" />
                    </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#grid)" />
            </svg>

            <div style={{
                position: "absolute", top: "42%", left: "50%",
                transform: "translate(-50%, -50%)",
                width: 640, height: 640, borderRadius: "50%",
                background: "radial-gradient(ellipse, color-mix(in srgb, var(--sv2-accent) 13%, transparent) 0%, color-mix(in srgb, var(--sv2-accent) 6%, transparent) 45%, transparent 70%)",
                pointerEvents: "none",
            }} />

            <div style={{
                position: "relative", zIndex: 1,
                display: "flex", flexDirection: "column", alignItems: "flex-start",
                width: "72%", maxWidth: 520,
            }}>
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.35, duration: 0.9 }}
                    style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 32 }}
                >
                    <motion.div
                        animate={{ opacity: [1, 0.25, 1] }}
                        transition={{ repeat: Infinity, duration: 2.8, ease: "easeInOut" }}
                        style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--sv2-green)" }}
                    />
                    <span style={{ fontSize: 10, fontWeight: 600, color: T.ink3, letterSpacing: "0.18em", textTransform: "uppercase" }}>
                        Live Markets
                    </span>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.5, duration: 1.4 }}
                    style={{ width: "100%", marginBottom: 20 }}
                >
                    <MarketLine />
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.75, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
                    style={{ marginBottom: 64 }}
                >
                    <Ticker />
                </motion.div>

                <motion.div
                    initial={{ scaleX: 0, opacity: 0 }}
                    animate={{ scaleX: 1, opacity: 1 }}
                    transition={{ delay: 0.85, duration: 1.1, ease: [0.22, 1, 0.36, 1] }}
                    style={{
                        width: "100%", height: "1px",
                        background: `linear-gradient(to right, ${T.border2}, ${T.border} 70%, transparent)`,
                        transformOrigin: "left", marginBottom: 44,
                    }}
                />

                <motion.div
                    initial={{ opacity: 0, y: 14 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 1.0, duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
                >
                    <p style={{
                        fontSize: 10, fontWeight: 600,
                        color: T.ink3,
                        letterSpacing: "0.18em", textTransform: "uppercase",
                        margin: "0 0 16px",
                    }}>
                        AltInvest Platform
                    </p>
                    <h2 style={{
                        fontSize: 34, fontWeight: 700,
                        color: T.ink,
                        letterSpacing: "-0.8px", lineHeight: 1.2,
                        margin: "0 0 16px",
                        fontFamily: T.font,
                    }}>
                        Alternative Investment<br />Intelligence.
                    </h2>
                    <p style={{
                        fontSize: 14, fontWeight: 400,
                        color: T.ink2,
                        lineHeight: 1.65, margin: 0,
                    }}>
                        Unified analytics for modern assets.
                    </p>
                </motion.div>
            </div>

            <div style={{
                position: "absolute", bottom: 0, left: 0, right: 0, height: 72,
                background: "linear-gradient(to top, var(--sv2-bg), transparent)",
                pointerEvents: "none",
            }} />
        </div>
    );
}