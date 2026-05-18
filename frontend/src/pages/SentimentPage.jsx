import { useTheme } from "../context/ThemeContext";
import { makeStyles } from "../styles/makeStyles";
import GlobalSentimentChart from "../components/sentiment/GlobalSentimentChart";
import MarketMoodCard from "../components/sentiment/MarketMoodCard";
import TrendingTopics from "../components/sentiment/TrendingTopics";
import AssetSentimentRanking from "../components/sentiment/AssetSentimentRanking";
import LiveAIFeed from "../components/sentiment/LiveAIFeed";

export default function SentimentPage() {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);

    return (
        <div style={s.content}>
            {/* Page header */}
            <div style={s.pageHeader}>
                <div>
                    <h1 style={s.pageTitle}>Sentiment Analytics</h1>
                    <p style={s.pageSub}>AI-processed social and news sentiment across alternative markets.</p>
                </div>
            </div>

            {/* Top row: big chart + right column */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 260px", gap: 10, marginBottom: 10 }}>
                <GlobalSentimentChart />
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    <MarketMoodCard />
                    <TrendingTopics />
                </div>
            </div>

            {/* Bottom row: ranking + live feed */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <AssetSentimentRanking />
                <LiveAIFeed />
            </div>
        </div>
    );
}