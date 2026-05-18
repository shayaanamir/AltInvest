import { useState } from "react";
import { useTheme } from "../../context/ThemeContext";
import { NAV_ITEMS, BOTTOM_NAV } from "../../data/constants";
import { makeStyles } from "../../styles/makeStyles";

function LogoIcon({ color }) {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <rect x="1" y="1" width="7" height="7" rx="1.5" fill={color} />
      <rect x="10" y="1" width="7" height="7" rx="1.5" fill={color} fillOpacity="0.5" />
      <rect x="1" y="10" width="7" height="7" rx="1.5" fill={color} fillOpacity="0.5" />
      <rect x="10" y="10" width="7" height="7" rx="1.5" fill={color} />
    </svg>
  );
}

function ChevronLeft({ color }) {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M15 18l-6-6 6-6" />
    </svg>
  );
}

function ChevronRight({ color }) {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 18l6-6-6-6" />
    </svg>
  );
}

export default function Sidebar({ activePage, onNavigate }) {
  const { tokens: t } = useTheme();
  const s = makeStyles(t);

  const [collapsed, setCollapsed] = useState(false);

  const sidebarStyle = {
    ...s.sidebar,
    width: collapsed ? 72 : s.sidebar.width,
    minWidth: collapsed ? 72 : s.sidebar.minWidth,
    alignItems: collapsed ? "center" : "stretch",
    padding: collapsed ? "16px 0 12px" : s.sidebar.padding,
  };

  return (
    <aside style={sidebarStyle}>
      <div style={{
        ...s.logo,
        padding: collapsed ? "0 0 14px 0" : s.logo.padding,
        justifyContent: "center",
        flexDirection: collapsed ? "column" : "row",
        position: "relative"
      }}>
        <div style={{ ...s.logoIcon, overflow: "hidden", background: "none" }}>
          <img src="/altinvest_logo.png" alt="AltInvest Logo" style={{ width: "100%", height: "100%", objectFit: "contain" }} />
        </div>
        {!collapsed && <span style={{ ...s.logoText, flex: 1 }}>AltInvest</span>}

        <div
          style={{
            cursor: "pointer",
            display: "flex", alignItems: "center", justifyContent: "center",
            width: 22, height: 22, borderRadius: 6,
            background: t.bgCard2, border: `1px solid ${t.border}`,
            position: collapsed ? "static" : "absolute",
            right: 14,
            marginTop: collapsed ? 8 : 0,
            opacity: 0.8
          }}
          onClick={() => setCollapsed(!collapsed)}
          title="Toggle Sidebar"
          onMouseEnter={(e) => e.currentTarget.style.opacity = 1}
          onMouseLeave={(e) => e.currentTarget.style.opacity = 0.8}
        >
          {collapsed ? <ChevronRight color={t.textSecondary} /> : <ChevronLeft color={t.textSecondary} />}
        </div>
      </div>

      {!collapsed && <div style={s.menuLabel}>Menu</div>}
      {collapsed && <div style={{ height: 26 }} />}

      <nav style={{ ...s.nav, padding: collapsed ? "0" : s.nav.padding, alignItems: collapsed ? "center" : "stretch" }}>
        {NAV_ITEMS.map((item) => (
          <div
            key={item.label}
            style={{
              ...s.navItem,
              ...(item.label === activePage ? s.navItemActive : {}),
              padding: collapsed ? "9px" : s.navItem.padding,
              justifyContent: collapsed ? "center" : "flex-start",
            }}
            onClick={() => onNavigate && onNavigate(item.label)}
            title={collapsed ? item.label : undefined}
          >
            <span style={s.navIcon}>{item.icon}</span>
            {!collapsed && <span style={s.navLabel}>{item.label}</span>}
            {!collapsed && item.badge && <span style={s.badge}>{item.badge}</span>}
          </div>
        ))}
      </nav>

      <div style={{ flex: 1 }} />
      <div style={{ ...s.bottomNav, padding: collapsed ? "8px 0 0" : s.bottomNav.padding, alignItems: collapsed ? "center" : "stretch" }}>
        {BOTTOM_NAV.map((item) => (
          <div
            key={item.label}
            style={{
              ...s.navItem,
              padding: collapsed ? "9px" : s.navItem.padding,
              justifyContent: collapsed ? "center" : "flex-start",
            }}
            title={collapsed ? item.label : undefined}
            onClick={() => {
              if (item.label === "Logout") {
                localStorage.removeItem("token");
                localStorage.removeItem("user");
                if (onNavigate) onNavigate("Landing");
              } else {
                if (onNavigate) onNavigate(item.label);
              }
            }}
          >
            <span style={s.navIcon}>{item.icon}</span>
            {!collapsed && <span style={s.navLabel}>{item.label}</span>}
          </div>
        ))}
      </div>
    </aside>
  );
}