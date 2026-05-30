import type { ReactNode } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { I18nContext } from './i18n-context-value';
import { locales, messages, type Locale, type MessageKey } from './messages';

const storageKey = 'noshiro.locale';
const defaultLocale: Locale = 'zh-CN';

function readStoredLocale() {
  if (typeof window === 'undefined') {
    return defaultLocale;
  }

  const stored = window.localStorage.getItem(storageKey);
  return locales.includes(stored as Locale) ? (stored as Locale) : defaultLocale;
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>(readStoredLocale);

  useEffect(() => {
    document.documentElement.lang = locale;
    window.localStorage.setItem(storageKey, locale);
  }, [locale]);

  const value = useMemo(
    () => ({
      locale,
      setLocale,
      t: (key: MessageKey) => messages[locale][key],
    }),
    [locale],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}
