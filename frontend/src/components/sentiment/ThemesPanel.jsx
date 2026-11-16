import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../errors";
import { sentimentApi } from "../../services/sentimentApi";
import { relativeTime } from "../../utils/dateTime";
import { IconArrowUpRight, IconArrowDownRight } from "../icons";

// Themes are named by an LLM from the real headlines the sentiment engines read; each is backed by at least
// two of them. Hovering a theme lists the headlines behind it.
export default function ThemesPanel() {
  const { data, error, refetch } = useAsync(() => sentimentApi.getThemes(), []);
  const themes = data || [];
  const generatedAt = themes.find((t) => t.generatedAt)?.generatedAt;

  return (
    <div className="sv2-card sv2-card-pad-sm">
      <div className="sv2-card-title" style={{ marginBottom: 4 }}>Themes people keep coming back to</div>
      {error && <ErrorState error={error} onRetry={refetch} title="Couldn't load themes" />}
      {!error && data && themes.length === 0 && (
        <div className="sv2-muted sv2-small sv2-mt-12">No recurring themes in this week's headlines yet.</div>
      )}
      <div className="sv2-chip-row sv2-mt-12">
        {themes.map((t) => (
          <span
            key={t.label}
            className={`sv2-theme-pill ${t.direction}`}
            title={t.headlines.length ? `${t.count} headlines, e.g.:\n• ${t.headlines.join("\n• ")}` : undefined}
          >
            {t.direction === "up" ? <IconArrowUpRight size={11} /> : <IconArrowDownRight size={11} />}
            {t.label}
            {t.count ? <span className="sv2-mute2"> · {t.count}</span> : null}
          </span>
        ))}
      </div>
      {themes.length > 0 && (
        <div className="sv2-tiny sv2-mute2 sv2-mt-12">
          Named by an LLM from this week's real headlines; the number is how many headlines back each theme.
          {generatedAt ? ` Updated ${relativeTime(generatedAt)}.` : ""}
        </div>
      )}
    </div>
  );
}
