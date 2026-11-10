// NFT collection floor chart: the same 30-day volatility cone as crypto (utils/volCone.js, D52), with the NFT hide
// rules of ml/docs/DECISIONS.md D52 (amended 2026-11-10) and D67. Pure functions, tested with `node --test`.
//
// The cone uses whichever floor volatility the ML service serves (EWMA if approved in step 10.3, otherwise the
// 30-day persistence vol). It is hidden when that volatility is missing or not positive, when the risk data is
// stale (ML 48 h or backend 36 h note), when the value is not from the ML NFT model, or when the collection is
// illiquid. It is NOT hidden just because EWMA was not approved.
import { CONE_DAYS, coneFromVol, shortDate } from "./volCone.js";

export const NFT_CONE_CAPTION = "Likely floor range based on recent volatility, not a price prediction.";
export const NFT_RISK_RELATIVE_NOTE =
  "This risk score is relative to the other NFT collections tracked here. It is not comparable to crypto risk scores.";
export const NFT_USD_CONE_NOTE =
  "In USD the range is the ETH range at the last ETH price; it does not include future ETH-USD moves.";

/** 'Last floor, 10 Nov' */
export function nftConeStartLabel(isoDate) {
  return `Last floor, ${shortDate(isoDate)}`;
}

/** Why the cone is hidden, or null when it may be drawn. `risk`: {volatility, note, modelVersion, isIlliquid}. */
export function nftConeHiddenReason(risk) {
  if (!risk) return "no risk data";
  const v = risk.volatility;
  if (typeof v !== "number" || !Number.isFinite(v) || v <= 0) return "no volatility";
  if (typeof risk.modelVersion !== "string" || !risk.modelVersion.startsWith("nft-")) return "not an ML NFT value";
  if (typeof risk.note === "string" && risk.note.toLowerCase().includes("data stale")) return "data stale";
  if (risk.isIlliquid === true) return "illiquid";
  return null;
}

/** Daily floor points {date, price} in the chosen currency ('ETH' or 'USD'), gap days left out, oldest first. */
export function floorPoints(history, currency) {
  const key = currency === "USD" ? "floor_usd" : "floor_eth";
  return (history || [])
    .filter((r) => typeof r[key] === "number" && r[key] > 0)
    .map((r) => ({ date: r.date, price: r[key] }));
}

/**
 * The layers the floor chart draws: "history" (at least 2 points), plus the two cone bands when allowed.
 * Never a forecast or center line. In USD the cone starts at the last USD floor; since the bands are
 * multiplicative this equals the ETH cone converted at the last date's ETH-USD (D67).
 */
export function nftChartLayers(points, risk) {
  if (!points || points.length < 2) return { layers: [], cone: null, hidden: "not enough floor history" };
  const hidden = nftConeHiddenReason(risk);
  const cone = hidden ? null : coneFromVol(points[points.length - 1], risk.volatility, CONE_DAYS);
  return { layers: cone ? ["history", "cone-outer", "cone-inner"] : ["history"], cone, hidden };
}
