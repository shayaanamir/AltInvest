import { useMemo, useState } from "react";
import { formatAssetPrice, formatCurrencyAxis } from "../../utils/formatters";
import { CONE_DAYS } from "../../utils/volCone";
import {
  NFT_CONE_CAPTION, NFT_ETH_ONLY_CONE_NOTE, ethOnlyCone, floorPoints, floorStaleness, nftChartLayers, nftConeStartLabel,
} from "../../utils/nftCone";
import ConeChart from "../charts/ConeChart";

const RANGES = { "1M": 30, "3M": 90, "1Y": 365 };

const fmtEth = (v) => `${v >= 10 ? v.toFixed(2) : v >= 1 ? v.toFixed(3) : v.toFixed(4)} ETH`;
const fmtEthAxis = (v) => (v >= 10 ? v.toFixed(1) : v >= 1 ? v.toFixed(2) : v.toFixed(3));

const HIDDEN_TEXT = {
  "no volatility": "No volatility range: the floor volatility is not available.",
  "no risk data": "No volatility range: the floor volatility is not available.",
  "not an ML NFT value": "No volatility range: the floor volatility is not available.",
  "data stale": "No volatility range: the floor data is out of date.",
  illiquid: "No volatility range: too few sales in the last 7 days for the floor to be reliable.",
};

function Legend() {
  return (
    <div className="adt-legend">
      <span><span className="adt-legend-swatch solid" /> Daily floor</span>
      <span><span className="adt-legend-swatch band inner" /> 50% range</span>
      <span><span className="adt-legend-swatch band outer" /> 80% range</span>
    </div>
  );
}

// Daily floor history that continues into the illustrative 30-day volatility cone, in ETH only (D52 amended, D67
// revised). The USD view shows the USD history, with the ETH-only cone as a separate small chart below it.
export default function NftFloorCard({ history, risk, liquidityBadge }) {
  const [currency, setCurrency] = useState("ETH");
  const [range, setRange] = useState("3M");
  const usd = currency === "USD";

  const rows = useMemo(() => (history || []).slice(-(RANGES[range] + 1)), [history, range]);
  const points = useMemo(() => floorPoints(rows, currency), [rows, currency]);
  const { layers, cone } = useMemo(() => nftChartLayers(points, risk, currency), [points, risk, currency]);
  const eth = useMemo(() => (usd ? ethOnlyCone(history, risk) : null), [usd, history, risk]);
  const stale = useMemo(() => floorStaleness(history, rows), [history, rows]);
  const hidden = usd ? eth?.hidden : nftChartLayers(points, risk, "ETH").hidden;

  return (
    <div className="sv2-card adt-chart-card">
      <div className="adt-chart-head">
        <div>
          <div className="sv2-card-title nft-title-row">
            Floor price {liquidityBadge}
            {stale.stale && <span className="nft-liq-badge illiquid" data-role="floor-stale">Floor stale</span>}
          </div>
          {!usd && cone && <div className="adt-chart-sub">Shaded area: the next {CONE_DAYS} days' likely floor range from recent volatility</div>}
          {usd && <div className="adt-chart-sub">Floor in US dollars. The 30-day range below is in ETH.</div>}
          {hidden && hidden !== "usd view" && points.length >= 2 && <div className="adt-chart-sub">{HIDDEN_TEXT[hidden]}</div>}
          {stale.stale && (
            <div className="adt-chart-sub nft-stale-text">
              {stale.latestAgeDays != null
                ? `The latest OpenSea floor point is ${stale.latestAgeDays.toFixed(1)} days old.`
                : "The latest floor is missing."}
            </div>
          )}
          {stale.staleDaysInRange > 0 && (
            <div className="adt-chart-sub">{stale.staleDaysInRange} day{stale.staleDaysInRange > 1 ? "s" : ""} in this range had no OpenSea floor for more than 3 days; the line skips them.</div>
          )}
        </div>
        <div className="adt-chart-controls nft-chart-controls">
          <div className="sv2-segmented" role="group" aria-label="Currency">
            {["ETH", "USD"].map((c) => (
              <button key={c} className={currency === c ? "active" : ""} onClick={() => setCurrency(c)}>{c}</button>
            ))}
          </div>
          <div className="sv2-segmented" role="group" aria-label="Range">
            {Object.keys(RANGES).map((r) => (
              <button key={r} className={range === r ? "active" : ""} onClick={() => setRange(r)}>{r}</button>
            ))}
          </div>
        </div>
      </div>

      <ConeChart history={points} layers={layers} cone={cone}
        formatAxis={usd ? formatCurrencyAxis : fmtEthAxis} formatValue={usd ? formatAssetPrice : fmtEth}
        startText={nftConeStartLabel} emptyText="Not enough floor data yet." gradientId="nftFloorGrad" />

      {!usd && <div className="adt-chart-foot">{cone ? <Legend /> : <span />}</div>}
      {!usd && <div className="adt-chart-caption">{NFT_CONE_CAPTION}</div>}

      {usd && eth?.cone && (
        <div className="nft-eth-cone" data-role="eth-only-cone">
          <div className="adt-panel-label">Next {CONE_DAYS} days, in ETH</div>
          <ConeChart history={floorPoints(history, "ETH").slice(-31)} layers={eth.layers} cone={eth.cone}
            formatAxis={fmtEthAxis} formatValue={fmtEth} startText={nftConeStartLabel}
            emptyText="Not enough floor data yet." gradientId="nftEthConeGrad" />
          <div className="adt-chart-foot"><Legend /></div>
          <div className="adt-chart-caption">{NFT_CONE_CAPTION} {NFT_ETH_ONLY_CONE_NOTE}</div>
        </div>
      )}
    </div>
  );
}
