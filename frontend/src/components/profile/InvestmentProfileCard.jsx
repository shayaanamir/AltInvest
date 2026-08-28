const RISK_PCT = { conservative: 15, balanced: 50, aggressive: 85 };

function labelize(v) {
  if (!v) return "";
  return v.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function InvestmentProfileCard({ profile, editing, onChange }) {
  if (!profile) return null;
  const riskKey = (profile.riskProfile || "balanced").toLowerCase();
  const pct = RISK_PCT[riskKey] ?? 50;
  const goalOptions = profile.investmentGoalOptions || [];
  const goalKnown = goalOptions.includes(profile.investmentGoal);

  return (
    <div className="sv2-card set-subcard">
      <div className="set-section-title">Investment profile</div>
      <div className="set-row-desc set-mb-16">Captured at onboarding — editable here</div>

      <div className="prof-investment-grid">
        <div>
          <div className="prof-investment-label">Risk style</div>
          <div className="prof-risk-value">{labelize(riskKey)}</div>
          <div className="prof-risk-bar-track">
            <div className="prof-risk-bar-fill" style={{ width: `${pct}%` }} />
          </div>
          <div className="prof-risk-pills">
            {(profile.riskProfileOptions || []).map((opt) => (
              <button
                key={opt}
                type="button"
                disabled={!editing}
                className={`prof-risk-pill ${riskKey === opt ? "active" : ""}`}
                onClick={() => onChange && onChange({ riskProfile: opt })}
              >
                {labelize(opt)}
              </button>
            ))}
          </div>
        </div>

        <div>
          <div className="prof-investment-label">Primary goal</div>
          <select
            className="sv2-select set-select"
            value={profile.investmentGoal}
            disabled={!editing}
            onChange={(e) => onChange && onChange({ investmentGoal: e.target.value })}
          >
            {!goalKnown && <option value={profile.investmentGoal}>{labelize(profile.investmentGoal)}</option>}
            {goalOptions.map((g) => (
              <option key={g} value={g}>{labelize(g)}</option>
            ))}
          </select>
          <p className="set-row-desc set-mt-8">
            Your goal shapes what the dashboard puts first and how aggressively thin-evidence signals surface.
          </p>
        </div>
      </div>
    </div>
  );
}