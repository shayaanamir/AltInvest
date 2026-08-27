import { useState } from "react";
import { useTheme } from "../context/ThemeContext";
import "../styles/sentiment.css";
import SentimentHub from "../components/sentiment/SentimentHub";
import AssetSentimentDetail from "../components/sentiment/AssetSentimentDetail";

export default function SentimentPage() {
  const { isDark } = useTheme();
  const [selectedAsset, setSelectedAsset] = useState(null);

  const colors = isDark
    ? { green: "#3fcf8e", red: "#f0616f", arcGreen: "#2e6059", arcRed: "#6e3545", accent: "#e2825a", greyArc: "#343852", border: "rgba(255,255,255,0.08)", textSoft: "#9aa0ba", textMute: "#5b6280", purple: "#9b8cf0", teal: "#4fb4b0" }
    : { green: "#2f8f5b", red: "#c0392b", arcGreen: "#6ab5a4", arcRed: "#c49099", accent: "#bf5d38", greyArc: "#ddd6c6", border: "#ece5d7", textSoft: "#6c6555", textMute: "#a49b87", purple: "#7d6bc4", teal: "#2f8f8a" };

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
          <SentimentHub colors={colors} onSelectAsset={setSelectedAsset} />
        )}
      </div>
    </div>
  );
}