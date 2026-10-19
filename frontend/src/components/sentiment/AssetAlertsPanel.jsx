import { useAsync } from "../../hooks/useAsync";
import { alertsApi } from "../../services/alertsApi";
import { ErrorState, useToast } from "../../errors";
import { IconTrash } from "../icons";

/**
 * The user's real alerts on this asset (from /alerts), with a button to add another.
 * `version` changes after an alert is created so the list reloads.
 */
export default function AssetAlertsPanel({ symbol, covered, version, onNewAlert }) {
  const toast = useToast();
  const { data, loading, error, refetch, setData } = useAsync(
    async () => (await alertsApi.getAlerts()).filter((a) => a.targetType === "crypto" && a.targetSymbol === symbol),
    [symbol, version]
  );

  const removeAlert = async (alert) => {
    try {
      await alertsApi.deleteAlert(alert.id);
      setData((prev) => (prev || []).filter((a) => a.id !== alert.id));
    } catch (e) {
      toast.error(e, { title: "Couldn't delete the alert" });
    }
  };

  return (
    <div className="sv2-card sv2-card-pad-sm">
      <div className="sv2-card-title" style={{ marginBottom: 12 }}>Alerts</div>
      <button className="sv2-btn-outline" style={{ width: "100%" }} onClick={onNewAlert} disabled={!covered}>
        Set alert
      </button>

      <div className="sv2-mt-12">
        {error ? (
          <ErrorState error={error} onRetry={refetch} title="Couldn't load your alerts" />
        ) : loading && !data ? (
          <div className="sv2-muted sv2-small">Loading…</div>
        ) : !data || data.length === 0 ? (
          <div className="sv2-muted sv2-small">No alerts on this asset yet.</div>
        ) : (
          data.map((a) => (
            <div key={a.id} className="sv2-alert-row">
              <span>{a.conditionText}{a.status !== "active" ? ` (${a.status})` : ""}</span>
              <button className="sv2-trash-btn" title="Delete alert" aria-label="Delete alert" onClick={() => removeAlert(a)}><IconTrash /></button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
