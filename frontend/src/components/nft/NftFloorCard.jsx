import { useMemo, useState } from "react";
import { formatAssetPrice, formatCurrencyAxis } from "../../utils/formatters";
import { CONE_DAYS } from "../../utils/volCone";
import { NFT_CONE_CAPTION, NFT_USD_CONE_NOTE, floorPoints, nftChartLayers, nftConeStartLabel } from "../../utils/nftCone";
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

// Daily floor history (ETH or USD) that continues into the illustrative 30-day volatility cone (D52 amended, D67).
export default function NftFloorCard({ history, risk, liquidityBadge }) {
  const [currency, setCurrency] = useState("ETH");
  const [range, setRange] = useState("3M");

  const points = useMemo(() => floorPoints(history, currency).slice(-(RANGES[range] + 1)), [history, currency, range]);
  const { layers, cone, hidden } = useMemo(() => nftChartLayers(points, risk), [points, risk]);
  const usd = currency === "USD";

  return (
    <div className="sv2-card adt-chart-card">
      <div className="adt-chart-head">
        <div>
          <div className="sv2-card-title nft-title-row">Floor price {liquidityBadge}</div>
          {cone
            ? <div className="adt-chart-sub">Shaded area: the next {CONE_DAYS} days' likely floor range from recent volatility</div>
            : hidden && points.length >= 2 && <div className="adt-chart-sub">{HIDDEN_TEXT[hidden]}</div>}
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

      <div className="adt-chart-foot">
        {cone ? (
          <div className="adt-legend">
            <span><span className="adt-legend-swatch solid" /> Daily floor</span>
            <span><span className="adt-legend-swatch band inner" /> 50% range</span>
            <span><span className="adt-legend-swatch band outer" /> 80% range</span>
          </div>
        ) : <span />}
      </div>
      <div className="adt-chart-caption">
        {NFT_CONE_CAPTION}{usd && cone ? ` ${NFT_USD_CONE_NOTE}` : ""}
      </div>
    </div>
  );
}
