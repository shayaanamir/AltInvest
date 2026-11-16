import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { IconTrash, IconDownload } from "../icons";
import { authApi } from "../../services/authApi";
import { clearSession } from "../../hooks/useAuth";
import { resetAppPreferences } from "../../services/appPreferences";
import { useToast, describeError } from "../../errors";

// Quote a CSV cell when it holds a comma, quote or newline. Text starting with = + - @ would be run as
// a formula by spreadsheets, so those get a leading apostrophe (numbers are left alone).
const cell = (v) => {
  let s = String(v ?? "");
  if (typeof v === "string" && /^[=+\-@\t\r]/.test(s)) s = `'${s}`;
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

// Nested fields become dotted columns ({ quiet_hours: { start } } -> "quiet_hours.start"); lists are
// written as JSON in one cell.
function flatten(obj, prefix = "", out = {}) {
  Object.entries(obj ?? {}).forEach(([k, v]) => {
    const key = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === "object" && !Array.isArray(v)) flatten(v, key, out);
    else out[key] = Array.isArray(v) ? JSON.stringify(v) : v;
  });
  return out;
}

// One section per stored collection, each with its own header row, separated by a blank line.
function section(title, records) {
  const rows = records.map((r) => flatten(r));
  const columns = [...new Set(rows.flatMap((r) => Object.keys(r)))];
  const lines = [cell(title), columns.map(cell).join(",")];
  rows.forEach((r) => lines.push(columns.map((c) => cell(r[c])).join(",")));
  return lines.join("\n");
}

// The server export as CSV: the account record first, then every collection it returned.
function toCsv(data) {
  const { account, ...collections } = data;
  delete collections.exported_at;
  return [
    section("account", account ? [account] : []),
    ...Object.entries(collections).map(([name, rows]) => section(name, Array.isArray(rows) ? rows : [])),
  ].join("\n\n");
}

export default function DataAccountSection({ data }) {
  const [confirming, setConfirming] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [password, setPassword] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState(null);
  const [exporting, setExporting] = useState(false);
  // Accounts made with Google may have no password to re-enter.
  const [hasPassword, setHasPassword] = useState(true);

  useEffect(() => {
    let live = true;
    authApi.me().then((u) => live && setHasPassword(u.has_password !== false)).catch(() => {});
    return () => { live = false; };
  }, []);
  const toast = useToast();
  const navigate = useNavigate();

  if (!data) return null;

  // The server assembles the export from everything stored for this account (GET /account/export).
  const handleExport = async (format) => {
    setExporting(true);
    let payload;
    try {
      payload = await authApi.exportData();
    } catch (e) {
      toast.error(e, { title: "Couldn't export your data" });
      return;
    } finally {
      setExporting(false);
    }
    const content = format === "JSON" ? JSON.stringify(payload, null, 2) : toCsv(payload);
    const blob = new Blob([content], { type: format === "JSON" ? "application/json" : "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `altinvest-export.${format.toLowerCase()}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const requiredPhrase = data.accountDeletion?.confirmationPhrase || "DELETE";
  const canDelete = confirmText.trim() === requiredPhrase && (!hasPassword || !!password) && !deleting;

  const cancelDelete = () => {
    setConfirming(false); setConfirmText(""); setPassword(""); setDeleteError(null);
  };

  const handleDelete = async (e) => {
    e.preventDefault();
    if (!canDelete) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await authApi.deleteAccount(password);
    } catch (err) {
      setDeleteError(describeError(err).message);
      setDeleting(false);
      return;
    }
    // The server has already ended every session; just forget this one locally.
    clearSession();
    resetAppPreferences();
    toast.success("Your account and all its data have been deleted.");
    navigate("/", { replace: true });
  };

  return (
    <>
      <div className="sv2-card set-subcard">
        <div className="set-section-title">Export your data</div>
        <div className="set-row-desc set-mb-16">Everything we store for your account: profile, settings, holdings, watchlists, alerts and notifications</div>
        <div className="set-export-row">
          {(data.exportFormats || []).map((fmt) => (
            <button key={fmt} className="sv2-btn-outline set-export-btn" disabled={exporting} onClick={() => handleExport(fmt)}>
              <IconDownload size={14} /> Export {fmt}
            </button>
          ))}
        </div>
      </div>


      <div className="sv2-card set-subcard">
        <div className="set-section-title" style={{ color: "var(--sv2-red)" }}>Delete account</div>
        <div className="set-row-desc set-mb-16">Permanent — requires a typed confirmation</div>

        {!confirming ? (
          <button className="set-btn-danger" onClick={() => setConfirming(true)}>
            <IconTrash size={14} /> Delete account
        </button>
        ) : (
          <form className="set-delete-confirm" onSubmit={handleDelete}>
            <p className="set-row-desc">
              This permanently deletes your holdings, watchlists, alerts, notifications and settings, and
              signs you out everywhere. It can't be undone.
            </p>
            <label className="set-field">
              <span>Type <strong>{requiredPhrase}</strong> to confirm</span>
              <input
                className="set-input"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                placeholder={requiredPhrase}
                autoComplete="off"
              />
            </label>
            {hasPassword && <label className="set-field">
              <span>Your password</span>
              <input
                className="set-input"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>}
            {deleteError && <div className="set-form-status error">{deleteError}</div>}
            <div className="set-delete-actions">
              <button type="submit" className="set-btn-danger" disabled={!canDelete}>
                {deleting ? "Deleting…" : "Confirm delete"}
              </button>
              <button type="button" className="sv2-btn-outline" style={{ width: "auto" }} disabled={deleting} onClick={cancelDelete}>
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>
    </>
  );
}