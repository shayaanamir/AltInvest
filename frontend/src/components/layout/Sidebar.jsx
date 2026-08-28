import { useState } from "react";
import { useTheme } from "../../context/ThemeContext";
import { NAV_ITEMS, BOTTOM_NAV } from "../../data/constants";

function MenuIcon({ label, color = "currentColor", size = 16, style }) {
  switch (label) {
    case "Dashboard":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={style}>
          <rect x="3" y="3" width="7" height="9" />
          <rect x="14" y="3" width="7" height="5" />
          <rect x="14" y="12" width="7" height="9" />
          <rect x="3" y="16" width="7" height="5" />
        </svg>
      );
    case "Discover":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={style}>
          <circle cx="12" cy="12" r="10" />
          <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
        </svg>
      );
    case "Sentiment":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={style}>
          <circle cx="12" cy="12" r="10" />
          <path d="M12 6v6l4 2" />
        </svg>
      );
    case "Compare":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={style}>
          <rect x="4" y="3" width="6" height="18" rx="1.5" />
          <rect x="14" y="3" width="6" height="18" rx="1.5" />
        </svg>
      );
    case "Portfolio":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={style}>
          <rect x="2" y="6" width="20" height="12" rx="2" />
          <path d="M12 12h.01" />
          <path d="M17 12h.01" />
        </svg>
      );
    case "Watchlists":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={style}>
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
        </svg>
      );
    case "Alerts":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={style}>
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
      );
    case "Settings":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={style}>
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
        </svg>
      );
    case "Logout":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={style}>
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
          <polyline points="16 17 21 12 16 7" />
          <line x1="21" y1="12" x2="9" y2="12" />
        </svg>
      );
    case "Collapse":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={style}>
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <line x1="9" y1="3" x2="9" y2="21" />
          <path d="M16 15l-3-3 3-3" />
        </svg>
      );
    default:
      return null;
  }
}

