import { useState } from "react";
import { DEFAULT_RISK } from "../../utils/onboardingPayload";
import StepHead from "./StepHead";

// The buckets match the backend (routes/profile.py risk_profile_from_score): up to 25, up to 65, above.
// The text describes a temperament, not a forecast: there are no return figures here on purpose.
const PROFILES = [
  { key: "conservative", label: "Conservative", text: "You prefer stability and smaller swings, even if growth is slower." },
  { key: "balanced", label: "Balanced", text: "You accept some ups and downs in return for steadier long-term growth." },
  { key: "aggressive", label: "Aggressive", text: "You're comfortable with large swings for the chance of bigger gains." },
];

function profileFor(value) {
  if (value <= 25) return PROFILES[0];
  return value <= 65 ? PROFILES[1] : PROFILES[2];
}

export default function Step2RiskStyle({ answers, setAnswer }) {
  const [value, setValue] = useState(answers.risk ?? DEFAULT_RISK);
  const profile = profileFor(value);

  const change = (e) => {
    const v = Number(e.target.value);
    setValue(v);
    setAnswer("risk", v);
  };

  return (
    <>
      <StepHead
        eyebrow="Risk"
        title="How much risk are you comfortable with?"
        sub="Drag the slider to the level that sounds most like you. There's no right answer."
      />
      <div className="ob-risk">
        <div className="ob-slider-wrap">
          <input
            className="ob-slider"
            type="range" min="0" max="100" step="1"
            value={value}
            onChange={change}
            aria-label="Risk tolerance"
            aria-valuetext={profile.label}
            style={{ "--ob-pct": `${value}%` }}
          />
          <div className="ob-zones" aria-hidden="true">
            {PROFILES.map((p) => (
              <span key={p.key} className={`ob-zone ${p.key === profile.key ? "is-active" : ""}`}>{p.label}</span>
            ))}
          </div>
        </div>

        <div className="sv2-card ob-profile-card" aria-live="polite">
          <div className="ob-eyebrow">Your risk profile</div>
          <div className="ob-profile-name">{profile.label}</div>
          <div className="ob-option-desc">{profile.text}</div>
        </div>
        <p className="ob-note">
          Saved to your profile as a reminder of your own tolerance. AltInvest shows each asset's risk score
          separately. This is not investment advice.
        </p>
      </div>
    </>
  );
}
