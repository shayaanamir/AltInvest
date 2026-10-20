export default function LandingFooter() {
  const year = new Date().getFullYear();

  return (
    <footer className="lp2-footer">
      <div className="lp2-footer-left">
        <div className="lp2-footer-brand">
          <div className="lp2-footer-logo">AI</div>
          <span className="lp2-footer-name">AltInvest</span>
        </div>
        <div className="lp2-footer-copy">© {year} AltInvest. Analysis, not advice.</div>
      </div>
      <div className="lp2-footer-links">

        {["Privacy", "Terms", "Contact"].map((label) => (
          <a key={label} href="#">{label}</a>
        ))}
      </div>
    </footer>
  );
}