import { useEffect } from "react";
import { useAsync } from "../../hooks/useAsync";
import { alertsApi } from "../../services/alertsApi";
import { formatDate, useAppPreferences } from "../../services/appPreferences";
import { relativeTime } from "../../utils/dateTime";
import { ErrorState } from "../../errors";
import "../portfolio/addHoldingModal.css";

/** Every time an alert fired (GET /alerts/{id}/triggers), newest first. */
export default function AlertHistoryModal({ alert, onClose }) {
  useAppPreferences();
  const { data: rows, error, refetch } = useAsync(() => alertsApi.getTriggers(alert.id), [alert.id]);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="ahm-overlay" onClick={onClose}>
      <div className="ahm" role="dialog" aria-modal="true" aria-label={`${alert.name} alert history`} onClick={(e) => e.stopPropagation()}>
        <div className="ahm-head">
          <h2>Alert history</h2>
          <button type="button" className="ahm-close" aria-label="Close" onClick={onClose}>×</button>
        </div>
        <p className="ahm-desc">
          <strong>{alert.name}</strong>: {alert.conditionText}.{" "}
          {alert.lastCheckedAt ? `Last checked ${relativeTime(alert.lastCheckedAt)}.` : "Not checked yet; rules are checked every 5 minutes."}
        </p>
        <div className="ahm-list" style={{ maxHeight: 320 }}>
          {error ? (
            <ErrorState error={error} onRetry={refetch} title="Couldn't load the history" />
          ) : !rows ? (
            <div className="ahm-empty">Loading…</div>
          ) : rows.length === 0 ? (
            <div className="ahm-empty">This alert hasn't fired yet. It fires when the value crosses your line.</div>
          ) : (
            rows.map((t) => (
              <div key={t.id} className="ahm-item" style={{ cursor: "default" }}>
                <span className="ahm-item-main">
                  <span className="ahm-item-name">{t.message}</span>
                  <span className="ahm-item-sub">
                    {t.previous_value != null ? `${t.previous_value} → ${t.value}` : `${t.value}`}
                  </span>
                </span>
                <span className="ahm-item-price">{formatDate(t.triggered_at)}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
