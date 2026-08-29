import systemStates from "../../data/sample_data/systemStates.json";

export default function SessionExpiredModal({ onConfirm }) {
    const { title, subtitle, cta } = systemStates.sessionExpired;

    return (
        <div className="sv2-modal-overlay">
            <div className="sv2-modal" style={{ maxWidth: 380, padding: "28px 26px", textAlign: "center" }}>
                <h3 style={{ fontSize: 17, fontWeight: 800, color: "var(--sv2-text)", margin: "0 0 8px" }}>
                    {title}
                </h3>
                <p style={{ fontSize: 13, color: "var(--sv2-text-soft)", lineHeight: 1.55, margin: "0 0 20px" }}>
                    {subtitle}
                </p>
                <button
                    className="sv2-btn-primary"
                    style={{ width: "100%" }}
                    onClick={onConfirm}
                >
                    {cta}
                </button>
            </div>
        </div>
    );
}