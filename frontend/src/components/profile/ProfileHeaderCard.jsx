export default function ProfileHeaderCard({ profile, editing, onChange }) {
  if (!profile) return null;

  const memberSince = profile.memberSince ? new Date(profile.memberSince).toISOString().slice(0, 10) : "";

  return (
    <div className="sv2-card set-subcard prof-identity-card">
      <div className="prof-identity-top">
        <div className="prof-avatar" style={{ background: profile.avatarColor }}>
          {profile.avatarInitials}
        </div>
        <div className="prof-identity-text">
          {editing ? (
            <input
              className="set-input prof-name-input"
              value={profile.name}
              onChange={(e) => onChange({ name: e.target.value })}
            />
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
        </div>
        <div>
          <div className="prof-meta-label">Markets followed</div>
          <div className="prof-meta-value">{profile.marketsFollowed || "—"}</div>
        </div>
      </div>
    </div>
  );
}