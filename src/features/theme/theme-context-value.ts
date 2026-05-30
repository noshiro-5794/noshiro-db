import { createContext } from 'react';

export type ThemeMode = 'light' | 'dark';

export type ThemeState = {
  accentColor: string;
  setAccentColor: (color: string) => void;
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
  toggleMode: () => void;
};

export const ThemeContext = createContext<ThemeState | null>(null);
