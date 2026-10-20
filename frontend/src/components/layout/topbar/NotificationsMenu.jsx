import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAsync } from "../../../hooks/useAsync";
import { useDisclosure } from "../../../hooks/useDisclosure";
import { notificationsApi, notificationHref, onNotificationsChanged } from "../../../services/notificationsApi";
import NotificationItem from "./NotificationItem";
import { IconBell } from "../../icons";
import { ErrorState, useToast } from "../../../errors";

const RECENT_LIMIT = 8;
const COUNT_POLL_MS = 60_000; // new alert notifications are written by the server every few minutes

export default function NotificationsMenu() {
  const { isOpen, toggle, close, ref } = useDisclosure();
  const navigate = useNavigate();
  const toast = useToast();

  // The badge uses the server's unread total; the list loads when the menu opens.
  const { data: unreadCount, refetch: refetchCount } = useAsync(() => notificationsApi.unreadCount(), [], { subscribe: onNotificationsChanged });
  const { data: items, error, refetch } = useAsync(
    () => (isOpen ? notificationsApi.list({ limit: RECENT_LIMIT }) : Promise.resolve(null)),
    [isOpen],
    { subscribe: onNotificationsChanged }
  );

  useEffect(() => {
    const t = setInterval(() => refetchCount(), COUNT_POLL_MS);
    return () => clearInterval(t);
  }, [refetchCount]);

  const count = unreadCount ?? 0;

  const open = async (n) => {
    close();
    if (!n.read) notificationsApi.markRead(n.id).catch((e) => toast.error(e, { title: "Couldn't mark notification as read" }));
    navigate(notificationHref(n));
  };

  const dismiss = async (n) => {
    try {
      await notificationsApi.dismiss(n.id);
    } catch (e) {
      toast.error(e, { title: "Couldn't dismiss the notification" });
    }
  };

  const markAll = async () => {
    try {
      await notificationsApi.markAllRead();
    } catch (e) {
      toast.error(e, { title: "Couldn't mark notifications as read" });
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
        aria-label={count ? `Notifications, ${count} unread` : "Notifications"}
      >
        <IconBell size={17} />
        {count > 0 && <span className="tb-badge">{count > 99 ? "99+" : count}</span>}
      </button>

      {isOpen && (
        <div className="tb-dropdown tb-notifications-dropdown">
          <div className="tb-dropdown-head">
            <span>Notifications{count > 0 && <span className="tb-dropdown-head-sub"> · {count} unread</span>}</span>
            {count > 0 && (
              <button type="button" className="tb-head-action" onClick={markAll}>Mark all read</button>
            )}
          </div>

          <div className="tb-notifications-list">
            {error ? (
              <div style={{ padding: "8px 14px" }}>
                <ErrorState error={error} onRetry={refetch} title="Couldn't load notifications" />
              </div>
            ) : !items ? (
              <div className="tb-dropdown-empty">Loading…</div>
            ) : items.length === 0 ? (
              <div className="tb-dropdown-empty">You&apos;re all caught up.</div>
            ) : (
              items.map((n) => (
                <NotificationItem key={n.id} notification={n} onSelect={() => open(n)} onDismiss={() => dismiss(n)} />
              ))
            )}
          </div>

          <button
            type="button"
            className="tb-dropdown-footer-btn"
            onClick={() => {
              close();
              navigate("/notifications");
            }}
          >
            See all notifications
          </button>
        </div>
      )}
    </div>
  );
}
