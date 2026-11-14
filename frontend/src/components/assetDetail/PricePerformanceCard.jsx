import { useState, useMemo } from "react";
import { deriveAaiSignal } from "../../services/assetDetailApi";
import { formatCurrencyAxis, formatAssetPrice } from "../../utils/formatters";
import { CONE_CAPTION, CONE_DAYS, chartLayers, coneStartLabel } from "../../utils/volCone";
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
export default function PricePerformanceCard({ priceHistory, risk, aaiPanel }) {
  const [filter, setFilter] = useState("1M");

  const history = useMemo(() => sliceForFilter(priceHistory, filter), [priceHistory, filter]);
  const { layers, cone } = useMemo(() => chartLayers(history, risk), [history, risk]);

  const signal = aaiPanel ? deriveAaiSignal(aaiPanel.score) : null;

  return (
    <div className="sv2-card adt-chart-card">
      <div className="adt-chart-head">
        <div>
          <div className="sv2-card-title">Price performance</div>
          {cone && <div className="adt-chart-sub">Shaded area: the next {CONE_DAYS} days' likely range from recent volatility</div>}
        </div>
        <div className="adt-chart-controls">
          <div className="sv2-segmented">
            {FILTERS.map((f) => (
              <button key={f} className={filter === f ? "active" : ""} onClick={() => setFilter(f)}>{f}</button>
            ))}
          </div>
        </div>
      </div>

      <ConeChart history={history} layers={layers} cone={cone} formatAxis={formatCurrencyAxis}
        formatValue={formatAssetPrice} startText={coneStartLabel} emptyText="Not enough price data yet."
        gradientId="adtPriceGrad" />

      <div className="adt-chart-foot">
        {cone ? (
          <div className="adt-legend">
            <span><span className="adt-legend-swatch solid" /> Actual</span>
            <span><span className="adt-legend-swatch band inner" /> 50% range</span>
            <span><span className="adt-legend-swatch band outer" /> 80% range</span>
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
    </div>
  );
}
