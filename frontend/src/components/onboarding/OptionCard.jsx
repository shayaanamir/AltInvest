import { IconCheck2 } from "../icons";

/**
 * A selectable card used by the onboarding steps (markets, goals, home focus).
 * Rendered as a real <button> so it works with the keyboard; `role` is "checkbox" for multi-select
 * steps and "radio" for single-choice ones.
 */
export default function OptionCard({
  selected, onClick, icon, title, badge, desc, meta, role = "checkbox", className = "", children,
}) {
  return (
    <button
      type="button"
      role={role}
      aria-checked={selected}
      className={`ob-option ${selected ? "is-selected" : ""} ${className}`}
      onClick={onClick}
    >
      <span className="ob-check" aria-hidden="true"><IconCheck2 size={13} /></span>
      {children ?? (
        <>
          {icon && <span className="ob-option-icon" aria-hidden="true">{icon}</span>}
          <span className="ob-option-body">
            <span className="ob-option-title">
              {title}
              {badge && <span className="ob-badge">{badge}</span>}
            </span>
            {desc && <span className="ob-option-desc">{desc}</span>}
            {meta && <span className="ob-option-meta">{meta}</span>}
          </span>
        </>
      )}
    </button>
  );
}
