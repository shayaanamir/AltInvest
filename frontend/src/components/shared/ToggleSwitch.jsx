export default function ToggleSwitch({ checked, onChange, disabled = false, label }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      className={`sv2-toggle ${checked ? "on" : ""}`}
      onClick={() => !disabled && onChange && onChange(!checked)}
    >
      <span className="sv2-toggle-thumb" />
    </button>
  );
}