export default function Sidebar({ activePage, onNavigate }) {
  const { tokens: t } = useTheme();

  const [collapsed, setCollapsed] = useState(false);

  const sidebarStyle = {
    width: collapsed ? 72 : 230,
    minWidth: collapsed ? 72 : 230,
    background: "var(--sv2-bg, #faf7f1)",
    borderRight: "1px solid var(--sv2-border, #ece5d7)",
    display: "flex",
    flexDirection: "column",
    padding: collapsed ? "16px 0 12px" : "18px 0 14px",
    transition: "width 0.3s cubic-bezier(0.4, 0, 0.2, 1), min-width 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
    fontFamily: "'DM Sans', sans-serif",
    height: "100%",
    boxSizing: "border-box",
  };

  return (
    <aside style={sidebarStyle}>
      {/* Logo Header */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: collapsed ? "0 0 18px 0" : "0 20px 18px 20px",
        borderBottom: "1px solid var(--sv2-border, #ece5d7)",
        justifyContent: collapsed ? "center" : "flex-start",
      }}>
        <div style={{
          width: 42, height: 42, borderRadius: "50%",
          background: "var(--sv2-accent, #bf5d38)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 16, fontWeight: "800", color: "#ffffff",
          flexShrink: 0
        }}>
          AI
        </div>
        {!collapsed && (
          <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
            <span style={{ fontSize: 16, fontWeight: 700, color: "var(--sv2-text, #24211c)", lineHeight: 1.25 }}>AltInvest</span>
            <span style={{ fontSize: 11, color: "var(--sv2-text-soft, #6c6555)" }}>Alternative asset desk</span>
          </div>
        )}
      </div>

      {/* Navigation list */}
      <nav style={{
        display: "flex", flexDirection: "column", gap: 5,
        padding: collapsed ? "14px 0 0" : "14px 12px 0",
        alignItems: collapsed ? "center" : "stretch"
      }}>
        {NAV_ITEMS.map((item) => {
          const active = item.label === activePage;
          return (
            <div
              key={item.label}
              style={{
                display: "flex", alignItems: "center", gap: 12,
                padding: collapsed ? "10px" : "10px 16px",
                borderRadius: collapsed ? 8 : "0 24px 24px 0",
                cursor: "pointer",
                fontSize: 14.5,
                fontWeight: active ? 600 : 500,
                color: active ? "var(--sv2-text, #24211c)" : "var(--sv2-text-soft, #6c6555)",
                background: active ? "var(--sv2-card, #ffffff)" : "transparent",
                borderLeft: active ? "3px solid var(--sv2-accent, #bf5d38)" : "3px solid transparent",
                marginLeft: collapsed ? 0 : -12,
                paddingLeft: collapsed ? 10 : 13,
                justifyContent: collapsed ? "center" : "flex-start",
                transition: "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)"
              }}
              onClick={() => onNavigate && onNavigate(item.label)}
              title={collapsed ? item.label : undefined}
            >
              <MenuIcon label={item.label} color={active ? "var(--sv2-accent, #bf5d38)" : "var(--sv2-text-soft, #6c6555)"} size={17} />
              {!collapsed && <span>{item.label}</span>}
            </div>
          );
        })}
      </nav>

      <div style={{ flex: 1 }} />

      {/* Pro Box */}
      {!collapsed && (
        <div style={{
          margin: "0 12px 16px",
          background: "var(--sv2-card-alt, #f7f3ea)",
          borderRadius: 16,
          padding: "14px 16px",
          border: "1px solid var(--sv2-border, #ece5d7)"
        }}>
          <div style={{ fontSize: 10.5, fontWeight: 800, color: "var(--sv2-accent, #bf5d38)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
            Pro Account
          </div>
          <div style={{ fontSize: 11.5, color: "var(--sv2-text-soft, #6c6555)", marginTop: 6, lineHeight: 1.45 }}>
            Full AAI coverage, unlimited alerts and sentiment history.
          </div>
        </div>
      )}

      {/* Bottom Nav */}
      <div style={{
        display: "flex", flexDirection: "column", gap: 3,
        padding: collapsed ? "0" : "0 12px 10px",
        borderTop: "1px solid var(--sv2-border, #ece5d7)",
        paddingTop: 10,
        alignItems: collapsed ? "center" : "stretch"
      }}>
        {/* Settings */}
        {BOTTOM_NAV.map((item) => {
          const active = item.label === activePage;
          return (
            <div
              key={item.label}
              style={{
                display: "flex", alignItems: "center", gap: 12,
                padding: collapsed ? "10px" : "10px 16px",
                borderRadius: collapsed ? 8 : "0 24px 24px 0",
                cursor: "pointer",
                fontSize: 14.5,
                fontWeight: active ? 600 : 500,
                color: active ? "var(--sv2-text, #24211c)" : "var(--sv2-text-soft, #6c6555)",
                background: active ? "var(--sv2-card, #ffffff)" : "transparent",
                borderLeft: active ? "3px solid var(--sv2-accent, #bf5d38)" : "3px solid transparent",
                marginLeft: collapsed ? 0 : -12,
                paddingLeft: collapsed ? 10 : 13,
                justifyContent: collapsed ? "center" : "flex-start",
                transition: "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)"
              }}
              onClick={() => onNavigate && onNavigate(item.label)}
              title={collapsed ? item.label : undefined}
            >
              <MenuIcon label={item.label} color={active ? "var(--sv2-accent, #bf5d38)" : "var(--sv2-text-soft, #6c6555)"} size={17} />
              {!collapsed && <span>{item.label}</span>}
            </div>
          );
        })}

        {/* Logout */}
        <div
          style={{
            display: "flex", alignItems: "center", gap: 12,
            padding: collapsed ? "10px" : "10px 16px",
            borderRadius: collapsed ? 8 : "0 24px 24px 0",
            cursor: "pointer",
            fontSize: 14.5,
            fontWeight: 500,
            color: "var(--sv2-text-soft, #6c6555)",
            borderLeft: "3px solid transparent",
            marginLeft: collapsed ? 0 : -12,
            paddingLeft: collapsed ? 10 : 13,
            justifyContent: collapsed ? "center" : "flex-start",
            transition: "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)"
          }}
          onClick={() => {
            localStorage.removeItem("altinvest_token");
            localStorage.removeItem("altinvest_user");
            if (onNavigate) onNavigate("Landing");
          }}
          title={collapsed ? "Logout" : undefined}
        >
          <MenuIcon label="Logout" color="var(--sv2-text-soft, #6c6555)" size={17} />
          {!collapsed && <span>Logout</span>}
        </div>

        {/* Collapse */}
        <div
          style={{
            display: "flex", alignItems: "center", gap: 12,
            padding: collapsed ? "10px" : "10px 16px",
            borderRadius: collapsed ? 8 : "0 24px 24px 0",
            cursor: "pointer",
            fontSize: 14.5,
            fontWeight: 500,
            color: "var(--sv2-text-soft, #6c6555)",
            borderLeft: "3px solid transparent",
            marginLeft: collapsed ? 0 : -12,
            paddingLeft: collapsed ? 10 : 13,
            justifyContent: collapsed ? "center" : "flex-start",
            transition: "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)"
          }}
          onClick={() => setCollapsed(!collapsed)}
          title={collapsed ? "Expand" : "Collapse"}
        >
          <MenuIcon
            label="Collapse"
            color="var(--sv2-text-soft, #6c6555)"
            size={17}
            style={{ transform: collapsed ? "rotate(180deg)" : "none", transition: "transform 0.3s ease" }}
          />
          {!collapsed && <span>Collapse</span>}
        </div>
      </div>
    </aside>
  );
}