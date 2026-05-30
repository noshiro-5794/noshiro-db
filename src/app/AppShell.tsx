import type { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '@/features/auth/use-auth';
import { localeLabels, locales, type Locale } from '@/features/i18n/messages';
import { useI18n } from '@/features/i18n/use-i18n';
import { useTheme } from '@/features/theme/use-theme';
import { routes } from '@/routes/paths';

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  const { t, locale, setLocale } = useI18n();
  const { mode, toggleMode } = useTheme();
  const { role, profile, status } = useAuth();

  const navItems = [
    { to: routes.home, label: t('nav.home') },
    { to: routes.search, label: t('nav.search') },
    { to: routes.calendar, label: t('nav.calendar') },
    { to: routes.me, label: t('nav.me') },
  ];

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">Noshiro DB</span>
          <span className="brand-subtitle">Anime and galgame catalog</span>
        </div>
        <nav className="nav">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `nav-link${isActive ? ' is-active' : ''}`}
              end={item.to === routes.home}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="topbar-actions">
          <select
            aria-label="Language"
            className="select-control"
            value={locale}
            onChange={(event) => setLocale(event.target.value as Locale)}
          >
            {locales.map((item) => (
              <option key={item} value={item}>
                {localeLabels[item]}
              </option>
            ))}
          </select>
          <button className="button button-ghost" type="button" onClick={toggleMode}>
            {mode === 'light' ? t('theme.dark') : t('theme.light')}
          </button>
          <span className="auth-chip">
            {status === 'checking' ? t('auth.checking') : profile?.nickname || t(`auth.${role}`)}
          </span>
        </div>
      </header>
      <main className="content">{children}</main>
    </div>
  );
}
