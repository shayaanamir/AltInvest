import { IconChart, IconBars, IconEye, IconCompass, IconPie } from "../icons";
import { togglePick } from "../../utils/onboardingPayload";
import OptionCard from "./OptionCard";
import StepHead from "./StepHead";

// Keys match the backend's goal set (routes/profile.py _VALID_GOALS) and the Profile page.
const GOALS = [
  { key: "longterm", title: "Long-term investing", desc: "Build wealth steadily over years.", icon: <IconChart size={20} /> },
  { key: "trading", title: "Active trading", desc: "Act on shorter-term moves.", icon: <IconBars size={20} /> },
  { key: "research", title: "Deep research", desc: "Dig into fundamentals, sentiment and risk.", icon: <IconEye size={20} /> },
  { key: "discovery", title: "Market discovery", desc: "Find new narratives and early trends.", icon: <IconCompass size={20} /> },
  { key: "portfolio", title: "Portfolio balance", desc: "Spread risk across what you hold.", icon: <IconPie size={20} /> },
];

export default function Step3Goals({ answers, setAnswer }) {
  const chosen = answers.goals || [];

  return (
    <>
      <StepHead
        eyebrow="Goals"
        title="What are you here for?"
        sub="Pick everything that applies. Your first pick is your primary goal and appears on your profile."
      />
      <div className="ob-grid cols-3" role="group" aria-label="Goals">
        {GOALS.map((g) => (
          <OptionCard
            key={g.key}
            selected={chosen.includes(g.key)}
            onClick={() => setAnswer("goals", togglePick(chosen, g.key, GOALS.length))}
            icon={g.icon}
            title={g.title}
            badge={chosen[0] === g.key ? "Primary" : undefined}
            desc={g.desc}
          />
        ))}
      </div>
    </>
  );
}
