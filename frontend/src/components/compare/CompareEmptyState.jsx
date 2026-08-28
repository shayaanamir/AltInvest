import { IconColumns, IconPlus } from "./icons";

export default function CompareEmptyState({ onChooseAssets }) {
  return (
    <div className="cmp-card cmp-empty-outer">
      <div className="cmp-empty-inner">
        <div className="cmp-empty-icon">
          <IconColumns />
        </div>
        <h3 className="cmp-empty-title">Pick at least two assets</h3>
        <p className="cmp-empty-desc">
          Comparison works across categories: crypto against an NFT collection is fine, and shared
          dimensions are normalised so nothing is falsely equated.
        </p>
        <button className="cmp-choose-btn" onClick={onChooseAssets}>
          <IconPlus /> Choose assets
        </button>
      </div>
    </div>
  );
}