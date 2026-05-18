import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";

export default function AboutAsset() {
    const { tokens: t } = useTheme();
    const s = makeStyles(t);

    return (
        <div style={s.card}>
            <div style={{ padding: "11px 14px 10px", borderBottom: `1px solid ${t.border}` }}>
                <span style={{ ...s.cardTitle, display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontSize: 13, color: t.accentBlue }}>ℹ</span> About Bitcoin
                </span>
            </div>
            <div style={{
                padding: "12px 14px",
                fontSize: 11.5,
                color: t.textSecondary,
                lineHeight: 1.65,
                maxHeight: 160,
                overflow: "hidden",
                maskImage: "linear-gradient(to bottom, black 70%, transparent 100%)",
                WebkitMaskImage: "linear-gradient(to bottom, black 70%, transparent 100%)",
            }}>
                Bitcoin is a decentralized digital currency without a central bank or single administrator
                that can be sent from user to user on the peer-to-peer network without the need for
                intermediaries. Transactions are verified by network nodes through cryptography and
                recorded in a public distributed ledger called a blockchain. Bitcoin was invented in 2008
                by an unknown person or group of people using the name Satoshi Nakamoto, and started
                in 2009 when its source code was released as open-source software.
            </div>
        </div>
    );
}