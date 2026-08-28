export default function SettingsFooter({ onOpenProfile, onLogout }) {
  return (
    <div className="sv2-card set-footer">
      <span className="set-row-desc">
        Need your identity details instead?{" "}
        <button className="set-link-btn" onClick={onOpenProfile}>Open profile</button>
      </span>
      <button className="set-logout-btn" onClick={onLogout}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" />
        </svg>
        Logout
      </button>
    </div>
  );
}