import { useAsync } from "../../hooks/useAsync";
import { dashboardApi } from "../../services/dashboardApi";
import { IconFileText, IconSparkle } from "../icons";

export default function DashboardHeroHeader() {
  const { data: user } = useAsync(() => dashboardApi.getCurrentUser(), []);
  const userName = user?.name ?? null;

  return (
    <div className="dv2-hero">
      <div>
        <h1 className="dv2-hero-title">Market overview</h1>
        <p className="dv2-hero-sub">
          {userName
            ? `${userName.split(" ")[0]}, here's how your markets look right now.`
            : "Here's how your markets look right now."}
        </p>
      </div>
      <div className="dv2-hero-actions">
        <button className="dv2-btn-ghost" type="button">
          <IconFileText size={14} />
          Generate report
        </button>
        <button className="dv2-btn-accent" type="button">
          <IconSparkle size={14} />
          AI analysis
        </button>
      </div>
    </div>
  );
}