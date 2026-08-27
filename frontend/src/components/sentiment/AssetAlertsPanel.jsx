import { useState } from "react";
import { IconTrash } from "./icons";

const OPTIONS = [
  "When the score crosses 60",
  "When the score crosses 70",
  "When confidence drops below medium",
  "When trend reverses",
];

export default function AssetAlertsPanel() {
  const [choice, setChoice] = useState(OPTIONS[0]);
  const [alerts, setAlerts] = useState([{ id: 1, label: "Score drops below 60" }]);

  const addAlert = () => {
    setAlerts((a) => [...a, { id: Date.now(), label: choice }]);
  };

  const removeAlert = (id) => setAlerts((a) => a.filter((x) => x.id !== id));

  return (
    <div className="sv2-card sv2-card-pad-sm">
      <div className="sv2-card-title" style={{ marginBottom: 12 }}>Alerts</div>
      <div className="sv2-tiny sv2-mute2 sv2-mb-8">Let me know…</div>
      <select className="sv2-select" value={choice} onChange={(e) => setChoice(e.target.value)}>
        {OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
      <button className="sv2-btn-outline sv2-mt-8" style={{ width: "100%" }} onClick={addAlert}>Set alert</button>

      <div className="sv2-mt-12">
        {alerts.map((a) => (
          <div key={a.id} className="sv2-alert-row">
            <span>{a.label}</span>
            <button className="sv2-trash-btn" onClick={() => removeAlert(a.id)}><IconTrash /></button>
          </div>
        ))}
      </div>
    </div>
  );
}