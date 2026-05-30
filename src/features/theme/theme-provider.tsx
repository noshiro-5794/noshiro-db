import type { ReactNode } from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ThemeContext, type ThemeMode } from './theme-context-value';

const accentStorageKey = 'noshiro.theme.accent';
const modeStorageKey = 'noshiro.theme.mode';
const defaultAccentColor = '#7F6FB0';
const defaultMode: ThemeMode = 'light';
const hexColorPattern = /^#?[0-9a-f]{6}$/iu;

function normalizeHexColor(color: string) {
  return hexColorPattern.test(color) ? `#${color.replace('#', '')}` : defaultAccentColor;
}

function darkenHexColor(color: string, amount: number) {
  const hex = normalizeHexColor(color).replace('#', '');
  const channels = [0, 2, 4].map((start) => {
    const value = parseInt(hex.slice(start, start + 2), 16);
    return Math.round(value * (1 - amount))
      .toString(16)
      .padStart(2, '0');
  });

  return `#${channels.join('')}`;
}

function readStoredMode() {
  if (typeof window === 'undefined') {
    return defaultMode;
  }

  const stored = window.localStorage.getItem(modeStorageKey);
  return stored === 'dark' || stored === 'light' ? stored : defaultMode;
}

function readStoredAccentColor() {
  if (typeof window === 'undefined') {
    return defaultAccentColor;
  }

  return window.localStorage.getItem(accentStorageKey) ?? defaultAccentColor;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>(readStoredMode);
  const [accentColor, setAccentColor] = useState(readStoredAccentColor);

  useEffect(() => {
    document.documentElement.dataset.themeMode = mode;
    window.localStorage.setItem(modeStorageKey, mode);
  }, [mode]);

  useEffect(() => {
    const normalizedAccentColor = normalizeHexColor(accentColor);
    document.documentElement.style.setProperty('--color-accent', normalizedAccentColor);
    document.documentElement.style.setProperty('--color-accent-strong', darkenHexColor(normalizedAccentColor, 0.14));
    window.localStorage.setItem(accentStorageKey, accentColor);
  }, [accentColor]);

  const toggleMode = useCallback(() => {
    setMode((currentMode) => (currentMode === 'light' ? 'dark' : 'light'));
  }, []);

  const value = useMemo(
    () => ({
      accentColor,
      setAccentColor,
      mode,
      setMode,
      toggleMode,
    }),
    [accentColor, mode, toggleMode],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
