import { useEffect, useState } from "react";
import { alertsApi } from "../../services/alertsApi";
import { ALERT_METRIC_OPTIONS, ALERT_CONDITION_OPTIONS } from "../../content/uiOptions";
import { useToast } from "../../errors";
import "../portfolio/addHoldingModal.css";

const CHANNELS = [
  { key: "in-app", label: "In-app" },
  { key: "push", label: "Push" },
  { key: "email", label: "Email" },
];

/**
 * Creates an alert rule for a known target (POST /alerts).
 *   target: { type: "crypto" | "nft", symbol?, slug?, name }
 *   hint:   optional line of context shown under the threshold (e.g. the current price)
 */
export default function CreateAlertModal({ target, hint, onClose, onCreated }) {
  const toast = useToast();
  const [metric, setMetric] = useState("price");
  const [condition, setCondition] = useState("above");
  const [threshold, setThreshold] = useState("");
  const [channel, setChannel] = useState("in-app");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && !submitting && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose, submitting]);

  // "Shifts bullish / bearish" only means something for the sentiment metric.
  const conditions = ALERT_CONDITION_OPTIONS.filter((c) => metric === "sentiment" || !c.key.startsWith("shifts_"));
  const needsThreshold = condition === "above" || condition === "below";

  const changeMetric = (next) => {
    setMetric(next);
    if (next !== "sentiment" && condition.startsWith("shifts_")) setCondition("above");
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    let value = null;
    if (needsThreshold) {
      value = Number(threshold);
      if (threshold === "" || !Number.isFinite(value) || (metric === "price" && value <= 0)) {
        setError(metric === "price" ? "Enter a price greater than 0." : "Enter a number for the threshold.");
        return;
      }
    }

    setSubmitting(true);
    try {
      await alertsApi.createAlert({
        target_type: target.type,
        ...(target.type === "nft" ? { target_slug: target.slug } : { target_symbol: target.symbol }),
        target_name: target.name,
        metric_type: metric,
        condition,
        ...(value != null ? { threshold_value: value } : {}),
        delivery_channel: channel,
      });
    } catch (err) {
      toast.error(err, { title: "Couldn't create the alert" });
      setSubmitting(false);
      return;
    }
    toast.success(`We'll watch ${target.name} for you. Manage it on the Alerts page.`, { title: "Alert created" });
    onCreated?.();
    onClose();
  };

  return (
    <div className="ahm-overlay" onClick={() => !submitting && onClose()}>
      <form
        className="ahm"
        role="dialog"
        aria-modal="true"
        aria-label={`Set an alert on ${target.name}`}
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSubmit}
        noValidate
      >
        <div className="ahm-head">
          <h2>Set an alert</h2>
          <button type="button" className="ahm-close" aria-label="Close" onClick={onClose} disabled={submitting}>×</button>
        </div>
        <p className="ahm-desc">Get notified about <strong>{target.name}</strong> when this rule is met.</p>

        <label className="ahm-label">Watch</label>
        <select className="ahm-input" value={metric} onChange={(e) => changeMetric(e.target.value)}>
          {ALERT_METRIC_OPTIONS.map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}
        </select>

        <label className="ahm-label">When it</label>
        <select className="ahm-input" value={condition} onChange={(e) => { setCondition(e.target.value); setError(null); }}>
          {conditions.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
        </select>

        {needsThreshold && (
          <>
            <label className="ahm-label">{metric === "price" ? "Price (USD)" : "Value"}</label>
            <input
              className="ahm-input"
              inputMode="decimal"
              placeholder={metric === "price" ? "e.g. 80000" : "e.g. 60"}
              value={threshold}
              onChange={(e) => { setThreshold(e.target.value); setError(null); }}
              autoFocus
            />
            {hint && <div className="ahm-hint">{hint}</div>}
          </>
        )}
        {error && <div className="ahm-field-error">{error}</div>}

        <label className="ahm-label">Notify me by</label>
        <select className="ahm-input" value={channel} onChange={(e) => setChannel(e.target.value)}>
          {CHANNELS.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
        </select>

        <div className="ahm-footer">
          <button type="button" className="ahm-cancel" onClick={onClose} disabled={submitting}>Cancel</button>
          <button type="submit" className="ahm-submit" disabled={submitting}>{submitting ? "Saving…" : "Create alert"}</button>
        </div>
      </form>
    </div>
  );
}
