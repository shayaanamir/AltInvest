export default function ToggleSwitch({ checked, onChange, disabled = false, label }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      className={`set-toggle ${checked ? "on" : ""}`}
      onClick={() => !disabled && onChange && onChange(!checked)}
    >
      <span className="set-toggle-thumb" />
    </button>
  );
}