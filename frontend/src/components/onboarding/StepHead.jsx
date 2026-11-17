/** The eyebrow, title and one-line explanation at the top of every onboarding step. */
export default function StepHead({ eyebrow, title, sub }) {
  return (
    <header>
      <div className="ob-eyebrow">{eyebrow}</div>
      <h1 className="ob-title">{title}</h1>
      {sub && <p className="ob-sub">{sub}</p>}
    </header>
  );
}
