import type { ReactNode } from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ThemeContext, type ThemeMode, type ThemePreference } from './theme-context-value';

const accentStorageKey = 'noshiro.theme.accent';
const modeStorageKey = 'noshiro.theme.mode';
const defaultAccentColor = '#7F6FB0';
const defaultMode: ThemeMode = 'light';
const defaultPreference: ThemePreference = 'auto';
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

function getReadableTextColor(color: string) {
  const hex = normalizeHexColor(color).replace('#', '');
  const channels = [0, 2, 4].map((start) => {
    const value = parseInt(hex.slice(start, start + 2), 16) / 255;
    return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  });

  const luminance = channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
  return luminance > 0.46 ? '#17171c' : '#ffffff';
}

function detectSystemMode() {
  if (typeof window === 'undefined') {
    return defaultMode;
  }

  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function readStoredAccentColor() {
  if (typeof window === 'undefined') {
    return defaultAccentColor;
  }

  return window.localStorage.getItem(accentStorageKey) ?? defaultAccentColor;
}

function readStoredPreference(): ThemePreference {
  if (typeof window === 'undefined') {
    return defaultPreference;
  }

  const storedValue = window.localStorage.getItem(modeStorageKey);
  return storedValue === 'light' || storedValue === 'dark' || storedValue === 'auto' ? storedValue : defaultPreference;
}

function getEffectiveMode(preference: ThemePreference) {
  return preference === 'auto' ? detectSystemMode() : preference;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreference] = useState<ThemePreference>(readStoredPreference);
  const [mode, setEffectiveMode] = useState<ThemeMode>(() => getEffectiveMode(readStoredPreference()));
  const [accentColor, setAccentColor] = useState(readStoredAccentColor);

  const setMode = useCallback((nextPreference: ThemePreference) => {
    setPreference(nextPreference);
    setEffectiveMode(getEffectiveMode(nextPreference));
    window.localStorage.setItem(modeStorageKey, nextPreference);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.themeMode = mode;
  }, [mode]);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    function handleSystemModeChange(event: MediaQueryListEvent) {
      setEffectiveMode((currentMode) => {
        if (preference !== 'auto') {
          return currentMode;
        }
        return event.matches ? 'dark' : 'light';
      });
    }

    mediaQuery.addEventListener('change', handleSystemModeChange);
    return () => mediaQuery.removeEventListener('change', handleSystemModeChange);
  }, [preference]);

  useEffect(() => {
    const normalizedAccentColor = normalizeHexColor(accentColor);
    document.documentElement.style.setProperty('--color-accent', normalizedAccentColor);
    document.documentElement.style.setProperty('--color-accent-strong', darkenHexColor(normalizedAccentColor, 0.18));
    document.documentElement.style.setProperty('--color-accent-contrast', getReadableTextColor(normalizedAccentColor));
    window.localStorage.setItem(accentStorageKey, accentColor);
  }, [accentColor]);

  const toggleMode = useCallback(() => {
    setMode(mode === 'light' ? 'dark' : 'light');
  }, [mode, setMode]);

  const value = useMemo(
    () => ({
      accentColor,
      setAccentColor,
      mode,
      preference,
      setMode,
      toggleMode,
    }),
    [accentColor, mode, preference, setMode, toggleMode],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
