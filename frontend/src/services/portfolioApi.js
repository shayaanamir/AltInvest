import portfolioData from "../data/sample_data/portfolio.json";

const SIM_DELAY = 400;

function delay(fn) {
  return new Promise((resolve) => setTimeout(() => resolve(fn()), SIM_DELAY));
}

function round2(n) {
  return Math.round(n * 100) / 100;
}

function computeTotals() {
  const { cryptoHoldings, nftHoldings } = portfolioData;
  const cryptoValue = cryptoHoldings.reduce((s, h) => s + h.valueUsd, 0);
  const nftValue = nftHoldings.reduce((s, h) => s + h.valueUsd, 0);
  const cryptoCost = cryptoHoldings.reduce((s, h) => s + h.costBasisUsd, 0);
  const nftCost = nftHoldings.reduce((s, h) => s + h.costBasisUsd, 0);

  const totalBalance = cryptoValue + nftValue;
  const totalCostBasis = cryptoCost + nftCost;
  const totalProfitLoss = totalBalance - totalCostBasis;
  const totalProfitLossPct = totalCostBasis > 0 ? (totalProfitLoss / totalCostBasis) * 100 : 0;
  const positionsCount = cryptoHoldings.length + nftHoldings.length;

  return { totalBalance, totalCostBasis, totalProfitLoss, totalProfitLossPct, positionsCount, cryptoValue, nftValue };
}

// Tallies each holding's AI action (crypto + NFT) into a signal-mix count,
// e.g. { Buy: 2, Hold: 2 } — driven entirely by the holdings' aiAction field.
function countSignals() {
  const holdings = [...portfolioData.cryptoHoldings, ...portfolioData.nftHoldings];
  const counts = {};
  holdings.forEach((h) => {
    const key = (h.aiAction || "Hold").replace(" More", "");
    counts[key] = (counts[key] || 0) + 1;
  });
  return counts;
}

export const portfolioApi = {
  getSummary: () =>
    delay(() => {
      const totals = computeTotals();
      const { summary } = portfolioData;
      return {
        totalBalance: round2(totals.totalBalance),
        totalCostBasis: round2(totals.totalCostBasis),
        totalProfitLoss: round2(totals.totalProfitLoss),
        totalProfitLossPct: round2(totals.totalProfitLossPct),
        totalProfitLossPositive: totals.totalProfitLoss >= 0,
        positionsCount: totals.positionsCount,
        diversificationScore: summary.diversificationScore,
        diversificationLabel: summary.diversificationLabel,
        needsRebalancing: summary.needsRebalancing,
        rebalanceNote: summary.needsRebalancing ? summary.rebalanceNote : summary.balancedNote,
      };
    }),

  getPerformanceHistory: (filter = "3M") =>
    delay(() => portfolioData.performanceHistory[filter] || []),

  getAllocation: () =>
    delay(() => {
      const totals = computeTotals();
      const total = totals.totalBalance || 1;
      const rows = [
        { label: "Crypto", valueUsd: totals.cryptoValue, pct: (totals.cryptoValue / total) * 100 },
        { label: "NFTs", valueUsd: totals.nftValue, pct: (totals.nftValue / total) * 100 },
      ];
      return rows.filter((r) => r.valueUsd > 0);
    }),

  getCryptoHoldings: () => delay(() => portfolioData.cryptoHoldings),

  getNftHoldings: () => delay(() => portfolioData.nftHoldings),

  getIntelligence: () =>
    delay(() => {
      const { portfolioIntelligence, summary } = portfolioData;
      return {
        aggregateRiskScore: portfolioIntelligence.aggregateRiskScore,
        sentimentExposure: portfolioIntelligence.sentimentExposure,
        signalMix: countSignals(),
        suggestions: portfolioIntelligence.rebalancingSuggestions,
        concentrated: summary.needsRebalancing,
      };
    }),
};