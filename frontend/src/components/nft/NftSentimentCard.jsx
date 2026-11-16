import { useAsync } from "../../hooks/useAsync";
import { nftApi } from "../../services/nftApi";
import { NFT_MARKET_SLUG, formatScore } from "../../utils/nftSentiment";
import { ErrorState } from "../../errors";

// NFT news sentiment (sentiment_engine/nft_sentiment): an LLM reads the collection's news, rewordings of one
// story count once, and recent floor and sales momentum is blended in. Refreshed every 30 minutes.

function MoodBadge({ mood }) {
  if (!mood) return null;
  return <span className={`nft-mood-badge ${mood.toLowerCase()}`}>{mood}</span>;
}

function Headline({ h }) {
  const title = h.link
    ? <a href={h.link} target="_blank" rel="noopener noreferrer">{h.title}</a>
    : h.title;
  return (
    <li className="nft-sent-headline">
      <span className={`nft-sent-dot ${h.label}`} title={h.label} aria-label={h.label} />
      <div>
        <div className="nft-sent-title">{title}</div>
        <div className="sv2-mute2 sv2-tiny">
          {[h.source, h.age, h.moreOutlets ? `+${h.moreOutlets} more outlet${h.moreOutlets > 1 ? "s" : ""}` : ""]
            .filter(Boolean).join(" · ")}
        </div>
        {h.reason && <div className="nft-sent-reason">{h.reason}</div>}
      </div>
    </li>
  );
}

export default function NftSentimentCard({ slug }) {
  const { data, loading, error, refetch } = useAsync(
    () => Promise.all([nftApi.getSentiment(slug), nftApi.getSentiment(NFT_MARKET_SLUG).catch(() => null)]),
    [slug]);
  const [s, market] = data || [];

  return (
    <div className="sv2-card adt-panel-card nft-sent-card">
      <div className="adt-panel-label">News sentiment</div>
      {loading ? (
        <div className="sv2-muted sv2-small">Loading news sentiment…</div>
      ) : error ? (
        <ErrorState error={error} onRetry={refetch} variant="panel" title="Couldn't load news sentiment" />
      ) : !s ? (
        <div className="sv2-muted sv2-small">No news sentiment has been computed for this collection yet.</div>
      ) : (
        <>
          {s.hasReading ? (
            <div className="nft-sent-head">
              <div className="nft-big-number">
                {s.scoreLabel}<span className="nft-big-unit"> / 100</span> <MoodBadge mood={s.mood} />
              </div>
              <div className="adt-panel-sub">
                {s.coverageLine} · {s.confidenceLabel} confidence{s.trendText ? ` · ${s.trendText}` : ""}
              </div>
              <div className="nft-kv nft-sent-parts">
                <span>From the news</span><b>{formatScore(s.newsScore)}</b>
                {s.marketScore != null && (<><span>Floor and sales momentum</span><b>{formatScore(s.marketScore)}</b></>)}
                {market?.hasReading && (<><span>NFT market overall</span><b>{market.scoreLabel} <MoodBadge mood={market.mood} /></b></>)}
              </div>
            </div>
          ) : (
            <div className="sv2-muted sv2-small">
              No news about {s.name} in the last 7 days.
              {market?.hasReading ? ` NFT market overall: ${market.scoreLabel} (${market.mood}).` : ""}
            </div>
          )}

          {s.headlines.length > 0 && (
            <>
              <div className="nft-sent-subhead">Stories that moved it most</div>
              <ul className="nft-sent-headlines">{s.headlines.map((h) => <Headline key={h.title} h={h} />)}</ul>
            </>
          )}

          <div className="nft-note">
            {s.stale && <span className="nft-stale-text">Not refreshed for a few hours. </span>}
            {s.validationNote}{" "}
            {s.scorer ? `Scored by ${s.scorer}.` : ""}
            {s.usedFallback ? " The LLM was unavailable for part of this reading." : ""}
            {s.lastUpdated ? ` Updated ${s.lastUpdated.replace("T", " ").replace("Z", " UTC")}.` : ""}
          </div>
        </>
      )}
    </div>
  );
}
