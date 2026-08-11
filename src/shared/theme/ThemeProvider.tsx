import type { ReactNode } from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ThemeContext, type ThemeMode, type ThemePreference } from './theme-context-value';

const modeStorageKey = 'noshiro.theme.mode';
const defaultMode: ThemeMode = 'light';
const defaultPreference: ThemePreference = 'auto';

function detectSystemMode() {
  if (typeof window === 'undefined') {
    return defaultMode;
  }

  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function readStoredPreference(): ThemePreference {
  if (typeof window === 'undefined') {
    return defaultPreference;
  }

  try {
    const storedValue = window.localStorage.getItem(modeStorageKey);
    return storedValue === 'light' || storedValue === 'dark' || storedValue === 'auto'
      ? storedValue
      : defaultPreference;
  } catch {
    return defaultPreference;
  }
}

function storePreference(preference: ThemePreference) {
  try {
    window.localStorage.setItem(modeStorageKey, preference);
  } catch {
    // Theme changes still apply for this session when storage is unavailable.
  }
}

function getEffectiveMode(preference: ThemePreference) {
  return preference === 'auto' ? detectSystemMode() : preference;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreference] = useState<ThemePreference>(readStoredPreference);
  const [mode, setEffectiveMode] = useState<ThemeMode>(() => getEffectiveMode(readStoredPreference()));

  const setMode = useCallback((nextPreference: ThemePreference) => {
    setPreference(nextPreference);
    setEffectiveMode(getEffectiveMode(nextPreference));
    storePreference(nextPreference);
  }, []);

  useEffect(() => {
    document.documentElement.dataset['themeMode'] = mode;
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
    return () => {
      mediaQuery.removeEventListener('change', handleSystemModeChange);
    };
  }, [preference]);

  useEffect(() => {
    function handleStorage(event: StorageEvent) {
      if (event.key !== modeStorageKey) {
        return;
      }

      const nextPreference =
        event.newValue === 'light' || event.newValue === 'dark' || event.newValue === 'auto'
          ? event.newValue
          : defaultPreference;
      setPreference(nextPreference);
      setEffectiveMode(getEffectiveMode(nextPreference));
    }

    window.addEventListener('storage', handleStorage);
    return () => {
      window.removeEventListener('storage', handleStorage);
    };
  }, []);

  const toggleMode = useCallback(() => {
    setMode(mode === 'light' ? 'dark' : 'light');
  }, [mode, setMode]);

  const value = useMemo(
    () => ({
      mode,
      preference,
      setMode,
      toggleMode,
    }),
    [mode, preference, setMode, toggleMode],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
