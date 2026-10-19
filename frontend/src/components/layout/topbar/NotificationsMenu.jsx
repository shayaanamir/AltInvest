import { useNavigate } from "react-router-dom";
import { useAsync } from "../../../hooks/useAsync";
import { useDisclosure } from "../../../hooks/useDisclosure";
import { topbarApi } from "../../../services/topbarApi";
import NotificationItem from "./NotificationItem";
import { IconBell } from "../../icons";
import { ErrorState, useToast } from "../../../errors";

const RECENT_LIMIT = 5;

export default function NotificationsMenu() {
  const { isOpen, toggle, close, ref } = useDisclosure();
  const navigate = useNavigate();
  const toast = useToast();
  const { data, error, refetch, setData } = useAsync(() => topbarApi.getNotifications(), []);

  const items = (data?.items || []).slice(0, RECENT_LIMIT);
  const unreadCount = data?.unreadCount ?? 0;

  const handleSelect = async (notification) => {
    close();

    if (!notification.read) {
      // Optimistic mark-as-read
      setData((prev) => {
        if (!prev) return prev;
        const nextItems = prev.items.map((n) =>
          n.id === notification.id ? { ...n, read: true } : n
        );
        return { items: nextItems, unreadCount: Math.max(0, prev.unreadCount - 1) };
      });
      try {
        await topbarApi.markNotificationRead(notification.id);
      } catch (e) {
        setData(data); // put the unread state back
        toast.error(e, { title: "Couldn't mark notification as read" });
      }
    }

    const deepLink = notification.deepLink;
    if (!deepLink) return;

    if (deepLink.page === "AssetDetail" && deepLink.symbol) {
      navigate(`/asset-detail?symbol=${deepLink.symbol}`);
    } else if (deepLink.page === "NFTCollectionDetail" || deepLink.page === "Discover") {
      navigate("/discover");
    } else if (deepLink.page === "Portfolio") {
      navigate("/portfolio");
    }
  };

  return (
    <div className="tb-menu" ref={ref}>
      <button
        type="button"
        className="tb-icon-btn"
        onClick={toggle}
        aria-haspopup="true"
        aria-expanded={isOpen}
        aria-label="Notifications"
      >
        <IconBell size={17} />
        {unreadCount > 0 && <span className="tb-badge">{unreadCount > 9 ? "9+" : unreadCount}</span>}
      </button>

      {isOpen && (
        <div className="tb-dropdown tb-notifications-dropdown">
          <div className="tb-dropdown-head">
            <span>Notifications</span>
            {unreadCount > 0 && <span className="tb-dropdown-head-sub">{unreadCount} unread</span>}
          </div>

          <div className="tb-notifications-list">
            {error ? (
              <div style={{ padding: "8px 14px" }}>
                <ErrorState error={error} onRetry={refetch} title="Couldn't load notifications" />
              </div>
            ) : items.length === 0 ? (
              <div className="tb-dropdown-empty">You&apos;re all caught up.</div>
            ) : (
              items.map((notification) => (
                <NotificationItem
                  key={notification.id}
                  notification={notification}
                  onSelect={() => handleSelect(notification)}
                />
              ))
            )}
          </div>

          <button
            type="button"
            className="tb-dropdown-footer-btn"
            onClick={() => {
              close();
              navigate("/alerts");
            }}
          >
            View all alerts
          </button>
        </div>
      )}
    </div>
  );
}