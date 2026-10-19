import { useState } from "react";
import { useAsync } from "../../hooks/useAsync";
import { dashboardApi } from "../../services/dashboardApi";
import { IconFileText, IconSparkle } from "../icons";
import { ErrorState, useToast } from "../../errors";
import { downloadReport } from "../../services/reportApi";
import PortfolioAnalysisModal from "./PortfolioAnalysisModal";
import AddHoldingModal from "../portfolio/AddHoldingModal";

export default function DashboardHeroHeader() {
  const { data: user, error, refetch } = useAsync(() => dashboardApi.getCurrentUser(), []);
  const userName = user?.name ?? null;
  const toast = useToast();
  const [generating, setGenerating] = useState(false);
  const [analysing, setAnalysing] = useState(false);
  const [adding, setAdding] = useState(false);

  const handleGenerateReport = async () => {
    setGenerating(true);
    try {
      await downloadReport();
      toast.success("Your report was saved. Open it in a browser, or print it to PDF.", { title: "Report ready" });
    } catch (e) {
      toast.error(e, { title: "Couldn't generate the report" });
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="dv2-hero">
      <div>
        <h1 className="dv2-hero-title">Market overview</h1>
        <p className="dv2-hero-sub">
          {userName
            ? `${userName.split(" ")[0]}, here's how your markets look right now.`
            : "Here's how your markets look right now."}
        </p>
        {error && (
          <ErrorState error={error} onRetry={refetch} title="Couldn't load your profile" message="Your name may be missing from this greeting." />
        )}
      </div>
      <div className="dv2-hero-actions">
        <button className="dv2-btn-ghost" type="button" onClick={handleGenerateReport} disabled={generating}>
          <IconFileText size={14} />
          {generating ? "Generating…" : "Generate report"}
        </button>
        <button className="dv2-btn-accent" type="button" onClick={() => setAnalysing(true)}>
          <IconSparkle size={14} />
          AI analysis
        </button>
      </div>
      {analysing && <PortfolioAnalysisModal onClose={() => setAnalysing(false)} onAddHolding={() => setAdding(true)} />}
      {adding && <AddHoldingModal onClose={() => setAdding(false)} />}
    </div>
  );
}