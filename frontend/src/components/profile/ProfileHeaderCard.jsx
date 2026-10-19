import { formatDate, useAppPreferences } from "../../services/appPreferences";

export const NAME_MAX = 80;

export default function ProfileHeaderCard({ profile, editing, onChange, nameError, onResendVerification, resending }) {
  useAppPreferences(); // re-render when the date format changes
  if (!profile) return null;

  const memberSince = profile.memberSince ? formatDate(profile.memberSince) : "";

  return (
    <div className="sv2-card set-subcard prof-identity-card">
      <div className="prof-identity-top">
        <div className="prof-avatar" style={{ background: profile.avatarColor }}>
          {profile.avatarInitials}
        </div>
        <div className="prof-identity-text">
          {editing ? (
            <>
              <input
                className="set-input prof-name-input"
                value={profile.name}
                maxLength={NAME_MAX}
                aria-invalid={!!nameError}
                aria-describedby={nameError ? "prof-name-error" : undefined}
                onChange={(e) => onChange({ name: e.target.value })}
              />
              {nameError && <div id="prof-name-error" className="prof-field-error" role="alert">{nameError}</div>}
            </>
          ) : (
            <div className="prof-name">{profile.name}</div>
          )}
          <div className="prof-email">{profile.email}</div>
          {editing ? (
            <textarea
              className="set-input prof-bio-input"
              value={profile.bio}
              rows={2}
              onChange={(e) => onChange({ bio: e.target.value })}
            />
          ) : (
            <p className="prof-bio">{profile.bio}</p>
          )}
        </div>
      </div>

      <div className="prof-meta-row">
        <div>
          <div className="prof-meta-label">Member since</div>
          <div className="prof-meta-value">{memberSince}</div>
        </div>
        <div>
          <div className="prof-meta-label">Email status</div>
          <div className={`prof-meta-value ${profile.emailVerified ? "verified" : ""}`}>
            {profile.emailVerified ? "Verified" : "Unverified"}
          </div>
          {!profile.emailVerified && onResendVerification && (
            <button type="button" className="prof-verify-btn" onClick={onResendVerification} disabled={resending}>
              {resending ? "Sending…" : "Send verification email"}
            </button>
          )}
        </div>
        <div>
          <div className="prof-meta-label">Markets followed</div>
          <div className="prof-meta-value">{profile.marketsFollowed || "—"}</div>
        </div>
      </div>
    </div>
  );
}