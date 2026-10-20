import { useState, useEffect, useCallback } from "react";
import { useTheme } from "../context/ThemeContext";
import "../styles/sentiment.css";
import SentimentHub from "../components/sentiment/SentimentHub";
import AssetSentimentDetail from "../components/sentiment/AssetSentimentDetail";
import { sentimentApi, notifySentimentUpdated } from "../services/sentimentApi";
import { useSentimentPoller } from "../hooks/useSentimentPoller";
import { ErrorBoundary, useToast } from "../errors";
import { getApiState, subscribeConnection } from "../errors/connectionStatus";

export default function SentimentPage() {
  const { isDark } = useTheme();
  const toast = useToast();
  const [selectedAsset, setSelectedAsset]   = useState(null);
  const [refreshing, setRefreshing]         = useState(false);
  const [lastUpdated, setLastUpdated]       = useState(null);
  const [checkFailed, setCheckFailed]       = useState(false);
  const [apiState, setApiState]             = useState(getApiState);

  useEffect(() => subscribeConnection(() => setApiState(getApiState())), []);

  const colors = isDark
    ? { green: "#3fcf8e", red: "#f0616f", arcGreen: "#2e6059", arcRed: "#6e3545", accent: "#e2825a", greyArc: "#343852", border: "rgba(255,255,255,0.08)", textSoft: "#9aa0ba", textMute: "#5b6280", purple: "#9b8cf0", teal: "#4fb4b0" }
    : { green: "#2f8f5b", red: "#c0392b", arcGreen: "#6ab5a4", arcRed: "#c49099", accent: "#bf5d38", greyArc: "#ddd6c6", border: "#ece5d7", textSoft: "#6c6555", textMute: "#a49b87", purple: "#7d6bc4", teal: "#2f8f8a" };

  // Called by the poller every time the backend has fresh data. Widgets re-fetch in place; the
  // hub is not remounted, so the user's scope, range, tab and filters are left alone.
  const handlePollUpdate = useCallback(() => {
    notifySentimentUpdated();
    setLastUpdated(new Date());
  }, []);

  // Live poll: every 5 min, including while an asset's detail is open (it refreshes too)
  useSentimentPoller({
    onUpdate: handlePollUpdate,
    onStatus: (ok) => setCheckFailed(!ok),
  });

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await sentimentApi.refreshAllActive();
      setLastUpdated(new Date());
    } catch (e) {
      toast.error(e, { title: "Couldn't refresh the sentiment pipeline" });
    } finally {
      // refreshAllActive has already announced whatever did update, even after a partial failure
      setRefreshing(false);
    }
  };

  const updatedAt = lastUpdated
    ? lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : null;

  // "Live" only while the data service is answering. If it stops, say so and keep the time of
  // the last update the user can still see.
  const offline = apiState === "down";
  const base = offline
    ? (updatedAt ? `Offline · last updated ${updatedAt}` : "Offline")
    : (updatedAt ? `Live · Updated ${updatedAt}` : null);
  // A check that failed while the API is otherwise reachable (e.g. a server error) still counts.
  const liveLabel = !offline && checkFailed
    ? (base ? `${base} · last check for updates failed` : "Last check for updates failed")
    : base;

  return (
    <div className="sv2">
      <div className="sv2-page">
        {liveLabel && !selectedAsset && (
          <div style={{
            display: "flex", alignItems: "center", gap: 6,
            fontSize: 11, color: offline || checkFailed ? colors.red : (isDark ? "#3fcf8e" : "#2f8f5b"),
            marginBottom: -8, paddingLeft: 2,
          }}>
            <span style={{
              width: 7, height: 7, borderRadius: "50%",
              background: "currentColor", display: "inline-block",
              animation: offline || checkFailed ? "none" : "sv2-pulse 2s ease-in-out infinite",
            }} />
            {liveLabel}
          </div>
        )}

        <ErrorBoundary variant="section" label="Sentiment" resetKey={selectedAsset}>
        {selectedAsset ? (
          <AssetSentimentDetail
            assetId={selectedAsset}
            colors={colors}
            onBack={() => setSelectedAsset(null)}
            onSwitchAsset={setSelectedAsset}
          />
        ) : (
          <SentimentHub
            colors={colors}
            onSelectAsset={setSelectedAsset}
            onRefresh={handleRefresh}
            refreshing={refreshing}
          />
        )}
        </ErrorBoundary>
      </div>
    </div>
  );
}
