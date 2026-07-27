import type { ReactNode } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { I18nContext } from './i18n-context-value';
import { messages, type Locale, type MessageKey } from './catalog';

const defaultLocale: Locale = 'en-US';

function detectSystemLocale() {
  if (typeof window === 'undefined') {
    return defaultLocale;
  }

  const languages = navigator.languages.length > 0 ? navigator.languages : [navigator.language];
  const matchedLocale = languages.find((language) => {
    const normalizedLanguage = language.toLowerCase();
    return (
      normalizedLanguage.startsWith('zh') || normalizedLanguage.startsWith('ja') || normalizedLanguage.startsWith('en')
    );
  });

  if (!matchedLocale) {
    return defaultLocale;
  }

  const normalizedLocale = matchedLocale.toLowerCase();
  if (normalizedLocale.startsWith('zh')) {
    return 'zh-CN';
  }
  if (normalizedLocale.startsWith('ja')) {
    return 'ja-JP';
  }
  return 'en-US';
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>(detectSystemLocale);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  useEffect(() => {
    function handleLanguageChange() {
      setLocale(detectSystemLocale());
    }

    window.addEventListener('languagechange', handleLanguageChange);
    return () => window.removeEventListener('languagechange', handleLanguageChange);
  }, []);

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
