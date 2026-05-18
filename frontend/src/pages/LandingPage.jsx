import NoiseSVG from "../components/landingPage/NoiseSVG";
import LandingNav from "../components/landingPage/LandingNav";
import Hero from "../components/landingPage/Hero";
import SocialProof from "../components/landingPage/SocialProof";
import Features from "../components/landingPage/Features";
import StatsStrip from "../components/landingPage/StatsStrip";
import PlatformPreview from "../components/landingPage/PlatformPreview";
import CTA from "../components/landingPage/CTA";
import LandingFooter from "../components/landingPage/LandingFooter";

export default function LandingPage({ onNavigate }) {
    return (
        <div style={{
            background: "#08090f",
            minHeight: "100vh",
            fontFamily: "'DM Sans', 'Segoe UI', sans-serif",
        }}>
            <NoiseSVG />
            <LandingNav onNavigate={onNavigate} />
            <Hero onNavigate={onNavigate} />
            <SocialProof />
            <Features />
            <StatsStrip />
            <PlatformPreview />
            <CTA onNavigate={onNavigate} />
            <LandingFooter />
        </div>
    );
}