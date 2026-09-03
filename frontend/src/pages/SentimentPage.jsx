import { useState } from "react";
import { useTheme } from "../context/ThemeContext";
import "../styles/sentiment.css";
import SentimentHub from "../components/sentiment/SentimentHub";
import AssetSentimentDetail from "../components/sentiment/AssetSentimentDetail";
import { sentimentApi } from "../services/sentimentApi";

export default function SentimentPage() {
  const { isDark } = useTheme();
  const [selectedAsset, setSelectedAsset] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [refreshing, setRefreshing] = useState(false);

  const colors = isDark
    ? { green: "#3fcf8e", red: "#f0616f", arcGreen: "#2e6059", arcRed: "#6e3545", accent: "#e2825a", greyArc: "#343852", border: "rgba(255,255,255,0.08)", textSoft: "#9aa0ba", textMute: "#5b6280", purple: "#9b8cf0", teal: "#4fb4b0" }
    : { green: "#2f8f5b", red: "#c0392b", arcGreen: "#6ab5a4", arcRed: "#c49099", accent: "#bf5d38", greyArc: "#ddd6c6", border: "#ece5d7", textSoft: "#6c6555", textMute: "#a49b87", purple: "#7d6bc4", teal: "#2f8f8a" };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      // Refreshes every actively-covered asset (btc/eth/sol), not just BTC —
      // keeps the button's behavior matching what the Hub actually displays.
      await sentimentApi.refreshAllActive();
      setRefreshKey((prev) => prev + 1);
    } catch (e) {
      console.error("Pipeline refresh failed:", e);
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="sv2">
      <div className="sv2-page">
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