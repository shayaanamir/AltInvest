import { IconChart, IconGauge, IconPie, IconBell } from "../icons";

// Marketing copy, not app data — same convention as the existing
// Features.jsx / PlatformPreview.jsx const arrays.
const SURFACES = [
  { icon: <IconChart size={22} />, title: "Market Outlook", desc: "Price, prediction and signal in one frame, so the forecast never lives in a different tab than the price." },
  { icon: <IconGauge size={22} />, title: "Market Sentiment", desc: "Every score comes with its evidence base — you always know whether a read is corroborated or thin." },
  { icon: <IconPie size={22} />, title: "Portfolio Analytics", desc: "Concentration, risk and sentiment exposure across crypto, NFTs and tokenized assets together." },
  { icon: <IconBell size={22} />, title: "Market Signals", desc: "Threshold alerts on price, AAI score, sentiment or risk — monitoring without staring at charts." },
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