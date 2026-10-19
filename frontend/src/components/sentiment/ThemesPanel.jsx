import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../errors";
import { sentimentApi } from "../../services/sentimentApi";
import { IconArrowUpRight, IconArrowDownRight } from "../icons";

export default function ThemesPanel() {
  const { data, error, refetch } = useAsync(() => sentimentApi.getThemes(), []);
  const themes = data || [];

  return (
    <div className="sv2-card sv2-card-pad-sm">
      <div className="sv2-card-title" style={{ marginBottom: 4 }}>Themes people keep coming back to</div>
      {error && <ErrorState error={error} onRetry={refetch} title="Couldn't load themes" />}
      {!error && data && themes.length === 0 && <div className="sv2-muted sv2-small sv2-mt-12">No themes have been recorded yet.</div>}
      <div className="sv2-chip-row sv2-mt-12">
        {themes.map((t) => (
          <span key={t.label} className={`sv2-theme-pill ${t.direction}`}>
            {t.direction === "up" ? <IconArrowUpRight size={11} /> : <IconArrowDownRight size={11} />}
            {t.label}
          </span>
        ))}
      </div>
    </div>
  );
}