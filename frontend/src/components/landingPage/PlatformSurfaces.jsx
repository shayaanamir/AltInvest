function IconChart() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 17l6-6 4 4 8-8" />
      <path d="M14 7h7v7" />
    </svg>
  );
}
function IconGauge() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 15a3 3 0 100-6 3 3 0 000 6z" />
      <path d="M12 15l4-4" />
      <path d="M4 19a9 9 0 1116 0" />
    </svg>
  );
}
function IconPie() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21.2 15.1A10 10 0 1112 2v10z" />
    </svg>
  );
}
function IconBell() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8a6 6 0 10-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.7 21a2 2 0 01-3.4 0" />
    </svg>
  );
}

// Marketing copy, not app data — same convention as the existing
// Features.jsx / PlatformPreview.jsx const arrays.
const SURFACES = [
  { icon: <IconChart />, title: "Market Outlook", desc: "Price, prediction and signal in one frame, so the forecast never lives in a different tab than the price." },
  { icon: <IconGauge />, title: "Market Sentiment", desc: "Every score comes with its evidence base — you always know whether a read is corroborated or thin." },
  { icon: <IconPie />, title: "Portfolio Analytics", desc: "Concentration, risk and sentiment exposure across crypto, NFTs and tokenized assets together." },
  { icon: <IconBell />, title: "Market Signals", desc: "Threshold alerts on price, AAI score, sentiment or risk — monitoring without staring at charts." },
];

export default function PlatformSurfaces() {
  return (
    <section className="lp2-section">
      <div className="lp2-section-inner">
        <div className="lp2-eyebrow">Platform</div>
        <h2 className="lp2-heading">Four surfaces that answer four different questions.</h2>
        <div className="lp2-surfaces-grid">
          {SURFACES.map((s) => (
            <div className="lp2-surface-card" key={s.title}>
              <div className="lp2-surface-icon">{s.icon}</div>
              <div className="lp2-surface-title">{s.title}</div>
              <p className="lp2-surface-desc">{s.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}