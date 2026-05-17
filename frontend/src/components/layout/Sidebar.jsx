import { useState } from "react";
import { useTheme } from "../../context/ThemeContext";
import { NAV_ITEMS, BOTTOM_NAV } from "../../data/constants";
import { makeStyles } from "../../styles/makeStyles";

function LogoIcon({ color }) {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <rect x="1"  y="1"  width="7" height="7" rx="1.5" fill={color} />
      <rect x="10" y="1"  width="7" height="7" rx="1.5" fill={color} fillOpacity="0.5" />
      <rect x="1"  y="10" width="7" height="7" rx="1.5" fill={color} fillOpacity="0.5" />
      <rect x="10" y="10" width="7" height="7" rx="1.5" fill={color} />
    </svg>
  );
}

export default function Sidebar() {
  const { tokens: t } = useTheme();
  const s = makeStyles(t);
  const [activeNav, setActiveNav] = useState("Dashboard");

  return (
    <aside style={s.sidebar}>
      <div style={s.logo}>
        <div style={s.logoIcon}>
          <LogoIcon color={t.accentBlue} />
        </div>
        <span style={s.logoText}>AltInvest</span>
      </div>

      <div style={s.menuLabel}>Menu</div>

      <nav style={s.nav}>
        {NAV_ITEMS.map((item) => (
          <div
            key={item.label}
            style={{ ...s.navItem, ...(item.label === activeNav ? s.navItemActive : {}) }}
            onClick={() => setActiveNav(item.label)}
          >
            <span style={s.navIcon}>{item.icon}</span>
            <span style={s.navLabel}>{item.label}</span>
            {item.badge && <span style={s.badge}>{item.badge}</span>}
          </div>
        ))}
      </nav>

      <div style={{ flex: 1 }} />

      <div style={s.proBox}>
        <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
          <div style={s.proAvatar}>✦</div>
          <div>
            <div style={s.proTitle}>Pro Active</div>
            <div style={s.proSub}>Advanced AI models enabled.</div>
          </div>
        </div>
      </div>

      <div style={s.bottomNav}>
        {BOTTOM_NAV.map((item) => (
          <div key={item.label} style={s.navItem}>
            <span style={s.navIcon}>{item.icon}</span>
            <span style={s.navLabel}>{item.label}</span>
          </div>
        ))}
      </div>
    </aside>
  );
}
