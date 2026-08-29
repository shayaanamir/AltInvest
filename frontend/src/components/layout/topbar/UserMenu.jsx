import { useNavigate } from "react-router-dom";
import { useAsync } from "../../../hooks/useAsync";
import { useDisclosure } from "../../../hooks/useDisclosure";
import { clearSession } from "../../../hooks/useAuth";
import { topbarApi } from "../../../services/topbarApi";

export default function UserMenu() {
  const { isOpen, toggle, close, ref } = useDisclosure();
  const navigate = useNavigate();
  const { data: user } = useAsync(() => topbarApi.getCurrentUser(), []);

  if (!user) return null;

  const goTo = (path) => {
    close();
    navigate(path);
  };

  const handleLogout = () => {
    close();
    clearSession();
    navigate("/");
  };

  return (
    <div className="tb-menu" ref={ref}>
      <button
        type="button"
        className="tb-user-trigger"
        onClick={toggle}
        aria-haspopup="true"
        aria-expanded={isOpen}
      >
        <span className="tb-user-avatar" style={{ background: user.color }}>
          {user.initials}
        </span>
        <span className="tb-user-name">{user.name}</span>
      </button>

      {isOpen && (
        <div className="tb-dropdown tb-user-dropdown">
          <div className="tb-user-dropdown-head">
            <span className="tb-user-avatar" style={{ background: user.color }}>
              {user.initials}
            </span>
            <div>
              <div className="tb-user-dropdown-name">{user.name}</div>
              <div className="tb-user-dropdown-email">{user.email}</div>
            </div>
          </div>

          <div className="tb-user-dropdown-links">
            <button type="button" onClick={() => goTo("/profile")}>Profile</button>
            <button type="button" onClick={() => goTo("/settings")}>Settings</button>
          </div>

          <button type="button" className="tb-user-dropdown-logout" onClick={handleLogout}>
            Logout
          </button>
        </div>
      )}
    </div>
  );
}