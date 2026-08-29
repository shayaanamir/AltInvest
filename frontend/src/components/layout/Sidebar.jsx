import { useState } from "react";
import { useTheme } from "../../context/ThemeContext";
import { clearSession } from "../../hooks/useAuth";
import { NAV_ITEMS, BOTTOM_NAV } from "../../routes";
import {
  IconDashboard,
  IconCompass,
  IconClock,
  IconColumns,
  IconPortfolio,
  IconStar,
  IconBell,
  IconSettings,
  IconLogout,
  IconCollapse,
} from "../icons";

function MenuIcon({ label, color = "currentColor", size = 16, style }) {
  const iconProps = { size, style: { color, ...style } };

  switch (label) {
    case "Dashboard":
      return <IconDashboard {...iconProps} />;
    case "Discover":
      return <IconCompass {...iconProps} />;
    case "Sentiment":
      return <IconClock {...iconProps} />;
    case "Compare":
      return <IconColumns {...iconProps} />;
    case "Portfolio":
      return <IconPortfolio {...iconProps} />;
    case "Watchlists":
      return <IconStar {...iconProps} />;
    case "Alerts":
      return <IconBell {...iconProps} />;
    case "Settings":
      return <IconSettings {...iconProps} />;
    case "Logout":
      return <IconLogout {...iconProps} />;
    case "Collapse":
      return <IconCollapse {...iconProps} />;
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
          const active = item.key === activePage;
          return (
            <div
              key={item.key}
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
              onClick={() => onNavigate && onNavigate(item.key)}
              title={collapsed ? item.key : undefined}
            >
              <MenuIcon label={item.key} color={active ? "var(--sv2-accent, #bf5d38)" : "var(--sv2-text-soft, #6c6555)"} size={17} />
              {!collapsed && <span>{item.key}</span>}
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
          const active = item.key === activePage;
          return (
            <div
              key={item.key}
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
              onClick={() => onNavigate && onNavigate(item.key)}
              title={collapsed ? item.key : undefined}
            >
              <MenuIcon label={item.key} color={active ? "var(--sv2-accent, #bf5d38)" : "var(--sv2-text-soft, #6c6555)"} size={17} />
              {!collapsed && <span>{item.key}</span>}
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
            clearSession();
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