import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";

const HOLDINGS = [
    { sym: "BTC", name: "Bitcoin", ticker: "BTC", balance: "0.1557", value: "$10,000", change: "+", chgColor: "green", action: "Buy More", actionType: "buy" },
    { sym: "ETH", name: "Ethereum", ticker: "ETH", balance: "2.8984", value: "$10,000", change: "-1.2", chgColor: "red", action: "Hold", actionType: "hold" },
    { sym: "SOL", name: "Solana", ticker: "SOL", balance: "68.5871", value: "$10,000", change: "+", chgColor: "green", action: "Buy More", actionType: "buy" },
    { sym: "BAY", name: "Bored Ape YC", ticker: "BAYC", balance: "0.2353", value: "$10,000", change: "-4.5", chgColor: "red", action: "Reduce", actionType: "reduce" },
];

const TICKER_COLORS = {
    BTC: "#f7931a",
    ETH: "#627eea",
    SOL: "#9945ff",
    BAY: "#00d4ff",
};

export default function CurrentHoldings() {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);

    const actionStyle = (type) => {
        if (type === "buy") return { background: t.btnPrimaryBg, color: "#fff", border: "none" };
        if (type === "reduce") return { background: "rgba(255,64,96,0.15)", color: t.accentRed, border: `1px solid ${t.accentRed}` };
        return { background: "none", color: t.textSecondary, border: `1px solid ${t.btnOutlineBorder}` };
    };

    return (
        <div style={{ ...s.card, marginTop: 10 }}>
            <div style={s.cardHeader}>
                <span style={s.cardTitle}>Current Holdings</span>
            </div>
            <div>
                {/* Table header */}
                <div style={{
                    display: "grid",
                    gridTemplateColumns: "2fr 1fr 1fr 1fr 120px",
                    padding: "8px 16px",
                    borderBottom: `1px solid ${t.border}`,
                }}>
                    {["Asset", "Balance", "Value", "24h Change", "AI Action"].map(h => (
                        <span key={h} style={{ fontSize: 10.5, color: t.textMuted, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>{h}</span>
                    ))}
                </div>

                {HOLDINGS.map((row, i) => (
                    <div
                        key={row.ticker}
                        style={{
                            display: "grid",
                            gridTemplateColumns: "2fr 1fr 1fr 1fr 120px",
                            padding: "13px 16px",
                            alignItems: "center",
                            borderBottom: i < HOLDINGS.length - 1 ? `1px solid ${t.border}` : "none",
                            transition: "background 0.15s",
                        }}
                        onMouseEnter={e => e.currentTarget.style.background = t.bgHover}
                        onMouseLeave={e => e.currentTarget.style.background = "transparent"}
                    >
                        {/* Asset */}
                        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                            <div style={{
                                width: 34, height: 34, borderRadius: 8,
                                background: t.bgCard2, border: `1px solid ${t.borderLight}`,
                                display: "flex", alignItems: "center", justifyContent: "center",
                                fontSize: 9, fontWeight: 800, color: TICKER_COLORS[row.sym] || t.textPrimary,
                                letterSpacing: "0.02em",
                            }}>
                                {row.sym}
                            </div>
                            <div>
                                <div style={{ fontSize: 12.5, fontWeight: 700, color: t.textPrimary }}>{row.name}</div>
                                <div style={{ fontSize: 10, color: t.textMuted, marginTop: 1 }}>{row.ticker}</div>
                            </div>
                        </div>

                        {/* Balance */}
                        <span style={{ fontSize: 12, color: t.textSecondary }}>{row.balance}</span>

                        {/* Value */}
                        <span style={{ fontSize: 12, fontWeight: 600, color: t.textPrimary }}>{row.value}</span>

                        {/* 24h Change */}
                        <span style={{
                            fontSize: 12, fontWeight: 600,
                            color: row.chgColor === "green" ? t.accentGreen : t.accentRed,
                        }}>
                            {row.change}
                        </span>

                        {/* AI Action */}
                        <button style={{
                            ...actionStyle(row.actionType),
                            borderRadius: 7, padding: "5px 12px",
                            fontSize: 11.5, fontWeight: 600, cursor: "pointer",
                            whiteSpace: "nowrap",
                        }}>
                            {row.action}
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
}