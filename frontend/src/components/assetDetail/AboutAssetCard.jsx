import { deriveAaiSignal } from "../../services/assetDetailApi";

export default function AboutAssetCard({ name, about, aaiScore }) {
  if (!about) return null;
  const signal = deriveAaiSignal(aaiScore);

  return (
    <div className="sv2-card adt-about-card">
      <div className="sv2-card-title adt-mb-10">About {name}</div>
      <p className="adt-about-text">{about}</p>
      <div className="adt-about-tags">
        <span className="adt-tag-pill">AAI {Math.round(aaiScore ?? 0)}</span>
        <span className={`adt-tag-pill ${signal.tone}`}>{signal.label.replace("Strong ", "")}</span>
      </div>
    </div>
  );
}