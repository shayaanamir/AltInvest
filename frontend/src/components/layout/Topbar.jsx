import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";

export default function Topbar() {
  const { tokens: t, isDark, toggle } = useTheme();
  const s = makeStyles(t);

  return (
    <header style={s.topbar}>
      <div style={s.searchBox}>
        <span style={{ fontSize: 14, color: t.textMuted }}>⌕</span>
        <span style={s.searchPlaceholder}>Search assets, news, or AI insights (Press '/')</span>
        <kbd style={s.kbd}>/</kbd>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 12, marginLeft: "auto" }}>
        <div style={s.marketStatus}>
          <span style={s.marketDot} />
          <span style={s.marketLabel}>Market Open</span>
        </div>

        <button style={s.notifBtn}>🔔</button>

        <button
          style={s.themeToggle}
          onClick={toggle}
          title={isDark ? "Switch to Light" : "Switch to Dark"}
        >
          <div style={s.themeToggleTrack}>
            <div style={{
              ...s.themeToggleThumb,
              transform: isDark ? "translateX(0)" : "translateX(20px)",
            }}>
              {isDark ? "🌙" : "☀️"}
            </div>
          </div>
        </button>

        <div style={s.userInfo}>
          <div>
            <div style={s.userName}>Alex Investor</div>
            <div style={s.userTier}>Premium Tier</div>
          </div>
          <div style={s.avatar}>AI</div>
        </div>
      </div>
    </header>
  );
}
