export default function WhatsDrivingIt({ detail, colors }) {
  return (
    <div className="sv2-card sv2-card-pad-sm">
      <div className="sv2-card-title" style={{ marginBottom: 4 }}>What's driving it</div>
      <div className="sv2-mt-8">
        {detail.drivingFactors.map((f, i) => (
          <div key={i} className="sv2-driving-item">
            <span className={`sv2-driving-icon ${f.direction}`}>{f.direction === "up" ? "↑" : "↓"}</span>
            <div>
              <div className="sv2-driving-title">{f.title}</div>
              <div className="sv2-driving-desc">{f.description}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="sv2-tiny sv2-mute2 sv2-mt-12">
        Of {detail.articleCount} signals we read: {detail.distribution.positive}% positive, {detail.distribution.neutral}% neutral, {detail.distribution.negative}% negative
      </div>
      <div className="sv2-dist-bar">
        <div style={{ width: `${detail.distribution.positive}%`, background: colors.green }} />
        <div style={{ width: `${detail.distribution.neutral}%`, background: colors.border }} />
        <div style={{ width: `${detail.distribution.negative}%`, background: colors.red }} />
      </div>
    </div>
  );
}