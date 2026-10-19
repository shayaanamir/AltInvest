import { useAsync } from "../../hooks/useAsync";
import { dashboardApi } from "../../services/dashboardApi";
import { formatCurrencyCompact, formatCurrencyFull } from "../../utils/formatters";
import MiniMoodGauge from "./MiniMoodGauge";
import { ErrorState } from "../../errors";

export default function DashboardStatCards() {
  const { data: stats, error, refetch } = useAsync(() => dashboardApi.getMarketStats(), []);

  if (error) {
    return (
      <div className="dv2-stats-grid">
        <div className="sv2-card dv2-stat-card" style={{ gridColumn: "1 / -1" }}>
          <ErrorState error={error} onRetry={refetch} title="Couldn't load market stats" />
        </div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="dv2-stats-grid">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="sv2-card dv2-stat-card sv2-muted sv2-small">Loading…</div>
        ))}
      </div>
    );
  }

  const moodLabel = stats.marketMood
    ? stats.marketMood[0].toUpperCase() + stats.marketMood.slice(1)
    : "Neutral";
  const moodColor =
    stats.marketMood === "bullish" ? "var(--sv2-green)" :
    stats.marketMood === "bearish" ? "var(--sv2-red)" : "var(--sv2-text)";

  return (
    <div className="dv2-stats-grid">
      <div className="sv2-card dv2-stat-card">
        <div className="dv2-stat-label">Portfolio Value</div>
        <div className="dv2-stat-value">{formatCurrencyFull(stats.totalPortfolioValue)}</div>
        <div className="dv2-stat-sub">
          {stats.holdingsCount > 0
            ? `${stats.holdingsCount} holding${stats.holdingsCount === 1 ? "" : "s"} tracked`
            : "No holdings yet"}
        </div>
      </div>

      <div className="sv2-card dv2-stat-card">
        <div className="dv2-stat-label">Market Volume · 24H</div>
        <div className="dv2-stat-value">{formatCurrencyCompact(stats.totalVolume24h)}</div>
        <div className="dv2-stat-sub">
          Across {stats.assetsCount} tracked assets and {stats.collectionsCount} collections
        </div>
      </div>

      <div className="sv2-card dv2-stat-card">
        <div className="dv2-stat-label">Global AAI Sentiment</div>
        <div className="dv2-stat-value-row">
          <span className="dv2-stat-value">{stats.globalSentiment}</span>
          <span className="dv2-stat-value-unit">/ 100</span>
        </div>
        <div className="dv2-stat-sub">
          Composite of {stats.cryptoScoreCount} crypto and {stats.nftScoreCount} NFT scores
        </div>
      </div>

      <div className="sv2-card dv2-stat-card">
        <div className="dv2-stat-mood-row">
          <div>
            <div className="dv2-stat-label">Market Mood</div>
            <div className="dv2-stat-value" style={{ fontSize: 22, color: moodColor }}>{moodLabel}</div>
          </div>
          <MiniMoodGauge score={stats.globalSentiment} />
        </div>
        <div className="dv2-stat-sub">
          {stats.marketMoodConfidence != null ? `${stats.marketMoodConfidence}% AI confidence` : "No sentiment readings yet"}
        </div>
      </div>
    </div>
  );
}