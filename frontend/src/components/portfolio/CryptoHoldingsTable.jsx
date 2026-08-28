import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useTheme } from "../../context/ThemeContext";
import { sv2Colors } from "../../utils/sv2Colors";
import { portfolioApi } from "../../services/portfolioApi";
import { formatAssetPrice, formatPct } from "../../utils/formatters";
import { IconBell, IconTrash } from "../sentiment/icons";
import { IconPencil } from "./icons";

function aaiColor(score, colors) {
  if (score >= 70) return colors.green;
  if (score >= 45) return colors.accent;
  return colors.red;
}

export default function CryptoHoldingsTable() {
  const { isDark } = useTheme();
  const colors = isDark ? sv2Colors.dark : sv2Colors.light;
  const navigate = useNavigate();
  const [holdings, setHoldings] = useState(null);

  useEffect(() => {
    portfolioApi.getCryptoHoldings().then(setHoldings).catch(console.error);
  }, []);

  return (
    <div className="sv2-card sv2-card-pad" style={{ marginTop: 10 }}>
      <div className="sv2-card-title">Crypto holdings</div>
      <div className="sv2-card-sub" style={{ marginBottom: 6 }}>Row click opens the full asset page</div>

      {!holdings ? (
        <div className="sv2-muted sv2-small" style={{ padding: "24px 0" }}>Loading…</div>
      ) : (
        <div>
          <div className="pv2-holdings-row pv2-holdings-head">
            <span>Asset</span>
            <span>Balance</span>
            <span>Value</span>
            <span>24h</span>
            <span>AAI</span>
            <span>Suggested</span>
            <span>Manage</span>
          </div>

          {holdings.map((h) => {
            const positive = h.change24hPct >= 0;
            return (
              <div key={h.symbol} className="pv2-holdings-row" onClick={() => navigate("/asset-detail")}>
                <div className="pv2-asset-cell">
                  <div className="pv2-avatar" style={{ background: h.logoColor }}>
                    {h.symbol.slice(0, 3)}
                  </div>
                  <div>
                    <div className="pv2-asset-name">{h.name}</div>
                    <div className="pv2-asset-symbol">{h.symbol}</div>
                  </div>
                </div>

                <span className="sv2-small">{h.quantity}</span>
                <span className="sv2-small sv2-bold">{formatAssetPrice(h.valueUsd)}</span>

                <span className={`dv2-asset-change ${positive ? "positive" : "negative"}`}>
                  {positive ? "↗" : "↘"} {formatPct(h.change24hPct, { withSign: true })}
                </span>

                <span className="pv2-aai-pill">
                  <span className="pv2-aai-dot" style={{ background: aaiColor(h.aaiScore, colors) }} />
                  AAI {h.aaiScore}
                </span>

                <span className="pv2-suggested-btn">{h.aiAction}</span>

                <div className="pv2-manage-icons" onClick={(e) => e.stopPropagation()}>
                  <button type="button" title="Set alert"><IconBell size={14} /></button>
                  <button type="button" title="Edit"><IconPencil size={13} /></button>
                  <button type="button" title="Remove"><IconTrash size={14} /></button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}