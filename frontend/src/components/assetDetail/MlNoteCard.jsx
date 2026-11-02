import { isMlUncertain } from "../../utils/scoring";

/** The ML service's own note for this asset (from the backend's daily pull). Hidden when none is stored. */
export default function MlNoteCard({ mlSignal, mlNote }) {
  if (!mlNote) return null;
  return (
    <div className="sv2-card adt-about-card">
      <div className="sv2-card-title adt-mb-10">
        Model forecast{isMlUncertain(mlSignal) ? ": no reliable direction forecast" : ""}
      </div>
      <p className="adt-about-text">{mlNote}</p>
    </div>
  );
}
