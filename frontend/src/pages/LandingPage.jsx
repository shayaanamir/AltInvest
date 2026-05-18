import LandingNav from "../components/landingPage/LandingNav";
import Hero from "../components/landingPage/Hero";
import DashboardMockup from "../components/landingPage/DashboardMockup";
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
            position: "relative",
        }}>
            <div style={{ position: "relative", zIndex: 1 }}>
                <LandingNav onNavigate={onNavigate} />
                <Hero onNavigate={onNavigate} />
                <div style={{ display: "flex", justifyContent: "center", padding: "0 48px 80px" }}>
                    <DashboardMockup />
                </div>
                <SocialProof />
                <Features />
                <StatsStrip />
                <PlatformPreview />
                <CTA onNavigate={onNavigate} />
                <LandingFooter />
            </div>
        </div>
    );
}