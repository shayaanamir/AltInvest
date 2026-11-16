import { useEffect, useState } from "react";
import SettingsRow from "./SettingsRow";
import { authApi } from "../../services/authApi";
import { getGoogleConfig, requestGoogleCode, GoogleCancelled } from "../../services/googleAuth";
import { describeError } from "../../errors/errorCatalog";

const LABELS = {
  google: { title: "Google", description: "Use Google to sign in" },
  wallet: { title: "Wallet", description: "Read-only address for holdings import" },
};

const messageOf = (err) => (err?.kind ? describeError(err).message : err?.message);

/** Google is real: linked or not is read from /auth/me, and changed through /auth/google/link|unlink. */
function GoogleRow() {
  const [me, setMe] = useState(null);
  const [enabled, setEnabled] = useState(null);
  const [busy, setBusy] = useState(false);
  const [askPassword, setAskPassword] = useState(false);
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState(null);

  useEffect(() => {
    let live = true;
    authApi.me().then((u) => live && setMe(u)).catch(() => {});
    getGoogleConfig().then((c) => live && setEnabled(c.enabled));
    return () => { live = false; };
  }, []);

  const refresh = () => authApi.me().then(setMe).catch(() => {});

  const connect = async () => {
    setBusy(true);
    setStatus(null);
    try {
      const code = await requestGoogleCode();
      const res = await authApi.linkGoogle(code);
      setStatus({ type: "success", message: res.google_email ? `Connected ${res.google_email}.` : res.message });
      await refresh();
    } catch (err) {
      if (!(err instanceof GoogleCancelled)) setStatus({ type: "error", message: messageOf(err) });
    } finally {
      setBusy(false);
    }
  };

  const disconnect = async (e) => {
    e.preventDefault();
    if (!password) return;
    setBusy(true);
    setStatus(null);
    try {
      await authApi.unlinkGoogle(password);
      setAskPassword(false);
      setPassword("");
      setStatus({ type: "success", message: "Google disconnected." });
      await refresh();
    } catch (err) {
      setStatus({ type: "error", message: messageOf(err) });
    } finally {
      setBusy(false);
    }
  };

  const linked = !!me?.google_linked;
  const description = linked
    ? `Signed in as ${me.google_email || "your Google account"}`
    : LABELS.google.description;
  // Without a password, Google is this account's only way in.
  const cantDisconnect = linked && me && !me.has_password;

  return (
    <>
      <SettingsRow title={LABELS.google.title} description={description}>
        {linked ? (
          <button
            className="set-btn-accent set-connect-btn"
            disabled={busy || cantDisconnect || askPassword}
            title={cantDisconnect ? "Set a password under Security first, so you can still sign in" : undefined}
            onClick={() => { setStatus(null); setAskPassword(true); }}
          >
            Disconnect
          </button>
        ) : (
          <button
            className="set-btn-accent set-connect-btn"
            disabled={busy || !me || enabled !== true}
            title={enabled === false ? "Google sign-in isn't set up on this server" : undefined}
            onClick={connect}
          >
            {busy ? "Connecting…" : "Connect"}
          </button>
        )}
      </SettingsRow>

      {askPassword && (
        <form className="set-delete-confirm" onSubmit={disconnect}>
          <label className="set-field">
            <span>Enter your password to disconnect Google</span>
            <input
              className="set-input"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoFocus
            />
          </label>
          <div className="set-delete-actions">
            <button type="submit" className="set-btn-accent" disabled={!password || busy}>
              {busy ? "Disconnecting…" : "Disconnect Google"}
            </button>
            <button
              type="button"
              className="sv2-btn-outline"
              style={{ width: "auto" }}
              disabled={busy}
              onClick={() => { setAskPassword(false); setPassword(""); }}
            >
              Cancel
            </button>
          </div>
        </form>
      )}
      {cantDisconnect && (
        <div className="set-row-desc">To disconnect Google, first set a password under Security.</div>
      )}
      {status && <div className={`set-form-status ${status.type}`}>{status.message}</div>}
    </>
  );
}

export default function ConnectedAccountsSection({ data, onChange }) {
  if (!data) return null;

  return (
    <div className="sv2-card set-content">
      <div className="set-section-head">
        <div className="set-section-title">Connected accounts</div>
        <div className="set-section-sub">Sign-in providers and wallet linking</div>
      </div>

      {Object.keys(data).map((key) => {
        if (key === "google") return <GoogleRow key={key} />;
        const acct = data[key];
        const meta = LABELS[key] || { title: key, description: "" };
        const isComingSoon = acct.status === "coming_soon" || acct.status === "proposed";
        return (
          <SettingsRow key={key} title={meta.title} description={meta.description}>
            <button
              className="set-btn-accent set-connect-btn"
              disabled={isComingSoon}
              title={isComingSoon ? "Coming soon" : undefined}
              onClick={() => onChange({ [key]: { ...acct, connected: !acct.connected } })}
            >
              {acct.connected ? "Disconnect" : "Connect"}
            </button>
          </SettingsRow>
        );
      })}
    </div>
  );
}
