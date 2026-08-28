export default function SettingsRow({ title, description, children }) {
  return (
    <div className="set-row">
      <div className="set-row-text">
        <div className="set-row-title">{title}</div>
        {description && <div className="set-row-desc">{description}</div>}
      </div>
      <div className="set-row-control">{children}</div>
    </div>
  );
}