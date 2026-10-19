import { useState } from "react";
import { useNavigate } from "react-router-dom";
import AddHoldingModal from "./AddHoldingModal";
import { IconColumns, IconPlus } from "../icons";

export default function PortfolioHeader() {
  const navigate = useNavigate();
  const [adding, setAdding] = useState(false);

  return (
    <div className="dv2-hero">
      <div>
        <h1 className="dv2-hero-title">Portfolio</h1>
        <p className="dv2-hero-sub">Everything you own, and the context it gives every other screen.</p>
      </div>
      <div className="dv2-hero-actions">
        <button className="dv2-btn-ghost" type="button" onClick={() => navigate("/compare")}>
          <IconColumns size={14} />
          Compare holdings
        </button>
        <button className="dv2-btn-accent" type="button" onClick={() => setAdding(true)}>
          <IconPlus size={14} />
          Add holding
        </button>
      </div>
      {adding && <AddHoldingModal onClose={() => setAdding(false)} />}
    </div>
  );
}