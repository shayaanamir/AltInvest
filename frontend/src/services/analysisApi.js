import { portfolioApi } from "./portfolioApi";

/**
 * Portfolio analysis for the Dashboard's "AI analysis" and "Generate report".
 *
 * Everything here is arithmetic over values already stored for the signed-in user: their holdings
 * (value, cost basis) and the stored AAI score / signal / risk / sentiment of each asset they hold.
 * Nothing is predicted or invented, and no language model is involved.
 */

const CONCENTRATED_ABOVE_PCT = 50;

export async function loadPortfolioAnalysis() {
  const [crypto, nft, summary, intel] = await Promise.all([
    portfolioApi.getCryptoHoldings(),
    portfolioApi.getNftHoldings(),
    portfolioApi.getSummary(),
    portfolioApi.getIntelligence(),
  ]);

  const positions = [
    ...crypto.map((h) => ({
      kind: "crypto",
      name: h.name,
      label: h.symbol,
      valueUsd: h.valueUsd,
      costBasisUsd: h.costBasisUsd,
      aaiScore: h.aaiScore,
      action: h.aiAction,
    })),
    ...nft.map((h) => ({
      kind: "nft",
      name: h.collectionName,
      label: `${h.collectionName} #${h.tokenId}`,
      valueUsd: h.valueUsd,
      costBasisUsd: h.costBasisUsd,
      aaiScore: h.aaiScore ?? null,
      action: h.aiAction,
    })),
  ].sort((a, b) => b.valueUsd - a.valueUsd);

  const totalValue = positions.reduce((s, p) => s + p.valueUsd, 0);
  const withShare = positions.map((p) => ({ ...p, sharePct: totalValue > 0 ? (p.valueUsd / totalValue) * 100 : 0 }));

  const scored = withShare.filter((p) => p.aaiScore != null);
  const scoredValue = scored.reduce((s, p) => s + p.valueUsd, 0);
  const weightedAai = scoredValue > 0 ? scored.reduce((s, p) => s + p.aaiScore * p.valueUsd, 0) / scoredValue : null;
  const byScore = [...scored].sort((a, b) => b.aaiScore - a.aaiScore);

  return {
    empty: positions.length === 0,
    summary,
    intel,
    positions: withShare,
    totalValue,
    weightedAai,
    largest: withShare[0] || null,
    concentrated: !!withShare[0] && withShare[0].sharePct > CONCENTRATED_ABOVE_PCT,
    strongest: byScore[0] || null,
    weakest: byScore.length > 1 ? byScore[byScore.length - 1] : null,
    toReduce: withShare.filter((p) => p.action === "Reduce"),
    unscored: withShare.filter((p) => p.aaiScore == null),
  };
}
