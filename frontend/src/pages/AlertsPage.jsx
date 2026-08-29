import { useState } from "react";
import "../styles/alerts.css";
import { useAsync } from "../hooks/useAsync";
import { alertsApi } from "../services/alertsApi";
import { USE_MOCK } from "../config";
import AlertSection from "../components/alerts/AlertSection";
import AlertRow from "../components/alerts/AlertRow";
import HowAlertsWorkCard from "../components/alerts/HowAlertsWorkCard";
import { IconPlus } from "../components/icons";

export default function AlertsPage() {
  const { data: rawAlerts, loading, setData: setAlerts, refetch } = useAsync(() => alertsApi.getAlerts(), []);
  const alerts = rawAlerts || [];

  const toggle = async (id) => {
    const current = alerts.find((a) => a.id === id);
    if (!current) return;
    const nextStatus = current.status === "paused" ? "active" : "paused";

    // Optimistic update
    setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, status: nextStatus } : a)));

    if (!USE_MOCK) {
      try {
        await alertsApi.toggleAlert(id, nextStatus);
      } catch (e) {
        console.error("Failed to toggle alert, reverting:", e);
        refetch();
      }
    }
  };

  const remove = async (id) => {
    // Optimistic update
    setAlerts((prev) => prev.filter((a) => a.id !== id));

    if (!USE_MOCK) {
      try {
        await alertsApi.deleteAlert(id);
      } catch (e) {
        console.error("Failed to delete alert, reverting:", e);
        refetch();
      }
    }
  };

  const edit = () => {};

  const active = alerts.filter((a) => a.status === "active");
  const triggered = alerts.filter((a) => a.status === "triggered");
  const paused = alerts.filter((a) => a.status === "paused");

  return (
    <div className="sv2">
      <div className="sv2-page alr-page">
        <div className="alr-page-head">
          <div>
            <h1 className="sv2-h1">Alerts</h1>
            <p className="sv2-lead">Threshold rules that watch the market so you don't have to.</p>
          </div>
          <button className="alr-new-btn">
            <IconPlus /> New alert
          </button>
        </div>

        {loading ? (
          <div className="sv2-muted sv2-small">Loading alerts…</div>
        ) : (
          <div className="alr-flex-col">
            <AlertSection title="Active" count={active.length} subtitle="Watching in the background">
              {active.map((a) => (
                <AlertRow key={a.id} alert={a} onToggle={toggle} onEdit={edit} onDelete={remove} />
              ))}
            </AlertSection>

            <AlertSection
              title="Triggered"
              count={triggered.length}
              subtitle="Fired — review and re-arm if still relevant"
            >
              {triggered.map((a) => (
                <AlertRow key={a.id} alert={a} onToggle={toggle} onEdit={edit} onDelete={remove} />
              ))}
            </AlertSection>

            <AlertSection title="Paused" count={paused.length} subtitle="Kept, but not evaluated">
              {paused.map((a) => (
                <AlertRow key={a.id} alert={a} onToggle={toggle} onEdit={edit} onDelete={remove} />
              ))}
            </AlertSection>

            <HowAlertsWorkCard />
          </div>
        )}
      </div>
    </div>
  );
}