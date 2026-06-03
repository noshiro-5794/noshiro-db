import { lazy, Suspense, type ReactNode } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { Bell, Bookmark, BookOpen, CalendarDays, FileText, Home, Layers3, Library, MessageSquare, Search, Settings, ShieldCheck } from 'lucide-react';
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

const NotificationBell = lazy(() => import('@/features/community/components/NotificationBell').then((module) => ({ default: module.NotificationBell })));

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
      title: t('nav.groupWorkspace'),
      items: [
        { to: routes.home, label: t('nav.home'), icon: <Home className="size-4" />, end: true },
        { to: routes.communityPosts, label: t('nav.posts'), icon: <MessageSquare className="size-4" /> },
      ],
    },
    {
      title: t('nav.groupExplore'),
      items: [
        { to: routes.search, label: t('nav.search'), icon: <Search className="size-4" /> },
        { to: routes.calendar, label: t('nav.calendar'), icon: <CalendarDays className="size-4" /> },
      ],
    },
    {
      title: t('nav.groupLibrary'),
      items: [
        { to: routes.library, label: t('nav.library'), icon: <Library className="size-4" /> },
        { to: routes.collections, label: t('nav.collections'), icon: <Layers3 className="size-4" /> },
        { to: routes.reviews, label: t('nav.reviews'), icon: <FileText className="size-4" /> },
        { to: routes.bookmarks, label: t('nav.bookmarks'), icon: <Bookmark className="size-4" /> },
      ],
    },
    {
      title: t('nav.groupResources'),
      items: [
        ...(role === 'admin' ? [{ to: routes.admin, label: t('nav.admin'), icon: <ShieldCheck className="size-4" /> }] : []),
        { to: routes.docsIntroduction, label: t('nav.docs'), icon: <BookOpen className="size-4" /> },
      ],
    },
  ];

  const isAuthPage = location.pathname === routes.login || location.pathname === routes.register || location.pathname === routes.resetPassword;
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
                className="size-8 rounded-lg"
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
    <div className="workspace-shell">
      <aside className="workspace-sidebar">
        <NavLink
          className="flex min-w-0 shrink-0 items-center gap-2 rounded-xl px-2 py-1.5 transition hover:bg-neutral-100 dark:hover:bg-neutral-900"
          to={routes.home}
          aria-label="Noshiro DB"
        >
          <img className="size-8 rounded-lg" src="/brand/icon.svg" alt="" aria-hidden="true" />
          <span className="grid min-w-0">
            <span className="truncate text-sm font-semibold">Noshiro DB</span>
          </span>
        </NavLink>

        <nav className="workspace-nav">
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
                    <span className="inline-flex min-w-0 items-center gap-2">
                      {item.icon}
                      <span className="truncate">{item.label}</span>
                    </span>
                  </NavLink>
                ))}
              </div>
            </section>
          ))}
        </nav>

        <div className="ml-auto flex shrink-0 items-center gap-2 lg:ml-0 lg:mt-4 lg:grid lg:grid-cols-[minmax(0,1fr)_auto_auto]">
          <NavLink className="hidden min-h-10 items-center gap-3 rounded-xl border border-neutral-200 bg-neutral-50 px-3 text-sm text-neutral-500 transition hover:border-[var(--color-accent-border)] hover:text-neutral-950 dark:border-neutral-800 dark:bg-neutral-900/70 dark:text-neutral-400 dark:hover:text-white lg:flex" to={routes.me}>
            <img className="size-6 rounded-lg object-cover" src={profile?.avatar || '/assets/placeholders/avatar.png'} alt="" />
            <span className="min-w-0 truncate">{status === 'checking' ? t('auth.checking') : profile?.nickname || t(`auth.${role}`)}</span>
          </NavLink>
          <Suspense
            fallback={(
              <button
                aria-label={t('nav.notifications')}
                className="grid size-10 place-items-center rounded-xl border border-neutral-200 bg-neutral-50 text-neutral-500 dark:border-neutral-800 dark:bg-neutral-900/70 dark:text-neutral-400"
                type="button"
              >
                <Bell className="size-4" />
              </button>
            )}
          >
            <NotificationBell />
          </Suspense>
          <NavLink
            aria-label={t('settings.title')}
            className="grid size-10 place-items-center rounded-xl border border-neutral-200 bg-neutral-50 text-neutral-500 transition hover:border-[var(--color-accent-border)] hover:text-neutral-950 dark:border-neutral-800 dark:bg-neutral-900/70 dark:text-neutral-400 dark:hover:text-white"
            to={routes.settings}
          >
            <Settings className="size-4" />
          </NavLink>
        </div>
      </aside>
      <main className="workspace-main">
        <div className="workspace-frame">
          <div className="workspace-frame-content">
            {children}
          </div>
        </div>
      </main>
    </div>
  );
}
