import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

export type ThemeName = 'light' | 'dark' | 'black' | 'grey';

const THEME_KEY = 'ag-theme';
const LARGE_MODE_KEY = 'ag-large-mode';

interface ThemeContextType {
  theme: ThemeName;
  setTheme: (t: ThemeName) => void;
  largeMode: boolean;
  setLargeMode: (lm: boolean) => void;
}

const Ctx = createContext<ThemeContextType | null>(null);

function initialTheme(): ThemeName {
  try {
    const saved = localStorage.getItem(THEME_KEY) as ThemeName | null;
    if (saved && ['light', 'dark', 'black', 'grey'].includes(saved)) return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  } catch {
    return 'dark';
  }
}

function initialLargeMode(): boolean {
  try {
    return localStorage.getItem(LARGE_MODE_KEY) === 'true';
  } catch {
    return false;
  }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<ThemeName>(initialTheme);
  const [largeMode, setLargeMode] = useState<boolean>(initialLargeMode);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch {}
  }, [theme]);

  useEffect(() => {
    if (largeMode) {
      document.documentElement.classList.add('text-[16px]');
    } else {
      document.documentElement.classList.remove('text-[16px]');
    }
    try {
      localStorage.setItem(LARGE_MODE_KEY, String(largeMode));
    } catch {}
  }, [largeMode]);

  return (
    <Ctx.Provider value={{ theme, setTheme, largeMode, setLargeMode }}>
      {children}
    </Ctx.Provider>
  );
}

export const useTheme = () => {
  const context = useContext(Ctx);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
};
