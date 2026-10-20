import { useTheme } from "../../context/ThemeContext";
import SettingsRow from "./SettingsRow";
import ToggleSwitch from "./ToggleSwitch";

export default function AppearanceSection({ data, onChange }) {
  const { isDark, toggle } = useTheme();
  if (!data) return null;

  const handleDarkModeToggle = () => {
    const nextIsDark = !isDark;
    toggle();
    onChange({ theme: nextIsDark ? "dark" : "light" });
  };

  return (
    <div className="sv2-card set-content">
      <div className="set-section-head">
        <div className="set-section-title">Appearance</div>
        <div className="set-section-sub">The canonical home for theme and density</div>
      </div>

      <SettingsRow title="Dark mode" description="Also available from the top bar">
        <ToggleSwitch checked={isDark} onChange={handleDarkModeToggle} label="Dark mode" />
      </SettingsRow>

      <SettingsRow title="Density" description="Compact tightens table and list spacing">
        <select
          className="sv2-select set-select"
          value={data.density}
          onChange={(e) => onChange({ density: e.target.value })}
        >
          {data.densityOptions.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      </SettingsRow>
    </div>
  );
}