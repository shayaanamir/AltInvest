import { useState } from "react";
import "../styles/settingsProfile.css";
import { useAsync } from "../hooks/useAsync";
import { profileApi } from "../services/profileApi";
import ProfileHeaderCard from "../components/profile/ProfileHeaderCard";
import ActivityCard from "../components/profile/ActivityCard";
import InvestmentProfileCard from "../components/profile/InvestmentProfileCard";

export default function ProfilePage() {
  const { data: profile, setData: setProfile } = useAsync(() => profileApi.getProfile(), []);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  const applyChange = (patch) => setProfile((p) => ({ ...p, ...patch }));

  const handleSave = async () => {
    setSaving(true);
    try {
      const saved = await profileApi.updateProfile(profile);
      // Merge rather than fully replace — the backend response may omit
      // fields (like marketsFollowed) the mock still carries.
      setProfile((p) => ({ ...p, ...saved }));
      setEditing(false);
    } catch (e) {
      console.error("Failed to save profile:", e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="sv2">
      <div className="sv2-page">
        <div className="set-header">
          <div>
            <h1 className="sv2-h1" style={{ marginTop: 0 }}>Profile</h1>
            <p className="sv2-lead">Who you are in AltInvest, and what you've built up so far.</p>
          </div>
          {editing ? (
            <div style={{ display: "flex", gap: 8 }}>
              <button className="sv2-btn-outline" style={{ width: "auto" }} onClick={() => setEditing(false)} disabled={saving}>Cancel</button>
              <button className="set-btn-accent" onClick={handleSave} disabled={saving}>{saving ? "Saving…" : "Save"}</button>
            </div>
          ) : (
            <button className="set-btn-accent" onClick={() => setEditing(true)}>✎ Edit profile</button>
          )}
        </div>

        {!profile ? (
          <div className="sv2-card set-subcard sv2-muted sv2-small">Loading profile…</div>
        ) : (
          <>
            <div className="prof-top-grid">
              <ProfileHeaderCard profile={profile} editing={editing} onChange={applyChange} />
              <ActivityCard activitySummary={profile.activitySummary} />
            </div>
            <InvestmentProfileCard profile={profile} editing={editing} onChange={applyChange} />
          </>
        )}
      </div>
    </div>
  );
}