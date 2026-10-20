export default function PageHeader({ title, subtitle, children, className = "" }) {
  return (
    <div className={`sv2-page-header ${className}`}>
      <div>
        <h1 className="sv2-page-title">{title}</h1>
        {subtitle && <p className="sv2-page-sub">{subtitle}</p>}
      </div>
      {children && <div className="sv2-page-actions">{children}</div>}
    </div>
  );
}

