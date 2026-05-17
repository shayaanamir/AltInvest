import { createContext, useContext, useState } from "react";
import { dark, light } from "../theme/tokens";

const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  const [isDark, setIsDark] = useState(true);
  const tokens = isDark ? dark : light;
  const toggle = () => setIsDark((d) => !d);

  return (
    <ThemeContext.Provider value={{ tokens, isDark, toggle }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
