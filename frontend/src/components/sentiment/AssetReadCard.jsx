export default function AssetReadCard({ detail, colors }) {
  const scoreColor = detail.score >= 58 ? colors.green : detail.score >= 45 ? colors.accent : colors.red;

  return (
    <div className="sv2-card sv2-card-pad">
      <div className="sv2-card-title" style={{ marginBottom: 16 }}>The read</div>

      <div className="sv2-score-display">
        <div>
          <div className="sv2-score-big" style={{ color: scoreColor }}>{detail.score}</div>
          <div className="sv2-bold" style={{ fontSize: 15, color: scoreColor }}>{detail.label}</div>
          <div className="sv2-score-of100">out of 100</div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div className="sv2-tiny sv2-mute2">Confidence</div>
          <div>
            <span className="sv2-confidence-value">{detail.confidencePct}%</span>
            <span className="sv2-confidence-tag" style={{ color: colors.textSoft }}>{detail.confidenceLabel}</span>
          </div>
          <div className="sv2-progress" style={{ width: 140, marginTop: 6 }}>
            <div className="sv2-progress-fill" style={{ width: `${detail.confidencePct}%`, background: colors.green }} />
          </div>
          <div className="sv2-tiny sv2-mute2 sv2-mt-4">Well corroborated across independent sources.</div>
        </div>
      </div>

      <div className="sv2-progress sv2-mt-16">
        <div className="sv2-progress-fill" style={{ width: `${detail.score}%`, background: scoreColor }} />
      </div>

      <p className="sv2-narrative">{detail.narrative}</p>
      <div className="sv2-footnote">This is a sentiment read only — not the full AltInvest score, and not advice.</div>
    </div>
  );
}