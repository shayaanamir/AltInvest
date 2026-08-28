import { useState } from "react";

function formatLastActive(iso) {
  if (!iso) return "";
  const diffMin = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 60000));
  if (diffMin < 2) return "active now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const hrs = Math.floor(diffMin / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function SecuritySection({ data }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [status, setStatus] = useState(null);
  const [sessions, setSessions] = useState(data?.activeSessions || []);

  if (!data) return null;

  const handleUpdatePassword = (e) => {
    e.preventDefault();
    if (!current || !next || !confirm) {
      setStatus({ type: "error", message: "Fill in all three fields." });
      return;
    }
    if (next !== confirm) {
      setStatus({ type: "error", message: "New password and confirmation don't match." });
      return;
    }
    setStatus({ type: "success", message: "Password updated." });
    setCurrent(""); setNext(""); setConfirm("");
  };

  const logOutOthers = () => setSessions((s) => s.filter((sess) => sess.current));

  return (
    <>
      <div className="sv2-card set-subcard">
        <div className="set-section-title">Change password</div>
        <form onSubmit={handleUpdatePassword}>
          <div className="set-password-grid">
            <label className="set-field">
              <span>Current</span>
              <input className="set-input" type="password" value={current} onChange={(e) => setCurrent(e.target.value)} />
            </label>
            <label className="set-field">
              <span>New</span>
              <input className="set-input" type="password" value={next} onChange={(e) => setNext(e.target.value)} />
            </label>
            <label className="set-field">
              <span>Confirm</span>
              <input className="set-input" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
            </label>
          </div>
          {status && <div className={`set-form-status ${status.type}`}>{status.message}</div>}
          <button type="submit" className="set-btn-accent">Update password</button>
        </form>
      </div>

      <div className="sv2-card set-subcard">
        <div className="set-section-title">Active sessions</div>
        <div className="set-sessions">
          {sessions.map((s) => (
            <div key={s.id} className="set-session-row">
              <div className="set-session-device">
                {s.device}
                {s.current && <span className="sv2-tag-held" style={{ marginLeft: 8 }}>This device</span>}
              </div>
              <div className="set-session-meta">{s.location} · {formatLastActive(s.lastActive)}</div>
            </div>
          ))}
        </div>
        {sessions.length > 1 && (
          <button className="sv2-btn-outline set-mt-8" style={{ width: "auto" }} onClick={logOutOthers}>
            Log out of other sessions
          </button>
        )}
      </div>

      <div className="sv2-card set-subcard set-2fa-row">
        <div>
          <div className="set-section-title">Two-factor authentication</div>
          <div className="set-row-desc">Authenticator-app support is in build — we'll prompt you when it ships.</div>
        </div>
        <span className="set-pill-muted">
          {data.twoFactorStatus === "coming_soon" ? "Coming soon" : data.twoFactorEnabled ? "Enabled" : "Disabled"}
        </span>
      </div>
    </>
  );
}