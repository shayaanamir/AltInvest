import { useState, useCallback } from "react";
import { useTheme } from "../context/ThemeContext";
import "../styles/sentiment.css";
import SentimentHub from "../components/sentiment/SentimentHub";
import AssetSentimentDetail from "../components/sentiment/AssetSentimentDetail";
import { sentimentApi } from "../services/sentimentApi";
import { useSentimentPoller } from "../hooks/useSentimentPoller";
import { USE_MOCK } from "../config";

export default function SentimentPage() {
  const { isDark } = useTheme();
  const [selectedAsset, setSelectedAsset]   = useState(null);
  const [refreshKey, setRefreshKey]         = useState(0);
  const [refreshing, setRefreshing]         = useState(false);
  const [lastUpdated, setLastUpdated]       = useState(null);

  const colors = isDark
    ? { green: "#3fcf8e", red: "#f0616f", arcGreen: "#2e6059", arcRed: "#6e3545", accent: "#e2825a", greyArc: "#343852", border: "rgba(255,255,255,0.08)", textSoft: "#9aa0ba", textMute: "#5b6280", purple: "#9b8cf0", teal: "#4fb4b0" }
    : { green: "#2f8f5b", red: "#c0392b", arcGreen: "#6ab5a4", arcRed: "#c49099", accent: "#bf5d38", greyArc: "#ddd6c6", border: "#ece5d7", textSoft: "#6c6555", textMute: "#a49b87", purple: "#7d6bc4", teal: "#2f8f8a" };

  // Called by the poller every time the backend has fresh data
  const handlePollUpdate = useCallback(() => {
    setRefreshKey((k) => k + 1);
    setLastUpdated(new Date());
  }, []);

  // Live poll: every 5 min, only when not in mock mode
  useSentimentPoller({
    onUpdate: handlePollUpdate,
    enabled: !USE_MOCK && !selectedAsset, // pause when drilling into an asset
  });

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await sentimentApi.refreshAllActive();
      setRefreshKey((prev) => prev + 1);
      setLastUpdated(new Date());
    } catch (e) {
      console.error("Pipeline refresh failed:", e);
    } finally {
      setRefreshing(false);
    }
  };

  const liveLabel = lastUpdated
    ? `Updated ${lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
    : null;

  return (
    <div className="sv2">
      <div className="sv2-page">
        {!USE_MOCK && liveLabel && !selectedAsset && (
          <div style={{
            display: "flex", alignItems: "center", gap: 6,
            fontSize: 11, color: isDark ? "#3fcf8e" : "#2f8f5b",
            marginBottom: -8, paddingLeft: 2,
          }}>
            <span style={{
              width: 7, height: 7, borderRadius: "50%",
              background: "currentColor", display: "inline-block",
              animation: "sv2-pulse 2s ease-in-out infinite",
            }} />
            Live · {liveLabel}
          </div>
        )}

        {selectedAsset ? (
          <AssetSentimentDetail
            assetId={selectedAsset}
            colors={colors}
            onBack={() => setSelectedAsset(null)}
            onSwitchAsset={setSelectedAsset}
          />
        ) : (
          <SentimentHub
            key={refreshKey}
            colors={colors}
            onSelectAsset={setSelectedAsset}
            onRefresh={handleRefresh}
            refreshing={refreshing}
          />
        )}
      </div>
    </div>
  );
}