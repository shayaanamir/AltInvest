import { useState, useEffect } from "react";
import { sentimentApi } from "../../services/sentimentApi";
import { IconArrowUpRight, IconArrowDownRight } from "./icons";

export default function ThemesPanel() {
  const [themes, setThemes] = useState([]);

  useEffect(() => {
    sentimentApi.getThemes().then(setThemes).catch(console.error);
  }, []);

  return (
    <div className="sv2-card sv2-card-pad-sm">
      <div className="sv2-card-title" style={{ marginBottom: 4 }}>Themes people keep coming back to</div>
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