import { useState } from "react";
import { motion } from "framer-motion";
import { L } from "../../components/landingPage/landingTokens";

const PROFILES = [
    { label: "Conservative", val: 0, returns: "4–7%", vol: "Low", rec: "Capital preservation + stable yield" },
    { label: "Balanced", val: 50, returns: "8–12%", vol: "Medium", rec: "Diversified index + alt exposure" },
    { label: "Aggressive", val: 100, returns: "15–30%", vol: "High", rec: "High-conviction alpha strategies" },
];

function getProfile(val) {
    if (val <= 25) return PROFILES[0];
    if (val <= 65) return PROFILES[1];
    return PROFILES[2];
}

const chartPaths = {
    Conservative: "M0,40 C20,38 40,35 60,34 C80,33 100,32 140,30 C170,28 200,27 230,26",
    Balanced: "M0,44 C30,40 50,30 80,32 C110,34 130,28 160,22 C185,17 210,14 230,12",
    Aggressive: "M0,44 C20,38 40,24 70,20 C100,16 130,10 160,6 C185,3 210,2 230,2",
};

export default function Step2RiskStyle({ answers, setAnswer }) {
    const [sliderVal, setSliderVal] = useState(answers.risk ?? 50);
    const profile = getProfile(sliderVal);

    const handleChange = (e) => {
        const v = Number(e.target.value);
        setSliderVal(v);
        setAnswer("risk", v);
    };

    const path = chartPaths[profile.label];

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
                What's your investment style?
            </motion.h1>
            <motion.p
                initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.08, duration: 0.5 }}
                style={{ fontSize: 15, color: L.ink2, margin: "0 0 48px", textAlign: "center" }}
            >
                Drag the slider to set your risk appetite.
            </motion.p>

            {/* Slider */}
            <motion.div
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15, duration: 0.5 }}
                style={{ width: "100%", maxWidth: 500, marginBottom: 12 }}
            >
                <style>{`
          .risk-slider { -webkit-appearance: none; appearance: none; width: 100%; height: 4px;
            border-radius: 2px; outline: none; cursor: pointer;
            background: linear-gradient(90deg, #5b6ef5 ${sliderVal}%, rgba(255,255,255,0.12) ${sliderVal}%);
          }
          .risk-slider::-webkit-slider-thumb { -webkit-appearance: none; width: 20px; height: 20px;
            border-radius: 50%; background: #5b6ef5; border: 3px solid #fff;
            box-shadow: 0 2px 8px rgba(91,110,245,0.5); cursor: pointer; }
          .risk-slider::-moz-range-thumb { width: 20px; height: 20px; border-radius: 50%;
            background: #5b6ef5; border: 3px solid #fff; box-shadow: 0 2px 8px rgba(91,110,245,0.5); cursor: pointer; }
        `}</style>
                <input
                    type="range" min="0" max="100"
                    value={sliderVal}
                    onChange={handleChange}
                    className="risk-slider"
                />

                {/* Labels */}
                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 10 }}>
                    {PROFILES.map(p => (
                        <span key={p.label} style={{
                            fontSize: 12.5, fontWeight: profile.label === p.label ? 700 : 400,
                            color: profile.label === p.label ? L.blue : L.ink3,
                            transition: "color 0.2s",
                        }}>
                            {p.label}
                        </span>
                    ))}
                </div>
            </motion.div>

            {/* Profile card */}
            <motion.div
                initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2, duration: 0.5 }}
                style={{
                    width: "100%", maxWidth: 500,
                    background: "rgba(255,255,255,0.04)",
                    border: "1px solid rgba(255,255,255,0.09)",
                    borderRadius: 14, overflow: "hidden",
                }}
            >
                {/* Chart */}
                <div style={{ padding: "20px 20px 0", position: "relative", height: 80 }}>
                    <svg width="100%" height="60" viewBox="0 0 230 48" preserveAspectRatio="none">
                        <defs>
                            <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor={L.blue} stopOpacity="0.3" />
                                <stop offset="100%" stopColor={L.blue} stopOpacity="0" />
                            </linearGradient>
                        </defs>
                        <motion.path
                            key={profile.label}
                            d={path + ` L230,48 L0,48 Z`}
                            fill="url(#riskGrad)"
                            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                            transition={{ duration: 0.4 }}
                        />
                        <motion.path
                            key={profile.label + "-line"}
                            d={path}
                            fill="none" stroke={L.blue} strokeWidth="2" strokeLinecap="round"
                            initial={{ pathLength: 0 }} animate={{ pathLength: 1 }}
                            transition={{ duration: 0.7, ease: "easeOut" }}
                        />
                    </svg>
                </div>

                {/* Stats */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0 }}>
                    <div style={{ padding: "16px 20px", borderTop: "1px solid rgba(255,255,255,0.06)", borderRight: "1px solid rgba(255,255,255,0.06)" }}>
                        <div style={{ fontSize: 10.5, color: L.ink3, fontWeight: 600, marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.06em" }}>Expected Return</div>
                        <div style={{ fontSize: 22, fontWeight: 700, color: L.ink, letterSpacing: "-0.5px" }}>{profile.returns}</div>
                    </div>
                    <div style={{ padding: "16px 20px", borderTop: "1px solid rgba(255,255,255,0.06)" }}>
                        <div style={{ fontSize: 10.5, color: L.ink3, fontWeight: 600, marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.06em" }}>Volatility</div>
                        <div style={{ fontSize: 22, fontWeight: 700, color: L.ink, letterSpacing: "-0.5px" }}>{profile.vol}</div>
                    </div>
                </div>

                {/* AI rec */}
                <div style={{ padding: "14px 20px", borderTop: "1px solid rgba(255,255,255,0.06)", background: "rgba(91,110,245,0.06)" }}>
                    <div style={{ fontSize: 10, color: L.blue, fontWeight: 700, marginBottom: 4, letterSpacing: "0.05em" }}>AI Recommendation</div>
                    <div style={{ fontSize: 13, color: L.ink }}>{profile.rec}</div>
                </div>
            </motion.div>
        </div>
    );
}