import type { ReactNode } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { BookOpen, CalendarDays, FileText, Home, Layers3, Library, Search, UserRound } from 'lucide-react';
import { useAuth } from '@/features/auth/use-auth';
import { useI18n } from '@/features/i18n/use-i18n';
import { routes } from '@/routes/paths';
import { PublicFooter } from '@/shared/ui/PublicFooter';

type AppShellProps = {
  children: ReactNode;
};

type NavItem = {
  to: string;
  label: string;
  icon: ReactNode;
  end?: boolean;
};

export function AppShell({ children }: AppShellProps) {
  const { t } = useI18n();
  const { role, profile, status } = useAuth();
  const location = useLocation();

  const publicNavItems = [
    { to: routes.home, label: t('nav.home') },
    { to: routes.search, label: t('nav.search') },
    { to: routes.calendar, label: t('nav.calendar') },
    { to: routes.docsIntroduction, label: t('nav.docs') },
  ];
  const appNavGroups: Array<{ title: string; items: NavItem[] }> = [
    {
      title: t('nav.groupHome'),
      items: [
        { to: routes.home, label: t('nav.home'), icon: <Home className="size-4" />, end: true },
        { to: routes.me, label: t('nav.me'), icon: <UserRound className="size-4" /> },
      ],
    },
    {
      title: t('nav.groupDiscover'),
      items: [
        { to: routes.search, label: t('nav.search'), icon: <Search className="size-4" /> },
        { to: routes.calendar, label: t('nav.calendar'), icon: <CalendarDays className="size-4" /> },
      ],
    },
    {
      title: t('nav.groupMarked'),
      items: [
        { to: routes.library, label: t('nav.library'), icon: <Library className="size-4" /> },
        { to: routes.collections, label: t('nav.collections'), icon: <Layers3 className="size-4" /> },
        { to: routes.reviews, label: t('nav.reviews'), icon: <FileText className="size-4" /> },
      ],
    },
    {
      title: t('nav.groupOther'),
      items: [
        { to: routes.docsIntroduction, label: t('nav.docs'), icon: <BookOpen className="size-4" /> },
      ],
    },
  ];
  const isAuthPage = location.pathname === routes.login || location.pathname === routes.register;
  if (isAuthPage) {
    return children;
  }

  if (role === 'guest') {
    return (
      <div className="min-h-screen bg-white text-neutral-950 dark:bg-neutral-950 dark:text-neutral-50">
        <header className="sticky top-0 z-20 border-b border-neutral-200 bg-white/85 backdrop-blur-xl dark:border-neutral-800 dark:bg-neutral-950/85">
          <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-5">
            <NavLink className="flex min-w-0 items-center gap-2" to={routes.home} aria-label="Noshiro DB">
              <img
                className="size-8 rounded-lg ring-1 ring-neutral-200 dark:ring-neutral-800"
                src="/brand/icon.svg"
                alt=""
                aria-hidden="true"
              />
              <span className="truncate text-sm font-semibold">Noshiro DB</span>
            </NavLink>

            <nav className="absolute left-1/2 hidden -translate-x-1/2 items-center gap-1 rounded-full border border-neutral-200 bg-neutral-50 p-1 dark:border-neutral-800 dark:bg-neutral-900/80 md:flex">
              {publicNavItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    [
                      'rounded-full px-3 py-1.5 text-sm font-medium transition',
                      isActive
                        ? 'bg-white text-neutral-950 shadow-sm dark:bg-neutral-950 dark:text-white'
                        : 'text-neutral-500 hover:text-neutral-950 dark:text-neutral-400 dark:hover:text-white',
                    ].join(' ')
                  }
                  end={item.to === routes.home}
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>

            <div className="flex items-center gap-2">
              <NavLink
                className="hidden h-9 rounded-full px-3 py-2 text-sm font-medium leading-none text-neutral-600 transition hover:text-neutral-950 dark:text-neutral-400 dark:hover:text-white sm:inline-flex"
                to={routes.login}
              >
                {t('auth.login')}
              </NavLink>
              <NavLink
                className="h-9 rounded-full border border-neutral-950 bg-neutral-950 px-3 py-2 text-sm font-medium leading-none text-white transition hover:bg-neutral-800 dark:border-white dark:bg-white dark:text-neutral-950 dark:hover:bg-neutral-200"
                to={routes.register}
              >
                {t('auth.register')}
              </NavLink>
            </div>
          </div>
        </header>
        <main>{children}</main>
        <PublicFooter />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-100 text-neutral-950 dark:bg-neutral-950 dark:text-neutral-50 lg:grid lg:h-screen lg:grid-cols-[264px_minmax(0,1fr)] lg:overflow-hidden">
      <aside className="flex border-b border-neutral-200 bg-white/80 px-3 py-3 backdrop-blur-xl dark:border-neutral-800 dark:bg-neutral-950/80 lg:h-screen lg:flex-col lg:border-b-0 lg:border-r">
        <NavLink
          className="flex min-w-0 items-center gap-2 rounded-xl px-2 py-1.5 transition hover:bg-neutral-100 dark:hover:bg-neutral-900"
          to={routes.home}
          aria-label="Noshiro DB"
        >
          <img className="size-8 rounded-lg ring-1 ring-neutral-200 dark:ring-neutral-800" src="/brand/icon.svg" alt="" aria-hidden="true" />
          <span className="grid min-w-0">
            <span className="truncate text-sm font-semibold">Noshiro DB</span>
            <span className="truncate text-xs text-neutral-500 dark:text-neutral-400">{t('nav.workspace')}</span>
          </span>
        </NavLink>

        <nav className="ml-3 flex min-w-0 flex-1 gap-1 overflow-x-auto lg:ml-0 lg:mt-6 lg:flex-none lg:flex-col lg:gap-5 lg:overflow-visible">
          {appNavGroups.map((group) => (
            <section className="flex gap-1 lg:grid" key={group.title}>
              <h2 className="hidden px-3 text-[11px] font-semibold uppercase text-neutral-400 dark:text-neutral-500 lg:block">
                {group.title}
              </h2>
              <div className="flex gap-1 lg:grid">
                {group.items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      [
                        'inline-flex h-9 items-center gap-2 whitespace-nowrap rounded-xl px-3 text-sm font-medium transition lg:w-full',
                        isActive
                          ? 'bg-neutral-950 text-white shadow-sm dark:bg-white dark:text-neutral-950'
                          : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-950 dark:text-neutral-400 dark:hover:bg-neutral-900 dark:hover:text-white',
                      ].join(' ')
                    }
                    end={item.end}
                  >
                    {item.icon}
                    {item.label}
                  </NavLink>
                ))}
              </div>
            </section>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2 lg:ml-0 lg:mt-auto lg:grid">
          <span className="hidden min-h-10 items-center gap-3 rounded-xl border border-neutral-200 bg-neutral-50 px-3 text-sm text-neutral-500 dark:border-neutral-800 dark:bg-neutral-900/70 dark:text-neutral-400 lg:flex">
            <img className="size-6 rounded-lg object-cover" src={profile?.avatar || '/assets/placeholders/avatar.png'} alt="" />
            <span className="min-w-0 truncate">{status === 'checking' ? t('auth.checking') : profile?.nickname || t(`auth.${role}`)}</span>
          </span>
        </div>
      </aside>
      <main className="min-h-[calc(100vh-65px)] bg-neutral-100 p-3 dark:bg-neutral-950 lg:h-screen lg:min-h-0 lg:overflow-y-auto lg:p-4">
        <div className="min-h-full overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm dark:border-neutral-800 dark:bg-neutral-950">
          {children}
          <PublicFooter />
        </div>
      </main>
    </div>
  );
}
