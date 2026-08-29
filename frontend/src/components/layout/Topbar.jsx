import { useTheme } from "../../context/ThemeContext";
import { IconThemeToggle } from "../icons";
import TopbarSearch from "./topbar/TopbarSearch";
import MarketStatusPill from "./topbar/MarketStatusPill";
import NotificationsMenu from "./topbar/NotificationsMenu";
import UserMenu from "./topbar/UserMenu";
import "../../styles/topbar.css";

export default function Topbar() {
  const { isDark, toggle } = useTheme();

  return (
    <header className="tb-root">
      <TopbarSearch />

      <div className="tb-right">
        <MarketStatusPill />

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
      </div>
    </header>
  );
}