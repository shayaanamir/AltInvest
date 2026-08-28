import SettingsRow from "./SettingsRow";

const LABELS = {
  google: { title: "Google", description: "Use Google to sign in" },
  github: { title: "GitHub", description: "Use GitHub to sign in" },
  wallet: { title: "Wallet", description: "Read-only address for holdings import" },
};

export default function ConnectedAccountsSection({ data, onChange }) {
  if (!data) return null;

  return (
    <div className="sv2-card set-content">
      <div className="set-section-head">
        <div className="set-section-title">Connected accounts</div>
        <div className="set-section-sub">Sign-in providers and wallet linking</div>
      </div>

      {Object.keys(data).map((key) => {
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