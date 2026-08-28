import { motion } from "framer-motion";
import { useScrollReveal } from "./landingAnimations";

export default function CTA({ onNavigate }) {
  const { ref, inView } = useScrollReveal();

  return (
    <section className="lp2-cta-wrap">
      <motion.div
        ref={ref}
        initial={{ opacity: 0, y: 24 }}
        animate={inView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        className="lp2-cta-box"
      >
        <h2 className="lp2-cta-title">Start with one screen instead of five tabs.</h2>
        <p className="lp2-cta-desc">
          Create an account, tell AltInvest what you care about, and get a
          dashboard that already knows your markets.
        </p>
        <div className="lp2-cta-actions">
          <button className="lp2-cta-btn-primary" onClick={() => onNavigate && onNavigate("Signup")}>
            Get access
          </button>
          <button className="lp2-cta-btn-outline" onClick={() => onNavigate && onNavigate("Login")}>
            Sign in
          </button>
        </div>
      </motion.div>
    </section>
  );
}