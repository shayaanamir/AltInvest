import { useEffect, useMemo, useState } from "react";
import { useAsync } from "../../hooks/useAsync";
import { alertsApi } from "../../services/alertsApi";
import { fetchUniverse } from "../../services/assetRepository";
import { ALERT_METRIC_OPTIONS, ALERT_CONDITION_OPTIONS } from "../../content/uiOptions";
import { formatUsd } from "../../utils/formatters";
import { ErrorState, useToast } from "../../errors";
import "../portfolio/addHoldingModal.css";

const CHANNELS = [
  { key: "in-app", label: "In-app" },
  { key: "push", label: "Push" },
  { key: "email", label: "Email" },
];

/**
 * Create or edit an alert rule.
 *   Create, target known:   <CreateAlertModal target={{ type, symbol|slug, name }} hint? />
 *   Create, pick a target:  <CreateAlertModal />               (shows a search over the covered universe)
 *   defaults={{ metric, condition }} opens a create dialog pre-set to that rule.
 *   Edit:                   <CreateAlertModal alert={alert} />  (target and metric are fixed; condition,
 *                                                                threshold and delivery channel can change)
 * Calls onCreated() after a successful save, then closes. Failures stay in the dialog as a toast.
 */
export default function CreateAlertModal({ target: fixedTarget, alert, hint, defaults, onClose, onCreated }) {
  const toast = useToast();
  const editing = !!alert;

  const [picked, setPicked] = useState(null);
  const [query, setQuery] = useState("");
  const needsPicker = !editing && !fixedTarget;
  const { data: universe, loading, error: universeError, refetch } = useAsync(
    () => (needsPicker ? fetchUniverse({ category: "all", sort: "name", order: "asc" }) : Promise.resolve([])),
    [needsPicker]
  );

  const [metric, setMetric] = useState(alert?.metricType ?? defaults?.metric ?? "price");
  const [condition, setCondition] = useState(alert?.condition ?? defaults?.condition ?? "above");
  const [threshold, setThreshold] = useState(alert?.thresholdValue != null ? String(alert.thresholdValue) : "");
  const [channel, setChannel] = useState(alert?.deliveryChannel ?? "in-app");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && !submitting && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose, submitting]);

  const target = editing
    ? { type: alert.targetType, symbol: alert.targetSymbol, slug: alert.targetSlug, name: alert.name }
    : fixedTarget || (picked && { type: picked.type, symbol: picked.symbol, slug: picked.id, name: picked.name });

  const choices = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (universe || []).filter((u) => !q || u.name.toLowerCase().includes(q) || (u.symbol || "").toLowerCase().includes(q));
  }, [universe, query]);

  // "Shifts bullish / bearish" only means something for the sentiment metric.
  const conditions = ALERT_CONDITION_OPTIONS.filter((c) => metric === "sentiment" || !c.key.startsWith("shifts_"));
  const needsThreshold = condition === "above" || condition === "below";
  const metricLabel = ALERT_METRIC_OPTIONS.find((m) => m.key === metric)?.label ?? metric;

  const changeMetric = (next) => {
    setMetric(next);
    if (next !== "sentiment" && condition.startsWith("shifts_")) setCondition("above");
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!target) {
      setError("Choose what to watch.");
      return;
    }
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
      if (editing) {
        await alertsApi.updateAlert(alert.id, {
          condition,
          ...(value != null ? { threshold_value: value } : {}),
          delivery_channel: channel,
        });
      } else {
        await alertsApi.createAlert({
          target_type: target.type,
          ...(target.type === "nft" ? { target_slug: target.slug } : { target_symbol: target.symbol }),
          target_name: target.name,
          metric_type: metric,
          condition,
          ...(value != null ? { threshold_value: value } : {}),
          delivery_channel: channel,
        });
      }
    } catch (err) {
      toast.error(err, { title: editing ? "Couldn't save the alert" : "Couldn't create the alert" });
      setSubmitting(false);
      return;
    }
    if (editing) toast.success(`The alert on ${target.name} was updated.`, { title: "Alert saved" });
    else toast.success(`We'll watch ${target.name} for you. Manage it on the Alerts page.`, { title: "Alert created" });
    onCreated?.();
    onClose();
  };

  return (
    <div className="ahm-overlay" onClick={() => !submitting && onClose()}>
      <form
        className="ahm"
        role="dialog"
        aria-modal="true"
        aria-label={editing ? "Edit alert" : "New alert"}
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSubmit}
        noValidate
      >
        <div className="ahm-head">
          <h2>{editing ? "Edit alert" : "New alert"}</h2>
          <button type="button" className="ahm-close" aria-label="Close" onClick={onClose} disabled={submitting}>×</button>
        </div>
        <p className="ahm-desc">
          {target
            ? <>Get notified about <strong>{target.name}</strong> when this rule is met.</>
            : "Pick an asset or collection, then set the rule that should notify you."}
        </p>

        {needsPicker && (
          <>
            <label className="ahm-label">Asset or collection</label>
            <input
              className="ahm-input"
              placeholder="Search assets and collections"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              autoFocus
            />
            <div className="ahm-list">
              {universeError ? (
                <ErrorState error={universeError} onRetry={refetch} title="Couldn't load the asset list" />
              ) : loading ? (
                <div className="ahm-empty">Loading…</div>
              ) : choices.length === 0 ? (
                <div className="ahm-empty">{query ? "No matches." : "Nothing covered yet."}</div>
              ) : (
                choices.map((c) => (
                  <button
                    key={`${c.type}-${c.id}`}
                    type="button"
                    className={`ahm-item ${picked && picked.id === c.id && picked.type === c.type ? "selected" : ""}`}
                    onClick={() => { setPicked(c); setError(null); }}
                  >
                    <span className="ahm-dot" style={{ background: c.color || "var(--sv2-accent)" }}>
                      {(c.symbol || c.name).slice(0, 3).toUpperCase()}
                    </span>
                    <span className="ahm-item-main">
                      <span className="ahm-item-name">{c.name}</span>
                      <span className="ahm-item-sub">{c.type === "nft" ? "NFT collection" : c.subcategory}</span>
                    </span>
                    <span className="ahm-item-price">{c.priceLabel || formatUsd(c.price)}</span>
                  </button>
                ))
              )}
            </div>
          </>
        )}

        <label className="ahm-label">Watch</label>
        {editing ? (
          <div className="ahm-fixed">{metricLabel}</div>
        ) : (
          <select className="ahm-input" value={metric} onChange={(e) => changeMetric(e.target.value)}>
            {ALERT_METRIC_OPTIONS.map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}
          </select>
        )}

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
              autoFocus={!needsPicker}
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
          <button type="submit" className="ahm-submit" disabled={submitting}>
            {submitting ? "Saving…" : editing ? "Save changes" : "Create alert"}
          </button>
        </div>
      </form>
    </div>
  );
}
