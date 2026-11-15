import { useState, useMemo } from "react";
import { deriveAaiSignal } from "../../services/assetDetailApi";
import { formatCurrencyAxis, formatAssetPrice } from "../../utils/formatters";
import { CONE_CAPTION, CONE_DAYS, chartLayers, coneStartLabel } from "../../utils/volCone";
import { PAST_RANGES_CAPTION, PAST_RANGES_TOGGLE_LABEL, calibration, calibrationText, pastBandsForWindow } from "../../utils/pastRanges";
import ConeChart from "../charts/ConeChart";

const FILTERS = ["1D", "1W", "1M", "3M", "1Y"];

// priceHistory is one point per day, oldest first.
const FILTER_DAYS = { "1D": 1, "1W": 7, "1M": 30, "3M": 90, "1Y": 365 };

function sliceForFilter(arr, filter) {
  if (!arr) return arr;
  return arr.slice(-(FILTER_DAYS[filter] + 1));
}

// History line, then (when the served volatility allows it, D82) an illustrative 30-day volatility cone (D52).
// There is no forecast or center line: no price model is approved, and lower/upper bounds stay null.
// Phase 11 (D87-D89): behind the line, the range the cone would have shown 30 days earlier for each day (toggle,
// default on), and a descriptive calibration line over the visible window (60 days or more).
export default function PricePerformanceCard({ priceHistory, risk, aaiPanel, pastRanges }) {
  const [filter, setFilter] = useState("1M");
  const [showPast, setShowPast] = useState(true);

  const history = useMemo(() => sliceForFilter(priceHistory, filter), [priceHistory, filter]);
  const { layers, cone } = useMemo(() => chartLayers(history, risk), [history, risk]);
  const allPastBands = useMemo(() => pastBandsForWindow(pastRanges, history), [pastRanges, history]);
  const hasPast = allPastBands.length >= 2;
  const pastBands = hasPast && showPast ? allPastBands : [];
  const calibrationLine = pastBands.length ? calibrationText(calibration(pastBands)) : null;

  const signal = aaiPanel ? deriveAaiSignal(aaiPanel.score) : null;

  return (
    <div className="sv2-card adt-chart-card">
      <div className="adt-chart-head">
        <div>
          <div className="sv2-card-title">Price performance</div>
          {cone && <div className="adt-chart-sub">Shaded area: the next {CONE_DAYS} days' likely range from recent volatility</div>}
        </div>
        <div className="adt-chart-controls">
          {hasPast && (
            <label className="adt-past-toggle">
              <input type="checkbox" checked={showPast} onChange={(e) => setShowPast(e.target.checked)} />
              {PAST_RANGES_TOGGLE_LABEL}
            </label>
          )}
          <div className="sv2-segmented">
            {FILTERS.map((f) => (
              <button key={f} className={filter === f ? "active" : ""} onClick={() => setFilter(f)}>{f}</button>
            ))}
          </div>
        </div>
      </div>

      <ConeChart history={history} layers={layers} cone={cone} formatAxis={formatCurrencyAxis}
        formatValue={formatAssetPrice} startText={coneStartLabel} emptyText="Not enough price data yet."
        gradientId="adtPriceGrad" pastBands={pastBands} />

      <div className="adt-chart-foot">
        {cone || pastBands.length ? (
          <div className="adt-legend">
            <span><span className="adt-legend-swatch solid" /> Actual</span>
            {cone && <span><span className="adt-legend-swatch band inner" /> 50% range</span>}
            {cone && <span><span className="adt-legend-swatch band outer" /> 80% range</span>}
            {pastBands.length > 0 && <span><span className="adt-legend-swatch band past" /> Past 50% / 80% ranges</span>}
          </div>
        ) : <span />}
        {signal && (
          <div className="adt-signal-badge">
            {/* A composite rating of the asset, not a price forecast; the chart above says it is not a prediction. */}
            AAI rating (composite score)
            <span className={`adt-signal-pill ${signal.tone}`}>{signal.label.replace("Strong ", "")}</span>
            {aaiPanel?.confidence != null && (
              <span className="adt-signal-conf">{Math.round(aaiPanel.confidence * 100)}% confidence</span>
            )}
          </div>
        )}
      </div>
      <div className="adt-chart-caption">{CONE_CAPTION}</div>
      {pastBands.length > 0 && <div className="adt-chart-caption" data-role="past-caption">{PAST_RANGES_CAPTION}</div>}
      {calibrationLine && <div className="adt-chart-caption adt-calibration" data-role="past-calibration">{calibrationLine}</div>}
    </div>
  );
}
