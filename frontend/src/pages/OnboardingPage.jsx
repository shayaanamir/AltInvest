import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import "../styles/onboarding.css";

import Step1Markets from "../components/onboarding/Step1Markets";
import Step2RiskStyle from "../components/onboarding/Step2RiskStyle";
import Step3Goals from "../components/onboarding/Step3Goals";
import Step4Assets from "../components/onboarding/Step4Assets";
import Step5Focus from "../components/onboarding/Step5Focus";
import { IconThemeToggle, IconArrowLeft, IconArrowRight } from "../components/icons";
import { useTheme } from "../context/ThemeContext";
import { onboardingApi } from "../services/onboardingApi";
import { authApi } from "../services/authApi";
import { resolveLandingPath } from "../services/appPreferences";
import { answersToPayload } from "../utils/onboardingPayload";
import systemStates from "../content/systemStates.json";

const STEPS = [Step1Markets, Step2RiskStyle, Step3Goals, Step4Assets, Step5Focus];
const TOTAL_STEPS = STEPS.length;

function SkipDialog({ onStay, onLeave }) {
    const { title, message, confirmLabel, cancelLabel } = systemStates.confirmDialogs.abandonOnboarding;
    useEffect(() => {
        const onKey = (e) => e.key === "Escape" && onStay();
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, [onStay]);

    return (
        <div className="sv2-modal-overlay" onClick={onStay}>
            <div className="sv2-modal ob-modal" role="dialog" aria-modal="true" aria-labelledby="ob-skip-title" onClick={(e) => e.stopPropagation()}>
                <h3 id="ob-skip-title">{title}</h3>
                <p>{message}</p>
                <div className="ob-modal-actions">
                    <button type="button" className="ob-btn ob-btn-outline" onClick={onLeave}>{confirmLabel}</button>
                    <button type="button" className="ob-btn ob-btn-primary" onClick={onStay} autoFocus>{cancelLabel}</button>
                </div>
            </div>
        </div>
    );
}

export default function OnboardingPage({ onNavigate }) {
    const [step, setStep] = useState(0);
    const [answers, setAnswers] = useState({});
    const [saving, setSaving] = useState(false);
    const [saveFailed, setSaveFailed] = useState(false);
    const [confirmSkip, setConfirmSkip] = useState(false);
    const { isDark, toggle } = useTheme();
    const reduceMotion = useReducedMotion();
    const navigate = useNavigate();
    const mainRef = useRef(null);
    const firstRender = useRef(true);

    const setAnswer = (key, val) => setAnswers((a) => ({ ...a, [key]: val }));
    const StepComponent = STEPS[step];

    // Move to the top of each new step and put keyboard focus there.
    useEffect(() => {
        if (firstRender.current) { firstRender.current = false; return; }
        window.scrollTo(0, 0);
        mainRef.current?.focus({ preventScroll: true });
    }, [step]);

    const leave = async () => {
        // The saved home focus decides where to land; fall back to the dashboard if it can't be read.
        try {
            navigate(await resolveLandingPath(), { replace: true });
        } catch {
            if (onNavigate) onNavigate("Dashboard"); else navigate("/dashboard", { replace: true });
        }
    };

    // Saves the answers (or the skip), then leaves. It leaves only once the server has them, so a
    // failed save is shown and can be retried, or the person can carry on without saving.
    const finish = async (skipped) => {
        if (saving) return;
        setConfirmSkip(false);
        setSaving(true);
        setSaveFailed(false);
        try {
            await onboardingApi.save(answersToPayload(answers, { skipped, theme: isDark ? "dark" : "light" }));
        } catch {
            setSaving(false);
            setSaveFailed(true);
            return;
        }
        authApi.me().catch(() => {});   // refresh the saved user (onboarding_completed); not worth blocking on
        leave();
    };

    const next = () => (step < TOTAL_STEPS - 1 ? setStep((s) => s + 1) : finish(false));
    const back = () => step > 0 && setStep((s) => s - 1);

    return (
        <div className="sv2 ob-page">
            <div className="ob-top">
                <div className="ob-brand">
                    <div className="ob-logo" aria-hidden="true">AI</div>
                    <div className="ob-brand-text">
                        <span className="ob-brand-name">AltInvest</span>
                        <span className="ob-brand-sub">Alternative asset desk</span>
                    </div>
                </div>
                <div className="ob-top-right">
                    <span className="ob-stepcount">Step {step + 1} of {TOTAL_STEPS}</span>
                    <button
                        type="button" className="ob-icon-btn" onClick={toggle}
                        title={isDark ? "Switch to light mode" : "Switch to dark mode"}
                        aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
                    >
                        <IconThemeToggle isDark={isDark} variant="outline" size={16} />
                    </button>
                    <button type="button" className="ob-link" onClick={() => setConfirmSkip(true)} disabled={saving}>Skip</button>
                </div>
            </div>

            <div className="ob-progress" role="progressbar" aria-valuemin={1} aria-valuemax={TOTAL_STEPS} aria-valuenow={step + 1} aria-label="Onboarding progress">
                {STEPS.map((_, i) => <span key={i} className={`ob-seg ${i <= step ? "done" : ""}`} />)}
            </div>

            <main className="ob-main" ref={mainRef} tabIndex={-1} style={{ outline: "none" }}>
                <AnimatePresence mode="wait">
                    <motion.div
                        key={step}
                        initial={reduceMotion ? false : { opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={reduceMotion ? { opacity: 1 } : { opacity: 0 }}
                        transition={{ duration: reduceMotion ? 0 : 0.18 }}
                    >
                        <StepComponent answers={answers} setAnswer={setAnswer} />
                    </motion.div>
                </AnimatePresence>
            </main>

            {saveFailed && (
                <div role="alert" className="ob-saveerr">
                    <span>We couldn't save your answers. Check your connection and try again.</span>
                    <button type="button" className="ob-link" onClick={leave}>Continue without saving</button>
                </div>
            )}

            <div className="ob-footer">
                <div className="ob-footer-inner">
                    {step > 0 ? (
                        <button type="button" className="ob-btn ob-btn-outline" onClick={back} disabled={saving}>
                            <IconArrowLeft size={14} /> Back
                        </button>
                    ) : <span />}
                    <button type="button" className="ob-btn ob-btn-primary" onClick={next} disabled={saving}>
                        {saving ? "Saving…" : step === TOTAL_STEPS - 1 ? "Finish" : "Continue"}
                        {!saving && step < TOTAL_STEPS - 1 && <IconArrowRight size={14} />}
                    </button>
                </div>
            </div>

            {confirmSkip && <SkipDialog onStay={() => setConfirmSkip(false)} onLeave={() => finish(true)} />}
        </div>
    );
}
