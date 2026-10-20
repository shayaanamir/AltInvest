import { useTheme } from "../../context/ThemeContext";

// Landing/marketing design tokens — reconciled onto the app's --sv2-* orange
// palette (see stylesheet audit). Values resolve through CSS custom
// properties so light/dark theming is automatic; the *_HEX exports exist
// only for contexts (WebGL shader uniforms, Canvas 2D fillStyle) that
// require a literal hex string rather than a CSS var().
export const L = {
  // Backgrounds
  bg0:    "var(--sv2-bg)",
  bg1:    "var(--sv2-card)",
  // Borders
  border:  "var(--sv2-border)",
  border2: "var(--sv2-border-strong)",
  // Text
  ink:    "var(--sv2-text)",
  ink2:   "var(--sv2-text-soft)",
  ink3:   "var(--sv2-text-mute)",
  // Brand / semantic colors
  accent: "var(--sv2-accent)",
  green:  "var(--sv2-green)",
  red:    "var(--sv2-red)",
  // Typography
  font:   "'DM Sans', 'Segoe UI', sans-serif",
};


// Literal hex mirrors of --sv2-accent, for the two spots that can't consume
// a CSS var: the SoftAurora WebGL shader and AuthRightPanel's canvas draw.
export const ACCENT_HEX = { dark: "#e2825a", light: "#bf5d38" };
export const GREEN_HEX  = { dark: "#3fcf8e", light: "#2f8f5b" };

// Kept for backward compatibility with existing `useLandingTheme()` call
// sites. No longer branches on light/dark internally — --sv2-* vars already
// cascade off html[data-theme] — but still returns isDark for the few
// consumers that need the literal boolean (e.g. hex selection above).
export function useLandingTheme() {
  const { isDark } = useTheme();
  return { ...L, isDark };
}