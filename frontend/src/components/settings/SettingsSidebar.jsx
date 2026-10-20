import { IconTune, IconPalette, IconBell, IconShield, IconLink, IconDatabase } from "../icons";

const ICONS = {
  tune: <IconTune size={16} />,
  palette: <IconPalette size={16} />,
  bell: <IconBell size={16} />,
  shield: <IconShield size={16} />,
  link: <IconLink size={16} />,
  db: <IconDatabase size={16} />,
};

export default function SettingsSidebar({ tabs, activeTab, onSelect }) {
  return (
    <nav className="sv2-card set-sidebar">
      {tabs.map((t) => (
        <button
          key={t.key}
          className={`set-sidebar-item ${activeTab === t.key ? "active" : ""}`}
          onClick={() => onSelect(t.key)}
        >
          <span className="set-sidebar-icon">{ICONS[t.icon]}</span>
          <span>{t.label}</span>
        </button>
      ))}
    </nav>
  );
}