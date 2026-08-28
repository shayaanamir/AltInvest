import { useTheme } from "../../context/ThemeContext";

// Landing page design tokens — dark-only, matches screenshots exactly
export const L = {
  bg0:          "#08090f",
  bg1:          "#0d0e1a",
  bg2:          "#12131f",
  bg3:          "#191a2e",
  bg4:          "#1e2038",
  border:       "rgba(255,255,255,0.07)",
  border2:      "rgba(255,255,255,0.12)",
  ink:          "#e8eaf4",
  ink2:         "#8b8faa",
  ink3:         "#44475a",
  blue:         "#5b6ef5",
  blueDim:      "#3b4bb8",
  purple:       "#9b6dff",
  purpleLight:  "#c4a0ff",
  green:        "#00d48b",
  red:          "#ff4060",
  amber:        "#f5b731",
  teal:         "#00c9b0",
  font:         "'DM Sans', 'Segoe UI', sans-serif",
};

// Light-mode equivalent for the hero/nav only. Aligned to the sv2 light
// palette (see styles/sentiment.css) so the very top of the page reads
// as one continuous system with everything below it.
export const LIGHT_L = {
  bg0:          "#faf7f1",
  bg1:          "#f7f3ea",
  bg2:          "#ffffff",
  bg3:          "#f7f3ea",
  bg4:          "#f1ede3",
  border:       "rgba(36,33,28,0.08)",
  border2:      "rgba(36,33,28,0.14)",
  ink:          "#24211c",
  ink2:         "#6c6555",
  ink3:         "#a49b87",
  blue:         "#5b6ef5",
  blueDim:      "#3b4bb8",
  purple:       "#8b5cf6",
  purpleLight:  "#6d28d9",
  green:        "#2f8f5b",
  red:          "#c0392b",
  amber:        "#bf5d38",
  teal:         "#2f8f8a",
  font:         "'DM Sans', 'Segoe UI', sans-serif",
};

// Only the hero + nav use this — everything below them uses the .sv2
// (--sv2-*) variables directly instead.
export function useLandingTheme() {
  const { isDark } = useTheme();
  return isDark ? L : LIGHT_L;
}