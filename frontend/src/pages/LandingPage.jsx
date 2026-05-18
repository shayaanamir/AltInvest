import LandingNav from "../components/landingPage/LandingNav";
import Hero from "../components/landingPage/Hero";
import Features from "../components/landingPage/Features";
import PlatformPreview from "../components/landingPage/PlatformPreview";
import CTA from "../components/landingPage/CTA";
import LandingFooter from "../components/landingPage/LandingFooter";
import DashboardMockup from "@/components/landingPage/DashboardMockup";

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
                <div id="home">
                    <Hero onNavigate={onNavigate} />
                </div>
                <div id="platform" style={{
                    display: "flex", alignItems: "center", justifyContent: "center",
                    minHeight: "100vh", padding: "60px 48px 0", boxSizing: "border-box",
                }}>
                    <DashboardMockup />
                </div>
                <div id="analytics">
                    <Features />
                </div>
                <div id="capabilities">
                    <PlatformPreview />
                </div>
                <div id="access">
                    <CTA onNavigate={onNavigate} />
                </div>
                <LandingFooter />
            </div>
        </div>
    );
}