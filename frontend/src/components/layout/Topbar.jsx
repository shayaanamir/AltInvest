import { useTheme } from "../../context/ThemeContext";
import { useState } from "react";
import { IconThemeToggle, IconBell } from "../icons";
import CreateAlertModal from "../alerts/CreateAlertModal";
import TopbarSearch from "./topbar/TopbarSearch";
import MarketStatusPill from "./topbar/MarketStatusPill";
import NotificationsMenu from "./topbar/NotificationsMenu";
import UserMenu from "./topbar/UserMenu";
import "../../styles/topbar.css";

export default function Topbar() {
  const { isDark, toggle } = useTheme();
  const [creatingAlert, setCreatingAlert] = useState(false); // "New alert" from any page

  return (
    <header className="tb-root">
      <TopbarSearch />

      <div className="tb-right">
        <MarketStatusPill />

        <button type="button" className="tb-icon-btn tb-new-alert" onClick={() => setCreatingAlert(true)} title="New alert" aria-label="Create an alert">
          <IconBell size={15} />
          <span className="tb-new-alert-plus" aria-hidden="true">+</span>
        </button>

        <NotificationsMenu />

        <button
          type="button"
          className="tb-icon-btn"
          onClick={toggle}
          title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
          aria-label="Toggle theme"
        >
          <IconThemeToggle isDark={isDark} variant="outline" size={16} />
        </button>

        <UserMenu />
        {creatingAlert && <CreateAlertModal onClose={() => setCreatingAlert(false)} />}
      </div>
    </header>
  );
}