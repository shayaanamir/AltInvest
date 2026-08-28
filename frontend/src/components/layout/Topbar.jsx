import { useTheme } from "../../context/ThemeContext";
import { IconThemeToggle } from "../icons";

export default function Topbar() {
  const { isDark, toggle } = useTheme();

  return (
    <header
      style={{
        height: 58,
        background: "var(--sv2-bg)",
        borderBottom: "1px solid var(--sv2-border)",
        display: "flex", alignItems: "center",
        padding: "0px 40px 0 40px", gap: 14, flexShrink: 0,
        transition: "background 0.25s, border-color 0.25s",
      }}
    >
      <div style={{
        flex: 1, background: "var(--sv2-card-alt)",
        border: "1px solid var(--sv2-border-strong)", borderRadius: 8, height: 34,
        display: "flex", alignItems: "center", padding: "0 10px", gap: 7,
        maxWidth: 380,
      }}>
        <span style={{ fontSize: 14, color: "var(--sv2-text-mute)" }}>⌕</span>
        <span style={{ fontSize: 11.5, color: "var(--sv2-text-mute)", flex: 1 }}>
          Search assets, news, or AI insights (Press '/')
        </span>
        <kbd style={{
          fontSize: 10, color: "var(--sv2-text-mute)",
          background: "var(--sv2-chip)", border: "1px solid var(--sv2-border-strong)",
          borderRadius: 4, padding: "1px 5px", fontFamily: "monospace",
        }}>/</kbd>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 12, marginLeft: "auto" }}>
        <button
          style={{ background: "none", border: "none", cursor: "pointer", padding: 0 }}
          onClick={toggle}
          title={isDark ? "Switch to Light" : "Switch to Dark"}
        >
          <div style={{
            width: 50, height: 24,
            background: "var(--sv2-chip)", border: "1px solid var(--sv2-border-strong)",
            borderRadius: 25, position: "relative", padding: 2,
            display: "flex", alignItems: "center",
          }}>
            <div style={{
              width: 20, height: 20, borderRadius: "50%",
              background: "var(--sv2-card)", border: "1px solid var(--sv2-border-strong)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 11, transition: "transform 0.25s cubic-bezier(0.34,1.56,0.64,1)",
              transform: isDark ? "translateX(0)" : "translateX(29px)",
            }}>
              <IconThemeToggle isDark={isDark} variant="filled" size={12} />
            </div>
          </div>
        </button>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ fontSize: 11.5, fontWeight: 600, color: "var(--sv2-text)", textAlign: "right" }}>
            Alex Investor
          </div>
          <div style={{
            width: 32, height: 32, borderRadius: "50%",
            background: "var(--sv2-accent)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 11, fontWeight: 700, color: "#fff",
          }}>
            AI
          </div>
        </div>
      </div>
    </header>
  );
}