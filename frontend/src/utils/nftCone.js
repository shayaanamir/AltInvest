// NFT collection floor chart: the same 30-day volatility cone as crypto (utils/volCone.js, D52), with the NFT hide
// rules of ml/docs/DECISIONS.md D52 (amended 2026-11-10) and D67 (revised 2026-11-11). Pure functions, tested with
// `node --test`.
//
// The cone uses whichever floor volatility the ML service serves (today persistence vol_30d, D73). It is hidden
// when that volatility is missing or not positive, when the risk data is stale (ML 48 h or backend 36 h note), when
// the value is not from the ML NFT service, or when the collection is illiquid. The served volatility is of the ETH
// floor, so the cone is only ever drawn in ETH: the USD view shows the USD history and a separate ETH-only cone.
import { CONE_DAYS, coneFromVol, shortDate } from "./volCone.js";

export const NFT_CONE_CAPTION = "Likely floor range based on recent volatility, not a price prediction.";
export const NFT_RISK_RELATIVE_NOTE =
  "This risk score is relative to the other NFT collections tracked here. It is not comparable to crypto risk scores.";
export const NFT_ETH_ONLY_CONE_NOTE = "This range is in ETH. ETH price moves are not included.";
export const STALE_POINT_HOURS = 72; // D67h: a floor point more than 3 days old
export const ETH_CONE_HISTORY_DAYS = 30;

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
 * The layers the main floor chart draws: "history" (at least 2 points), plus the two cone bands only in the ETH
 * view. Never a forecast or center line, and never a cone in USD (D67 revised).
 */
export function nftChartLayers(points, risk, currency = "ETH") {
  if (!points || points.length < 2) return { layers: [], cone: null, hidden: "not enough floor history" };
  if (currency !== "ETH") return { layers: ["history"], cone: null, hidden: "usd view" };
  const hidden = nftConeHiddenReason(risk);
  const cone = hidden ? null : coneFromVol(points[points.length - 1], risk.volatility, CONE_DAYS);
  return { layers: cone ? ["history", "cone-outer", "cone-inner"] : ["history"], cone, hidden };
}

/** The separate ETH-only cone shown in the USD view: the last 30 days of the ETH floor and its cone. */
export function ethOnlyCone(history, risk) {
  return nftChartLayers(floorPoints(history, "ETH").slice(-(ETH_CONE_HISTORY_DAYS + 1)), risk, "ETH");
}

/**
 * D67h: {stale, latestAgeDays, staleDaysInRange}. Stale when the newest row's OpenSea point is more than 3 days old
 * or the newest floor is missing. staleDaysInRange counts rows of `rows` whose point was more than 3 days old.
 */
export function floorStaleness(history, rows = history) {
  const last = (history || [])[history?.length - 1];
  if (!last) return { stale: false, latestAgeDays: null, staleDaysInRange: 0 };
  const age = typeof last.floor_age_hours === "number" ? last.floor_age_hours : null;
  const stale = (age != null && age > STALE_POINT_HOURS) || !(typeof last.floor_eth === "number" && last.floor_eth > 0);
  const staleDaysInRange = (rows || []).filter((r) => typeof r.floor_age_hours === "number" && r.floor_age_hours > STALE_POINT_HOURS).length;
  return { stale, latestAgeDays: age == null ? null : age / 24, staleDaysInRange };
}
