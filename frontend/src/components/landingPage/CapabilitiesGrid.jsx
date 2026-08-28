function IconBars() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <line x1="6" y1="20" x2="6" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="18" y1="20" x2="18" y2="14" />
    </svg>
  );
}
function IconShield() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2l8 4v6c0 5-3.4 8.7-8 10-4.6-1.3-8-5-8-10V6z" /><path d="M9 12l2 2 4-4" />
    </svg>
  );
}
function IconSparkle() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" stroke="none">
      <path d="M12 2c.8 4.6 3.4 7.2 8 8-4.6.8-7.2 3.4-8 8-.8-4.6-3.4-7.2-8-8 4.6-.8 7.2-3.4 8-8z" />
    </svg>
  );
}
function IconCompass() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" /><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
    </svg>
  );
}
function IconWallet() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 7a2 2 0 012-2h13a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2z" /><path d="M16 12h.01" /><path d="M3 9h18" />
    </svg>
  );
}
function IconGaugeSmall() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19a9 9 0 1116 0" /><path d="M12 15l3-4" />
    </svg>
  );
}

const CAPABILITIES = [
  { icon: <IconBars />, title: "Asset Analytics", desc: "Statistics, history and AI prediction per asset." },
  { icon: <IconShield />, title: "Risk Analytics", desc: "Volatility, liquidity, regulatory and market risk." },
  { icon: <IconSparkle />, title: "Alt-Asset Scoring", desc: "The AAI composite, with confidence attached." },
  { icon: <IconCompass />, title: "Market Discovery", desc: "Filter the universe by score, mood and volatility." },
  { icon: <IconWallet />, title: "Portfolio Optimizer", desc: "Plain-language rebalancing suggestions." },
  { icon: <IconGaugeSmall />, title: "Market Sentiment", desc: "Narrative themes and headline-level evidence." },
];

export default function CapabilitiesGrid() {
  return (
    <section className="lp2-section">
      <div className="lp2-section-inner">
        <div className="lp2-eyebrow">Capabilities</div>
        <h2 className="lp2-heading">Everything on one desk.</h2>
        <div className="lp2-cap-grid">
          {CAPABILITIES.map((c) => (
            <div className="lp2-cap-card" key={c.title}>
              <div className="lp2-cap-icon-badge">{c.icon}</div>
              <div className="lp2-surface-title">{c.title}</div>
              <p className="lp2-surface-desc">{c.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}