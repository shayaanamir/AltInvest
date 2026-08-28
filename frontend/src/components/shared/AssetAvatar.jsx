export default function AssetAvatar({ symbol, color, size = 38 }) {
  const initials = (symbol || "?").slice(0, 3).toUpperCase();
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: color || "var(--sv2-accent)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: size * 0.32,
        fontWeight: 800,
        color: "#fff",
        flexShrink: 0,
      }}
    >
      {initials}
    </div>
  );
}