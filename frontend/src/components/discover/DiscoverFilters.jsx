function pct(value, min, max) {
  if (max === min) return 0;
  return ((value - min) / (max - min)) * 100;
}

function sliderFill(p) {
  return { background: `linear-gradient(90deg, var(--sv2-accent) ${p}%, var(--sv2-chip) ${p}%)` };
}

export default function DiscoverFilters({ config, filters, onChange, onReset }) {
  if (!config) return null;
  const { marketCapRange, sentimentRange, aaiScoreRange, volatilityRange } = config.filters;

  const sentMin = sentimentRange.min * 100;
  const sentMax = sentimentRange.max * 100;
  const sentStep = sentimentRange.step * 100;

  const fmtCap = (v) => `$${(v / 1e9).toFixed(0)}B`;

  return (
    <div className="disc-filters-card">
      <div className="disc-filters-head">
        <h3>Filters</h3>
        <button className="disc-reset-btn" onClick={onReset}>Reset</button>
      </div>

      <div className="disc-field">
        <div className="disc-field-label"><span>Min AAI score</span><span>{filters.minAai}</span></div>
        <input
          type="range" className="disc-slider"
          min={aaiScoreRange.min} max={aaiScoreRange.max} step={aaiScoreRange.step}
          value={filters.minAai}
          style={sliderFill(pct(filters.minAai, aaiScoreRange.min, aaiScoreRange.max))}
          onChange={(e) => onChange({ ...filters, minAai: Number(e.target.value) })}
        />
      </div>

      <div className="disc-field">
        <div className="disc-field-label"><span>Min sentiment</span><span>{filters.minSentiment}</span></div>
        <input
          type="range" className="disc-slider"
          min={sentMin} max={sentMax} step={sentStep}
          value={filters.minSentiment}
          style={sliderFill(pct(filters.minSentiment, sentMin, sentMax))}
          onChange={(e) => onChange({ ...filters, minSentiment: Number(e.target.value) })}
        />
      </div>

      <div className="disc-field">
        <div className="disc-field-label"><span>Max volatility</span><span>{filters.maxVolatility}</span></div>
        <input
          type="range" className="disc-slider"
          min={volatilityRange.min} max={volatilityRange.max} step={volatilityRange.step}
          value={filters.maxVolatility}
          style={sliderFill(pct(filters.maxVolatility, volatilityRange.min, volatilityRange.max))}
          onChange={(e) => onChange({ ...filters, maxVolatility: Number(e.target.value) })}
        />
      </div>

      <div className="disc-field">
        <div className="disc-field-label"><span>Min market cap</span><span>{fmtCap(filters.minMarketCap)}</span></div>
        <input
          type="range" className="disc-slider"
          min={marketCapRange.min} max={marketCapRange.max} step={marketCapRange.step}
          value={filters.minMarketCap}
          style={sliderFill(pct(filters.minMarketCap, marketCapRange.min, marketCapRange.max))}
          onChange={(e) => onChange({ ...filters, minMarketCap: Number(e.target.value) })}
        />
      </div>

      <div className="disc-field" style={{ marginBottom: 0 }}>
        <div className="disc-field-label"><span>Sort by</span></div>
        <select
          className="disc-select"
          value={filters.sortBy}
          onChange={(e) => onChange({ ...filters, sortBy: e.target.value })}
        >
          {config.sortOptions.map((opt) => (
            <option key={opt.key} value={opt.key}>{opt.label}</option>
          ))}
        </select>
      </div>
    </div>
  );
}