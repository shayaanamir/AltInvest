import { useState } from "react";
import "../styles/settingsProfile.css";
import { useAsync } from "../hooks/useAsync";
import { profileApi } from "../services/profileApi";
import { authApi } from "../services/authApi";
import ProfileHeaderCard, { NAME_MAX } from "../components/profile/ProfileHeaderCard";
import ActivityCard from "../components/profile/ActivityCard";
import InvestmentProfileCard from "../components/profile/InvestmentProfileCard";
import { ErrorState, useToast, describeError } from "../errors";

function validateName(name) {
  const trimmed = (name || "").trim();
  if (!trimmed) return "Name can't be empty.";
  if (trimmed.length > NAME_MAX) return `Name must be ${NAME_MAX} characters or fewer.`;
  return null;
}

export default function ProfilePage() {
  const toast = useToast();
  const { data: profile, loading, error, refetch, setData: setProfile } = useAsync(() => profileApi.getProfile(), []);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [beforeEdit, setBeforeEdit] = useState(null); // what Cancel restores
  const [resending, setResending] = useState(false);

  const nameError = editing ? validateName(profile?.name) : null;

  const applyChange = (patch) => setProfile((p) => ({ ...p, ...patch }));

  const startEditing = () => {
    setBeforeEdit(profile);
    setSaveError(null);
    setEditing(true);
  };

  const cancelEditing = () => {
    if (beforeEdit) setProfile(beforeEdit);
    setSaveError(null);
    setEditing(false);
  };

  const handleSave = async () => {
    if (nameError) return;
    setSaving(true);
    setSaveError(null);
    try {
      const saved = await profileApi.updateProfile(profile);
      setProfile((p) => ({ ...p, ...saved }));
      setEditing(false);
      toast.success("Profile saved");
    } catch (e) {
      // Shown beside the form as well as in a toast, and the edits stay so nothing is lost.
      setSaveError(describeError(e).message);
      toast.error(e, { title: "Couldn't save your profile" });
    } finally {
      setSaving(false);
    }
  };

  const handleResendVerification = async () => {
    setResending(true);
    try {
      const res = await authApi.resendVerification();
      if (res.already_verified) setProfile((p) => ({ ...p, emailVerified: true }));
      toast.success(res.message);
    } catch (e) {
      toast.error(e, { title: "Couldn't send the verification email" });
    } finally {
      setResending(false);
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
              <button className="sv2-btn-outline" style={{ width: "auto" }} onClick={cancelEditing} disabled={saving}>Cancel</button>
              <button className="set-btn-accent" onClick={handleSave} disabled={saving || !!nameError}>{saving ? "Saving…" : "Save"}</button>
            </div>
          ) : (
            profile && <button className="set-btn-accent" onClick={startEditing}>✎ Edit profile</button>
          )}
        </div>

        {saveError && <p className="prof-save-error" role="alert">Couldn't save: {saveError}</p>}

        {error ? (
          <div className="sv2-card set-subcard">
            <ErrorState error={error} onRetry={refetch} variant="panel" title="Couldn't load your profile" />
          </div>
        ) : loading || !profile ? (
          <div className="sv2-card set-subcard sv2-muted sv2-small">Loading profile…</div>
        ) : (
          <>
            <div className="prof-top-grid">
              <ProfileHeaderCard
                profile={profile}
                editing={editing}
                onChange={applyChange}
                nameError={nameError}
                onResendVerification={handleResendVerification}
                resending={resending}
              />
              <ActivityCard activitySummary={profile.activitySummary} />
            </div>
            <InvestmentProfileCard profile={profile} editing={editing} onChange={applyChange} />
          </>
        )}
      </div>
    </div>
  );
}
