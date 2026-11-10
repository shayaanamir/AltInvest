import { useSearchParams, useNavigate } from "react-router-dom";
import "../styles/assetDetail.css";
import "../styles/nftCollection.css";
import { useAsync } from "../hooks/useAsync";
import { nftApi } from "../services/nftApi";
import { formatAssetPrice, formatPct } from "../utils/formatters";
import { NFT_RISK_RELATIVE_NOTE } from "../utils/nftCone";
import NftFloorCard from "../components/nft/NftFloorCard";
import { IconArrowLeft } from "../components/icons";
import { ErrorState, ErrorBoundary } from "../errors";

const eth = (v, d = 4) => (typeof v === "number" ? `${v.toFixed(d)} ETH` : "—");
const num = (v) => (typeof v === "number" ? Math.round(v).toLocaleString() : "—");

function LiquidityBadge({ liquidity }) {
  if (!liquidity?.label) return null;
  return <span className={`nft-liq-badge ${liquidity.label.toLowerCase()}`} title={liquidity.marketplaces}>Liquidity: {liquidity.label}</span>;
}

function RiskCard({ risk }) {
  return (
    <div className="sv2-card adt-panel-card">
      <div className="adt-panel-label">Floor risk score</div>
      {risk.riskScore == null ? (
        <div className="sv2-muted sv2-small">No risk score stored for this collection yet.</div>
      ) : (
        <>
          <div className="nft-big-number">{risk.riskScore.toFixed(0)}<span className="nft-big-unit"> / 100</span></div>
          <div className="adt-panel-sub">Higher = calmer floor. Annualised floor volatility {formatPct(risk.volatility * 100)}.</div>
        </>
      )}
      <div className="nft-note">{NFT_RISK_RELATIVE_NOTE}</div>
    </div>
  );
}

function LiquidityCard({ liquidity }) {
  if (!liquidity) {
    return (
      <div className="sv2-card adt-panel-card">
        <div className="adt-panel-label">Liquidity</div>
        <div className="sv2-muted sv2-small">No liquidity data stored for this collection yet.</div>
      </div>
    );
  }
  return (
    <div className="sv2-card adt-panel-card">
      <div className="adt-panel-label">Liquidity</div>
      <div className="nft-big-number">{typeof liquidity.score === "number" ? liquidity.score.toFixed(0) : "—"}
        <span className="nft-big-unit"> / 100</span> <LiquidityBadge liquidity={liquidity} /></div>
      <div className="nft-kv">
        <span>Sales, last 7 days</span><b>{num(liquidity.sales7d)}</b>
        <span>Sales, last 30 days</span><b>{num(liquidity.sales30d)}</b>
        <span>Volume, last 30 days</span><b>{eth(liquidity.volume30dEth, 1)}</b>
        <span>Removed as wash trades (30 days)</span>
        <b>{typeof liquidity.washShare30d === "number" ? formatPct(liquidity.washShare30d * 100) : "—"}</b>
      </div>
      <div className="nft-note">{liquidity.marketplaces}. Ranked against the other tracked collections; under 10 sales in 7 days counts as illiquid.</div>
    </div>
  );
}

function SalesCard({ sales }) {
  return (
    <div className="sv2-card adt-panel-card">
      <div className="adt-panel-label">Recent sales</div>
      {sales.length === 0 ? (
        <div className="sv2-muted sv2-small">No sales stored yet.</div>
      ) : (
        <div className="nft-sales">
          {sales.slice(0, 6).map((s) => (
            <div key={`${s.tokenId}-${s.timestamp}`} className="nft-sale-row">
              <span>#{s.tokenId}</span>
              <span className="sv2-mute2">{(s.timestamp || "").slice(0, 10)} · {s.marketplace}</span>
              <b>{eth(s.priceEth, 3)}</b>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function NftCollectionPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const slug = searchParams.get("slug");
  const { data: c, loading, error, refetch } = useAsync(
    () => (slug ? nftApi.getCollection(slug) : Promise.resolve(null)), [slug]);
  const back = () => navigate(-1);

  return (
    <div className="sv2">
      <div className="sv2-page adt-page">
        <button className="adt-back-btn" onClick={back}><IconArrowLeft size={15} /> Back</button>
        {loading ? (
          <div className="sv2-muted sv2-small">Loading collection…</div>
        ) : error ? (
          <div className="sv2-card sv2-card-pad">
            <ErrorState error={error} onRetry={refetch} variant="panel" title={`Couldn't load ${slug}`} />
          </div>
        ) : !c ? (
          <div className="sv2-muted sv2-small">{slug ? `No NFT collection "${slug}" is tracked.` : "No collection selected."}</div>
        ) : (
          <>
            <div className="sv2-card adt-header-card">
              <div className="adt-header-top">
                <div className="adt-header-id">
                  <div className="adt-avatar nft-avatar" style={{ background: c.bannerColor || "var(--sv2-accent)" }}>{c.symbol}</div>
                  <div>
                    <div className="adt-name-row">
                      <span className="adt-name">{c.name}</span>
                      {c.subcategory && <span className="adt-tag">{c.subcategory}</span>}
                      {c.verified && <span className="adt-tag">Verified</span>}
                      <span className="adt-tag">NFT</span>
                    </div>
                    <div className="adt-price-row">
                      <span className="adt-price">{eth(c.floorEth)}</span>
                      {typeof c.floorUsd === "number" && <span className="sv2-muted">{formatAssetPrice(c.floorUsd)}</span>}
                      {typeof c.change24h === "number" && (
                        <span className={`adt-change ${c.change24h >= 0 ? "positive" : "negative"}`}>{formatPct(c.change24h, { withSign: true })} 24h</span>
                      )}
                    </div>
                    <div className="sv2-mute2 sv2-tiny">
                      Floor price {c.floorDate ? `at 00:00 UTC, ${c.floorDate}` : ""} · {num(c.supply)} items
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <ErrorBoundary variant="section" label="Floor chart">
              <NftFloorCard history={c.history} risk={c.risk} liquidityBadge={<LiquidityBadge liquidity={c.liquidity} />} />
            </ErrorBoundary>

            <div className="adt-panel-row">
              <ErrorBoundary variant="section" label="Risk"><RiskCard risk={c.risk} /></ErrorBoundary>
              <ErrorBoundary variant="section" label="Liquidity"><LiquidityCard liquidity={c.liquidity} /></ErrorBoundary>
              <ErrorBoundary variant="section" label="Sales"><SalesCard sales={c.recentSales} /></ErrorBoundary>
            </div>

            <div className="sv2-mute2 sv2-tiny nft-footnote">
              Data: OpenSea floor and sales, Ethereum prices from Binance; updated daily
              {c.risk.lastUpdated ? ` (last update ${c.risk.lastUpdated.replace("T", " ").replace("Z", " UTC")})` : ""}.
              No forecast of the floor price is shown.
            </div>
          </>
        )}
      </div>
    </div>
  );
}
