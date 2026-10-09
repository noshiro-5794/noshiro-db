import { createContext } from 'react';

export type ThemeMode = 'light' | 'dark';
export type ThemePreference = 'auto' | ThemeMode;

export type ThemeState = {
  mode: ThemeMode;
  preference: ThemePreference;
  setMode: (mode: ThemePreference) => void;
  toggleMode: () => void;
};

export const ThemeContext = createContext<ThemeState | null>(null);
