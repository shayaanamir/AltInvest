import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { L } from "../components/landingPage/landingTokens";

import Step1Markets from "../components/onboarding/Step1Markets";
import Step2RiskStyle from "../components/onboarding/Step2RiskStyle";
import Step3Goals from "../components/onboarding/Step3Goals";
import Step4Assets from "../components/onboarding/Step4Assets";
import Step5Layout from "../components/onboarding/Step5Layout";
import { onboardingApi } from "../services/onboardingApi";
import { authApi } from "../services/authApi";
import { answersToPayload } from "../utils/onboardingPayload";

const TOTAL_STEPS = 5;

const STEPS = [Step1Markets, Step2RiskStyle, Step3Goals, Step4Assets, Step5Layout];

export default function OnboardingPage({ onNavigate }) {
    const [step, setStep] = useState(0);
    const [answers, setAnswers] = useState({});
    const [saving, setSaving] = useState(false);
    const [saveFailed, setSaveFailed] = useState(false);

    const stepNum = step + 1;
    const progress = (stepNum / TOTAL_STEPS) * 100;

    const goToDashboard = () => onNavigate && onNavigate("Dashboard");

    // Saves the answers (or the skip), then leaves. Leaves only once the server has them, so a
    // failed save is shown and can be retried, or the person can carry on without saving.
    const finish = async (skipped) => {
        if (saving) return;
        setSaving(true);
        setSaveFailed(false);
        try {
            await onboardingApi.save(answersToPayload(answers, { skipped }));
        } catch {
            setSaving(false);
            setSaveFailed(true);
            return;
        }
        authApi.me().catch(() => {});   // refresh the saved user (onboarding_completed); not worth blocking on
        goToDashboard();
    };

    const next = () => {
        if (step < TOTAL_STEPS - 1) setStep(s => s + 1);
        else finish(false);
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
                    onClick={() => finish(true)}
                    disabled={saving}
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

            {saveFailed && (
                <div role="alert" style={{
                    display: "flex", alignItems: "center", justifyContent: "center", gap: 14, flexWrap: "wrap",
                    padding: "10px 32px", fontSize: 13, color: "var(--sv2-red, #e5484d)", flexShrink: 0,
                }}>
                    <span>We couldn't save your answers. Check your connection and try again.</span>
                    <button
                        onClick={goToDashboard}
                        style={{
                            background: "none", border: "none", padding: 0, fontSize: 13, fontWeight: 600,
                            color: L.ink2, cursor: "pointer", fontFamily: "inherit", textDecoration: "underline",
                        }}
                    >
                        Continue without saving
                    </button>
                </div>
            )}

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
                    disabled={saving}
                    whileHover={saving ? undefined : { scale: 1.03 }}
                    whileTap={saving ? undefined : { scale: 0.97 }}
                    style={{
                        background: "var(--sv2-accent)",
                        border: "none", borderRadius: 10,
                        padding: "11px 28px", fontSize: 14, fontWeight: 700, color: "#fff",
                        cursor: saving ? "default" : "pointer", fontFamily: "inherit",
                        opacity: saving ? 0.7 : 1,
                        boxShadow: "0 4px 20px color-mix(in srgb, var(--sv2-accent) 35%, transparent)",
                    }}
                >
                    {saving ? "Saving…" : step === TOTAL_STEPS - 1 ? "Finish" : "Continue"}
                </motion.button>
            </div>
        </div>
    );
}