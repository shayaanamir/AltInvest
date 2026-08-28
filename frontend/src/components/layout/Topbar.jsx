import { useTheme } from "../../context/ThemeContext";
import { makeStyles } from "../../styles/makeStyles";
import { IconThemeToggle } from "../icons";

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
        <button
          style={s.themeToggle}
          onClick={toggle}
          title={isDark ? "Switch to Light" : "Switch to Dark"}
        >
          <div style={s.themeToggleTrack}>
            <div style={{
              ...s.themeToggleThumb,
              transform: isDark ? "translateX(0)" : "translateX(29px)",
            }}>
              <IconThemeToggle isDark={isDark} variant="filled" size={12} />
            </div>
          </div>
        </button>

        <div style={s.userInfo}>
          <div>
            <div style={s.userName}>Alex Investor</div>
          </div>
          <div style={s.avatar}>AI</div>
        </div>
      </div>
    </header>
  );
}
