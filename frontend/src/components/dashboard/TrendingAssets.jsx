import { useTheme } from "../../context/ThemeContext";
import { TRENDING_ASSETS } from "../../data/constants";
import { makeStyles } from "../../styles/makeStyles";
import MiniChart from "../charts/MiniChart";

const SIG_ARROW = { Up: "↑", Down: "↓", Hold: "—" };

function AssetCard({ sym, name, cat, price, chg, pos, score, sig, data, isLast }) {
  const { tokens: t } = useTheme();
  const s = makeStyles(t);

  const chgColor = pos ? t.accentGreen : t.accentRed;
  const sigColor = sig === "Hold" ? t.accentYellow : chgColor;

  return (
    <div style={{ ...s.assetCard, ...(isLast ? { borderRight: "none" } : {}) }}>
      <div style={s.assetTop}>
        <div style={s.assetSym}>{sym}</div>
        <div style={{ flex: 1 }}>
          <div style={s.assetName}>{name}</div>
          <div style={s.assetCat}>{cat}</div>
        </div>
        <div style={s.assetPb}>
          <div style={s.assetPrice}>{price}</div>
          <div style={{ ...s.assetChg, color: chgColor }}>{chg}</div>
        </div>
      </div>

      <div style={{ margin: "10px 0 6px" }}>
        <MiniChart color={chgColor} data={data} />
      </div>

      <div style={s.assetFooter}>
        <div style={s.scoreRow}>
          <span style={s.scoreIcon}>⬡</span>
          <span style={s.scoreLbl}>AAI Score: <b>{score}</b></span>
        </div>
        <div style={{ ...s.assetSig, color: sigColor }}>
          {SIG_ARROW[sig]} {sig}
        </div>
      </div>
    </div>
  );
}

export default function TrendingAssets() {
  const { tokens: t } = useTheme();
  const s = makeStyles(t);

  return (
    <div style={s.card}>
      <div style={s.trendingHdr}>
        <span style={s.cardTitle}>Trending Assets</span>
        <button style={s.viewAllBtn}>See Screener</button>
      </div>
      <div style={s.assetGrid}>
        {TRENDING_ASSETS.map((asset, i) => (
          <AssetCard
            key={asset.sym}
            {...asset}
            isLast={i === TRENDING_ASSETS.length - 1}
          />
        ))}
      </div>
    </div>
  );
}
