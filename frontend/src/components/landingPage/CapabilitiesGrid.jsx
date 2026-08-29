import { IconBars, IconShield, IconSparkle, IconCompass, IconWallet, IconGauge } from "../icons";

const CAPABILITIES = [
  { icon: <IconBars size={20} />, title: "Asset Analytics", desc: "Statistics, history and AI prediction per asset." },
  { icon: <IconShield size={20} withCheck />, title: "Risk Analytics", desc: "Volatility, liquidity, regulatory and market risk." },
  { icon: <IconSparkle size={20} variant="fourPoint" />, title: "Alt-Asset Scoring", desc: "The AAI composite, with confidence attached." },
  { icon: <IconCompass size={20} />, title: "Market Discovery", desc: "Filter the universe by score, mood and volatility." },
  { icon: <IconWallet size={20} />, title: "Portfolio Optimizer", desc: "Plain-language rebalancing suggestions." },
  { icon: <IconGauge size={20} small />, title: "Market Sentiment", desc: "Narrative themes and headline-level evidence." },
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