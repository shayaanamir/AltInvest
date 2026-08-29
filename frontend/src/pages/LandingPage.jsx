import LandingNav from "../components/landingPage/LandingNav";
import Hero from "../components/landingPage/Hero";
import PlatformSurfaces from "../components/landingPage/PlatformSurfaces";
import ScoreShowcase from "../components/landingPage/ScoreShowcase";
import CapabilitiesGrid from "../components/landingPage/CapabilitiesGrid";
import CTA from "../components/landingPage/CTA";
import LandingFooter from "../components/landingPage/LandingFooter";
import "../styles/landing.css";

export default function LandingPage({ onNavigate }) {
    return (
        <div className="sv2 lp2-root">
            <LandingNav onNavigate={onNavigate} />

            <div id="home">
                <Hero onNavigate={onNavigate} />
            </div>

            <div id="platform">
                <PlatformSurfaces />
            </div>

            <div id="analytics">
                <ScoreShowcase />
            </div>

            <div id="capabilities">
                <CapabilitiesGrid />
            </div>

            <div id="access">
                <CTA onNavigate={onNavigate} />
            </div>

            <LandingFooter />
        </div>
    );
}