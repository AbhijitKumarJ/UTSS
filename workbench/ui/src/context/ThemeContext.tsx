import React, { createContext, useContext, useState, useEffect } from "react";
import { ThemeName } from "../types";

interface ThemeContextType {
  theme: ThemeName;
  setTheme: (theme: ThemeName) => void;
  monacoTheme: string;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<ThemeName>(() => {
    try {
      const saved = localStorage.getItem("utss_workbench_theme");
      if (saved === "utss-dark" || saved === "vscode-dark" || saved === "vscode-light" || saved === "monokai") {
        return saved;
      }
    } catch (e) {}
    return "utss-dark";
  });

  const setTheme = (newTheme: ThemeName) => {
    setThemeState(newTheme);
    try {
      localStorage.setItem("utss_workbench_theme", newTheme);
    } catch (e) {}
    document.documentElement.setAttribute("data-theme", newTheme);
  };

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  // Map workbench theme to Monaco Editor themes
  const monacoThemeMap: Record<ThemeName, string> = {
    "utss-dark": "utss-dark",
    "vscode-dark": "vs-dark",
    "vscode-light": "vs",
    "monokai": "monokai"
  };
  const monacoTheme = monacoThemeMap[theme] || "vs-dark";

  return (
    <ThemeContext.Provider value={{ theme, setTheme, monacoTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
};
