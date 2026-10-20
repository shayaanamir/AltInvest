export default function HowAlertsWorkCard() {
  return (
    <div className="alr-card">
      <div className="alr-section-title">How alerts work</div>
      <p className="alr-howitworks-text">
        Each rule is evaluated against the same data behind the scores you see. When one fires it
        moves to Triggered, appears in your Notification Center, and links straight back to the
        asset that caused it. Delivery respects your notification preferences in Settings.
      </p>
    </div>
  );
}