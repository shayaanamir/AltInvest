import { createContext, useContext } from "react";

// The context object and its hook. The provider component is in ThemeProvider.jsx (a file that
// exports components must export nothing else, or fast refresh can't reload it).
export const ThemeContext = createContext(null);

export function useTheme() {
  return useContext(ThemeContext);
}
