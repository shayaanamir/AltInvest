import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { L } from "../../components/landingPage/landingTokens";

import Step1Markets from "./Step1Markets";
import Step2RiskStyle from "./Step2RiskStyle";
import Step3Goals from "./Step3Goals";
import Step4Assets from "./Step4Assets";
import Step5Layout from "./Step5Layout";

const TOTAL_STEPS = 5;

const STEPS = [Step1Markets, Step2RiskStyle, Step3Goals, Step4Assets, Step5Layout];

export default function OnboardingPage({ onNavigate }) {
    const [step, setStep] = useState(0);
    const [answers, setAnswers] = useState({});

    const stepNum = step + 1;
    const progress = (stepNum / TOTAL_STEPS) * 100;

    const next = () => {
        if (step < TOTAL_STEPS - 1) setStep(s => s + 1);
        else onNavigate && onNavigate("Dashboard");
    };

    const back = () => {
        if (step > 0) setStep(s => s - 1);
    };

    const setAnswer = (key, val) => setAnswers(a => ({ ...a, [key]: val }));

    const StepComponent = STEPS[step];

    return (
        <div className="sv2" style={{
            minHeight: "100vh", width: "100vw",
            background: L.bg0,
            fontFamily: "'DM Sans', 'Segoe UI', sans-serif",
            color: L.ink,
            display: "flex", flexDirection: "column",
            overflow: "hidden",
        }}>
            <div style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "0 32px", height: 52, flexShrink: 0,
            }}>
                <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
                    <div style={{
                        width: 30, height: 30, borderRadius: 8,
                        background: "var(--sv2-accent)",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 13, fontWeight: 800, color: "#fff",
                    }}>A</div>
                    <span style={{ fontSize: 15, fontWeight: 700, color: L.ink, letterSpacing: "-0.3px" }}>AltInvest</span>
                </div>

                <span style={{ fontSize: 13, color: L.ink2, fontWeight: 500 }}>
                    Step {stepNum} of {TOTAL_STEPS}
                </span>

                <button
                    onClick={() => onNavigate && onNavigate("Dashboard")}
                    style={{
                        background: "none", border: "none", fontSize: 13,
                        color: L.ink2, cursor: "pointer", fontFamily: "inherit",
                        fontWeight: 500, padding: 0,
                        transition: "color 0.15s",
                    }}
                    onMouseEnter={e => e.currentTarget.style.color = L.ink}
                    onMouseLeave={e => e.currentTarget.style.color = L.ink2}
                >
                    Skip
                </button>
            </div>

            <div style={{ height: 3, background: "var(--sv2-chip)", flexShrink: 0 }}>
                <motion.div
                    animate={{ width: `${progress}%` }}
                    transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                    style={{
                        height: "100%",
                        background: "var(--sv2-accent)",
                        borderRadius: 2,
                    }}
                />
            </div>

            <div style={{ flex: 1, overflow: "auto", display: "flex", flexDirection: "column" }}>
                <AnimatePresence mode="wait">
                    <motion.div
                        key={step}
                        initial={{ opacity: 0, x: 32 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -32 }}
                        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
                        style={{ flex: 1, display: "flex", flexDirection: "column" }}
                    >
                        <StepComponent
                            answers={answers}
                            setAnswer={setAnswer}
                        />
                    </motion.div>
                </AnimatePresence>
            </div>

            <div style={{
                display: "flex", alignItems: "center",
                justifyContent: step === 0 ? "flex-end" : "space-between",
                padding: "16px 32px", flexShrink: 0,
            }}>
                {step > 0 && (
                    <button
                        onClick={back}
                        style={{
                            background: "none", border: "none", fontSize: 13,
                            color: L.ink2, cursor: "pointer", fontFamily: "inherit",
                            fontWeight: 500, padding: 0,
                        }}
                    >
                        Back
                    </button>
                )}
                <motion.button
                    onClick={next}
                    whileHover={{ scale: 1.03 }}
                    whileTap={{ scale: 0.97 }}
                    style={{
                        background: "var(--sv2-accent)",
                        border: "none", borderRadius: 10,
                        padding: "11px 28px", fontSize: 14, fontWeight: 700, color: "#fff",
                        cursor: "pointer", fontFamily: "inherit",
                        boxShadow: "0 4px 20px color-mix(in srgb, var(--sv2-accent) 35%, transparent)",
                    }}
                >
                    Continue
                </motion.button>
            </div>
        </div>
    );
}