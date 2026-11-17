import { IconDashboard, IconPortfolio, IconCompass, IconChart } from "../icons";
import { useTheme } from "../../context/ThemeContext";
import { DEFAULT_FOCUS, FOCUS_PRESETS, WIDGET_LABELS, normalizeFocus } from "../../utils/homeFocus";
import { DEFAULT_DENSITY } from "../../utils/onboardingPayload";
import OptionCard from "./OptionCard";
import StepHead from "./StepHead";

const FOCUS_ICONS = {
  everything: <IconDashboard size={20} />,
  portfolio: <IconPortfolio size={20} />,
  markets: <IconCompass size={20} />,
  sentiment: <IconChart size={20} />,
};

/** A miniature of the dashboard this focus produces, drawn from the same rows the dashboard renders. */
function Preview({ rows }) {
  const lead = rows.flat().find((id) => id !== "stats");
  return (
    <span className="ob-preview" aria-hidden="true">
      {rows.map((row) => (
        <span className="ob-prev-row" key={row.join("+")}>
          {row.map((id) => (
            <span key={id} className={`ob-prev-block ${id === "stats" ? "is-stats" : ""} ${id === lead ? "is-lead" : ""}`}>
              {WIDGET_LABELS[id]}
            </span>
          ))}
        </span>
      ))}
    </span>
  );
}

export default function Step5Focus({ answers, setAnswer }) {
  const { isDark, setTheme } = useTheme();
  const focus = normalizeFocus(answers.focus ?? DEFAULT_FOCUS);
  const density = answers.density === "compact" ? "compact" : DEFAULT_DENSITY;

  return (
    <>
      <StepHead
        eyebrow="Your home"
        title="What do you want to see first?"
        sub="This sets what your dashboard shows and where AltInvest opens each time you sign in. You can change any of it later in Settings."
      />

      <section className="ob-group">
        <h2 className="ob-group-title">Home focus</h2>
        <p className="ob-group-sub">The preview is the dashboard you'll get.</p>
        <div className="ob-grid cols-2" role="radiogroup" aria-label="Home focus">
          {FOCUS_PRESETS.map((p) => (
            <OptionCard
              key={p.key}
              role="radio"
              className="ob-focus"
              selected={focus === p.key}
              onClick={() => setAnswer("focus", p.key)}
            >
              <span className="ob-focus-head">
                <span className="ob-option-icon" aria-hidden="true">{FOCUS_ICONS[p.key]}</span>
                <span className="ob-option-body">
                  <span className="ob-option-title">{p.label} · <span style={{ fontWeight: 500 }}>{p.blurb}</span></span>
                  <span className="ob-option-desc">{p.description}</span>
                </span>
              </span>
              <Preview rows={p.rows} />
              <span className="ob-lands">Opens on: <strong>{p.landing}</strong></span>
            </OptionCard>
          ))}
        </div>
      </section>

      <section className="ob-group">
        <div className="ob-looks">
          <div>
            <h2 className="ob-group-title">Density</h2>
            <p className="ob-group-sub">Compact fits the dashboard on one screen.</p>
            <div className="sv2-segmented" role="radiogroup" aria-label="Density">
              {[["comfortable", "Comfortable"], ["compact", "Compact"]].map(([key, label]) => (
                <button
                  key={key} type="button" role="radio" aria-checked={density === key}
                  className={density === key ? "active" : ""}
                  onClick={() => setAnswer("density", key)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <h2 className="ob-group-title">Theme</h2>
            <p className="ob-group-sub">Applied as you choose.</p>
            <div className="sv2-segmented" role="radiogroup" aria-label="Theme">
              {[["dark", "Dark"], ["light", "Light"]].map(([key, label]) => (
                <button
                  key={key} type="button" role="radio" aria-checked={(key === "dark") === isDark}
                  className={(key === "dark") === isDark ? "active" : ""}
                  onClick={() => setTheme(key)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
