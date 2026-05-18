export default function NoiseSVG() {
    return (
        <svg
            style={{
                position: "fixed", inset: 0, width: "100%", height: "100%",
                pointerEvents: "none", zIndex: 999, opacity: 0.025,
            }}
        >
            <filter id="ln">
                <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch" />
                <feColorMatrix type="saturate" values="0" />
            </filter>
            <rect width="100%" height="100%" filter="url(#ln)" />
        </svg>
    );
}