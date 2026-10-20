import { formatCurrencyCompact } from "../../utils/formatters";
import { activeFilterCount } from "../../services/discoverApi";

function pct(value, min, max) {
  if (max === min) return 0;
  return ((value - min) / (max - min)) * 100;
}

function sliderFill(p) {
  return { background: `linear-gradient(90deg, var(--sv2-accent) ${p}%, var(--sv2-chip) ${p}%)` };
}

const SIGNAL_LABELS = { BUY: "Buy", HOLD: "Hold", SELL: "Sell" };

/**
 * Sliders come from the UI config; sort keys, subcategories and signals come from the backend
 * (GET /discover/options), with how many assets have each.
 */
export default function DiscoverFilters({ config, options, category, filters, onChange, onReset }) {
  if (!config) return null;
  const { marketCapRange, sentimentRange, aaiScoreRange, volatilityRange, riskRange } = config.filters;
  const set = (patch) => onChange({ ...filters, ...patch });
  const toggleIn = (key, value) =>
    set({ [key]: filters[key].includes(value) ? filters[key].filter((v) => v !== value) : [...filters[key], value] });

  const sentMin = sentimentRange.min * 100;
  const sentMax = sentimentRange.max * 100;
  const sentStep = sentimentRange.step * 100;
  const fmtCap = (v) => formatCurrencyCompact(v, { digits: 0 });
  const count = activeFilterCount(filters);
  const isCrypto = category === "crypto";

  const slider = (label, shown, key, min, max, step) => (
    <div className="disc-field">
      <div className="disc-field-label"><span>{label}</span><span>{shown}</span></div>
      <input
        type="range" className="disc-slider" aria-label={label}
        min={min} max={max} step={step} value={filters[key]}
        style={sliderFill(pct(filters[key], min, max))}
        onChange={(e) => set({ [key]: Number(e.target.value) })}
      />
    </div>
  );

  return (
    <div className="disc-filters-card">
      <div className="disc-filters-head">
        <h3>Filters</h3>
        <button className="disc-reset-btn" onClick={onReset} disabled={count === 0}>
          Reset{count ? ` (${count})` : ""}
        </button>
      </div>

      <div className="disc-field">
        <div className="disc-field-label"><span>Sort by</span></div>
        <div className="disc-sort-row">
          <select className="disc-select" value={filters.sort} onChange={(e) => set({ sort: e.target.value })} aria-label="Sort by">
            {(options?.sorts || [{ key: filters.sort, label: filters.sort }]).map((o) => (
              <option key={o.key} value={o.key}>{o.label}</option>
            ))}
          </select>
          <button
            type="button"
            className="disc-order-btn"
            onClick={() => set({ order: filters.order === "desc" ? "asc" : "desc" })}
            title={filters.order === "desc" ? "Highest first" : "Lowest first"}
            aria-label={`Order: ${filters.order === "desc" ? "highest first" : "lowest first"}`}
          >
            {filters.order === "desc" ? "↓" : "↑"}
          </button>
        </div>
      </div>

      {options?.signals?.length > 0 && (
        <div className="disc-field">
          <div className="disc-field-label"><span>AAI signal</span></div>
          <div className="disc-chip-row">
            {options.signals.map((s) => (
              <button
                key={s.value} type="button"
                className={`disc-chip signal-${s.value.toLowerCase()} ${filters.signals.includes(s.value) ? "active" : ""}`}
                onClick={() => toggleIn("signals", s.value)}
                aria-pressed={filters.signals.includes(s.value)}
              >
                {SIGNAL_LABELS[s.value] || s.value} <span className="disc-chip-count">{s.count}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {options?.subcategories?.length > 0 && (
        <div className="disc-field">
          <div className="disc-field-label"><span>Category</span></div>
          <div className="disc-chip-row">
            {options.subcategories.map((s) => (
              <button
                key={s.value} type="button"
                className={`disc-chip ${filters.subcategories.includes(s.value) ? "active" : ""}`}
                onClick={() => toggleIn("subcategories", s.value)}
                aria-pressed={filters.subcategories.includes(s.value)}
              >
                {s.value} <span className="disc-chip-count">{s.count}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {slider("Min AAI score", filters.minAai, "minAai", aaiScoreRange.min, aaiScoreRange.max, aaiScoreRange.step)}
      {isCrypto && slider("Min sentiment", (filters.minSentiment / 100).toFixed(2), "minSentiment", sentMin, sentMax, sentStep)}
      {isCrypto && slider("Max risk score", filters.maxRisk, "maxRisk", riskRange.min, riskRange.max, riskRange.step)}
      {slider(isCrypto ? "Max volatility" : "Max illiquidity risk", filters.maxVolatility, "maxVolatility", volatilityRange.min, volatilityRange.max, volatilityRange.step)}
      {slider("Min market cap", fmtCap(filters.minMarketCap), "minMarketCap", marketCapRange.min, marketCapRange.max, marketCapRange.step)}

      <div className="disc-field disc-toggles" style={{ marginBottom: 0 }}>
        <label><input type="checkbox" checked={filters.heldOnly} onChange={(e) => set({ heldOnly: e.target.checked })} /> Only what I hold</label>
        <label><input type="checkbox" checked={filters.watchingOnly} onChange={(e) => set({ watchingOnly: e.target.checked })} /> Only what I watch</label>
        {!isCrypto && options?.has_verified && (
          <label><input type="checkbox" checked={filters.verifiedOnly} onChange={(e) => set({ verifiedOnly: e.target.checked })} /> Verified collections only</label>
        )}
      </div>
    </div>
  );
}
