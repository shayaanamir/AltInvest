import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "../styles/topbar.css";
import {
  notificationsApi, notificationHref, onNotificationsChanged, NOTIFICATION_TYPE_LABELS,
} from "../services/notificationsApi";
import NotificationItem from "../components/layout/topbar/NotificationItem";
import { ErrorState, useToast } from "../errors";

const PAGE_SIZE = 25;
const FILTERS = [
  { key: "all", label: "All" },
  { key: "unread", label: "Unread" },
  ...Object.entries(NOTIFICATION_TYPE_LABELS).map(([key, label]) => ({ key, label })),
];

/** Every notification, newest first, loaded a page at a time. */
export default function NotificationsPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [filter, setFilter] = useState("all");
  const [items, setItems] = useState([]);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [unread, setUnread] = useState(0);
  const [reload, setReload] = useState(0);

  const query = (offset) => ({
    offset,
    limit: PAGE_SIZE,
    unreadOnly: filter === "unread",
    types: filter !== "all" && filter !== "unread" ? [filter] : [],
  });

  // First page (again) whenever the filter changes or something changed elsewhere (e.g. the bell).
  useEffect(() => {
    let cancelled = false;
    Promise.all([notificationsApi.list(query(0)), notificationsApi.unreadCount()])
      .then(([page, count]) => {
        if (cancelled) return;
        setItems(page);
        setHasMore(page.length === PAGE_SIZE);
        setUnread(count);
        setError(null);
      })
      .catch((e) => !cancelled && setError(e))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter, reload]);

  useEffect(() => onNotificationsChanged(() => setReload((n) => n + 1)), []);

  const loadMore = async () => {
    try {
      const page = await notificationsApi.list(query(items.length));
      setItems((prev) => [...prev, ...page]);
      setHasMore(page.length === PAGE_SIZE);
    } catch (e) {
      toast.error(e, { title: "Couldn't load more notifications" });
    }
  };

  const act = async (fn, title) => {
    try {
      await fn();
    } catch (e) {
      toast.error(e, { title });
    }
  };

  const open = (n) => {
    if (!n.read) act(() => notificationsApi.markRead(n.id), "Couldn't mark notification as read");
    navigate(notificationHref(n));
  };

  return (
    <div className="sv2">
      <div className="sv2-page">
        <div className="sv2-page-header">
          <div>
            <h1 className="sv2-page-title">Notifications</h1>
            <p className="sv2-page-sub">{unread ? `${unread} unread` : "You're all caught up."} Alerts that fire and market events land here.</p>
          </div>
          {unread > 0 && (
            <button className="sv2-btn-outline" style={{ width: "auto" }} onClick={() => act(notificationsApi.markAllRead, "Couldn't mark notifications as read")}>
              Mark all read
            </button>
          )}
        </div>

        <div className="sv2-segmented" style={{ marginBottom: 14 }}>
          {FILTERS.map((f) => (
            <button key={f.key} className={filter === f.key ? "active" : ""} onClick={() => { setLoading(true); setFilter(f.key); }}>
              {f.label}
            </button>
          ))}
        </div>

        <div className="sv2-card ntf-list">
          {error ? (
            <ErrorState error={error} onRetry={() => setReload((n) => n + 1)} variant="panel" title="Couldn't load notifications" />
          ) : loading ? (
            <div className="tb-dropdown-empty">Loading…</div>
          ) : items.length === 0 ? (
            <div className="tb-dropdown-empty">{filter === "all" ? "No notifications yet." : "Nothing here."}</div>
          ) : (
            items.map((n) => (
              <NotificationItem
                key={n.id}
                full
                notification={n}
                onSelect={() => open(n)}
                onDismiss={() => act(() => notificationsApi.dismiss(n.id), "Couldn't dismiss the notification")}
              />
            ))
          )}
        </div>

        {hasMore && !loading && !error && (
          <div style={{ textAlign: "center", marginTop: 14 }}>
            <button className="sv2-btn-outline" style={{ width: "auto" }} onClick={loadMore}>Load more</button>
          </div>
        )}
      </div>
    </div>
  );
}
