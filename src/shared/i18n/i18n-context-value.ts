import { createContext } from 'react';
import type { Locale, MessageKey } from './catalog';

export type I18nState = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: MessageKey) => string;
};

export const I18nContext = createContext<I18nState | null>(null);
