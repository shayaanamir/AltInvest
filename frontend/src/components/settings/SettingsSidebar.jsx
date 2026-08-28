const ICONS = {
  tune: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <line x1="4" y1="6" x2="20" y2="6" /><circle cx="9" cy="6" r="2" fill="currentColor" stroke="none" />
      <line x1="4" y1="12" x2="20" y2="12" /><circle cx="15" cy="12" r="2" fill="currentColor" stroke="none" />
      <line x1="4" y1="18" x2="20" y2="18" /><circle cx="11" cy="18" r="2" fill="currentColor" stroke="none" />
    </svg>
  ),
  palette: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2a10 10 0 100 20c1.1 0 2-.9 2-2 0-.5-.2-1-.5-1.4-.3-.4-.5-.8-.5-1.3 0-1 .8-1.8 1.8-1.8H17a3 3 0 003-3c0-5-3.6-10.5-8-10.5z" />
      <circle cx="6.5" cy="11.5" r="1.2" fill="currentColor" stroke="none" />
      <circle cx="8.5" cy="7" r="1.2" fill="currentColor" stroke="none" />
      <circle cx="14" cy="6" r="1.2" fill="currentColor" stroke="none" />
    </svg>
  ),
  bell: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8a6 6 0 10-12 0c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.7 21a2 2 0 01-3.4 0" />
    </svg>
  ),
  shield: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2l8 4v6c0 5-3.4 8.7-8 10-4.6-1.3-8-5-8-10V6z" />
    </svg>
  ),
  link: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 13a5 5 0 007.5.5l2-2a5 5 0 00-7-7l-1.2 1.2" />
      <path d="M14 11a5 5 0 00-7.5-.5l-2 2a5 5 0 007 7l1.2-1.2" />
    </svg>
  ),
  db: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <ellipse cx="12" cy="5" rx="8" ry="3" /><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5" /><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" />
    </svg>
  ),
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