import { useMemo } from 'react';
import { useTheme } from './ThemeProvider';

export function useThemeColors() {
  const { theme } = useTheme();

  return useMemo(() => {
    if (typeof window === 'undefined') {
      return {
        allow: '#4ADE80',
        block: '#F87171',
        ask: '#FB923C',
        muted: '#9BA39E',
        line: '#2F3432',
        text: '#E8ECE9',
        accent: '#E3B341',
        surface: '#1A1D1C',
        bg: '#121413',
      };
    }

    const s = getComputedStyle(document.documentElement);
    const c = (n: string) => {
      const val = s.getPropertyValue(n).trim();
      return val ? `rgb(${val.replace(/\s+/g, ', ')})` : '#888888';
    };

    return {
      allow: c('--allow'),
      block: c('--block'),
      ask: c('--ask'),
      muted: c('--muted'),
      line: c('--border'),
      text: c('--text'),
      accent: c('--accent'),
      surface: c('--surface'),
      bg: c('--bg'),
    };
  }, [theme]);
}
