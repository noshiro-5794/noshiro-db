import { placeholderImagePaths } from '@/shared/assets/public-assets';
import { lazy, Suspense, useState, type ReactNode } from 'react';
import { Link, useLocation, useNavigate } from '@tanstack/react-router';
import {
  Bell,
  Bookmark,
  BookOpen,
  CalendarDays,
  ChevronsUpDown,
  FileText,
  Home,
  Layers3,
  Library,
  LogOut,
  Menu,
  MessageSquare,
  Monitor,
  Moon,
  Search,
  Settings,
  ShieldCheck,
  Sun,
  UserRound,
} from 'lucide-react';
import { useAuth } from '@/entities/session';
import { useI18n } from '@/shared/i18n';
import { cn } from '@/shared/lib/cn';
import { routes } from '@/shared/routing/paths';
import { resolvedRouteHref } from '@/shared/routing/resolved-href';
import { useTheme } from '@/shared/theme/use-theme';
import { Button } from '@/shared/ui/Button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/shared/ui/Dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/shared/ui/DropdownMenu';
import { PageLoader } from '@/shared/ui/PageLoader';
import { toast } from '@/shared/ui/toast';
import { PublicFooter } from '@/widgets/public-footer';

type AppShellProps = {
  children: ReactNode;
};

type NavItem = {
  to: string;
  label: string;
  icon: ReactNode;
  end?: boolean;
};

type NavGroup = {
  title: string;
  items: NavItem[];
};

function isThemePreference(value: unknown): value is 'auto' | 'dark' | 'light' {
  return value === 'auto' || value === 'dark' || value === 'light';
}

const NotificationBell = lazy(() =>
  import('@/widgets/notifications').then((module) => ({ default: module.NotificationBell })),
);

function NotificationControl({ label }: { label: string }) {
  return (
    <Suspense
      fallback={
        <Button aria-label={label} size="icon" tooltip={label} type="button" variant="ghost">
          <Bell className="size-4" />
        </Button>
      }
    >
      <NotificationBell />
    </Suspense>
  );
}

function WorkspaceAccountMenu() {
  const { logout, profile, role } = useAuth();
  const { preference, setMode } = useTheme();
  const { t } = useI18n();
  const navigate = useNavigate();

  async function handleSignOut() {
    try {
      await logout();
    } catch {
      toast.error(t('common.requestFailed'));
    } finally {
      await navigate({ replace: true, to: routes.home });
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            aria-label={profile?.nickname || t(`auth.${role}`)}
            className="h-9 w-full min-w-0 justify-start gap-2 px-1.5 text-left"
            type="button"
            variant="ghost"
          />
        }
      >
        <img
          alt=""
          className="size-6 shrink-0 rounded-sm object-cover ring-1 ring-border"
          decoding="async"
          referrerPolicy="no-referrer"
          src={profile?.avatar || placeholderImagePaths.avatar}
        />
        <span className="min-w-0 flex-1 truncate text-[13px] font-medium text-foreground">
          {profile?.nickname || t(`auth.${role}`)}
        </span>
        <ChevronsUpDown className="size-3.5 shrink-0 text-subtle-foreground" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-[calc(var(--ui-sidebar-width)-24px)]" side="top" sideOffset={8}>
        <DropdownMenuGroup>
          <DropdownMenuLabel className="grid gap-0.5 py-2">
            <span className="truncate text-xs font-medium text-foreground">{profile?.nickname}</span>
            <span className="truncate font-normal">{profile?.email}</span>
          </DropdownMenuLabel>
          <DropdownMenuItem render={<Link to={routes.me} />}>
            <UserRound className="mr-2 size-4 text-subtle-foreground" />
            {t('profile.title')}
          </DropdownMenuItem>
          <DropdownMenuItem render={<Link to={routes.settings} />}>
            <Settings className="mr-2 size-4 text-subtle-foreground" />
            {t('settings.title')}
          </DropdownMenuItem>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuRadioGroup
          value={preference}
          onValueChange={(nextPreference) => {
            if (isThemePreference(nextPreference)) setMode(nextPreference);
          }}
        >
          <DropdownMenuLabel>{t('settings.appearance')}</DropdownMenuLabel>
          <DropdownMenuRadioItem closeOnClick value="auto">
            <span className="inline-flex items-center gap-2">
              <Monitor className="size-4 text-subtle-foreground" />
              {t('settings.auto')}
            </span>
          </DropdownMenuRadioItem>
          <DropdownMenuRadioItem closeOnClick value="light">
            <span className="inline-flex items-center gap-2">
              <Sun className="size-4 text-subtle-foreground" />
              {t('settings.light')}
            </span>
          </DropdownMenuRadioItem>
          <DropdownMenuRadioItem closeOnClick value="dark">
            <span className="inline-flex items-center gap-2">
              <Moon className="size-4 text-subtle-foreground" />
              {t('settings.dark')}
            </span>
          </DropdownMenuRadioItem>
        </DropdownMenuRadioGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem className="text-[var(--ui-danger-text)]" onClick={() => void handleSignOut()}>
          <LogOut className="mr-2 size-4" />
          {t('settings.signOut')}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function WorkspaceNavigation({
  className,
  groups,
  onNavigate,
}: {
  className?: string;
  groups: NavGroup[];
  onNavigate?: () => void;
}) {
  return (
    <nav className={cn('grid min-w-0 content-start gap-3', className)}>
      {groups.map((group) => (
        <section className="grid gap-1" key={group.title}>
          <h2 className="px-2 text-[11px] font-medium text-[var(--ui-text-subtle)]">{group.title}</h2>
          <div className="grid gap-0.5">
            {group.items.map((item) => (
              <Link
                activeOptions={{ exact: Boolean(item.end) }}
                className="inline-flex h-8 w-full items-center gap-2 whitespace-nowrap rounded-[var(--ui-radius-control)] px-2 text-[13px] font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground data-[status=active]:bg-[var(--ui-bg-muted)] data-[status=active]:text-foreground"
                key={item.to}
                onClick={onNavigate}
                {...resolvedRouteHref(item.to)}
              >
                {item.icon}
                <span className="min-w-0 truncate">{item.label}</span>
              </Link>
            ))}
          </div>
        </section>
      ))}
    </nav>
  );
}

export function AppShell({ children }: AppShellProps) {
  const { t } = useI18n();
  const { role, profile, status } = useAuth();
  const location = useLocation();
  const [mobileNavigationOpen, setMobileNavigationOpen] = useState(false);

  const publicNavItems = [
    { to: routes.home, label: t('nav.home') },
    { to: routes.search, label: t('nav.search') },
    { to: routes.calendar, label: t('nav.calendar') },
    { to: routes.docsIntroduction, label: t('nav.docs') },
  ];
  const appNavGroups: NavGroup[] = [
    {
      title: t('nav.groupOverview'),
      items: [
        { to: routes.home, label: t('nav.home'), icon: <Home className="size-4" />, end: true },
        { to: routes.search, label: t('nav.search'), icon: <Search className="size-4" /> },
      ],
    },
    {
      title: t('nav.groupCommunity'),
      items: [{ to: routes.communityPosts, label: t('nav.activity'), icon: <MessageSquare className="size-4" /> }],
    },
    {
      title: t('nav.groupDiscover'),
      items: [{ to: routes.calendar, label: t('nav.calendar'), icon: <CalendarDays className="size-4" /> }],
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
      title: t('nav.groupMore'),
      items: [
        ...(role === 'admin'
          ? [{ to: routes.admin, label: t('nav.admin'), icon: <ShieldCheck className="size-4" /> }]
          : []),
        { to: routes.docsIntroduction, label: t('nav.docs'), icon: <BookOpen className="size-4" /> },
      ],
    },
  ];

  const isAuthPage =
    location.pathname === routes.login ||
    location.pathname === routes.register ||
    location.pathname === routes.resetPassword;
  if (status === 'checking') {
    return <PageLoader />;
  }
  if (isAuthPage) {
    return children;
  }

  if (role === 'guest') {
    return (
      <div className="min-h-screen bg-[var(--ui-bg-canvas)]" data-app-shell="public">
        <header className="sticky top-0 z-[var(--ui-layer-shell-header)] h-[var(--ui-shell-header-height)] border-b border-border-subtle bg-[color-mix(in_srgb,var(--ui-bg-canvas)_88%,transparent)] backdrop-blur-xl">
          <div className="mx-auto flex h-full max-w-6xl items-center justify-between gap-4 px-4 sm:px-5">
            <Link className="flex min-w-0 items-center gap-2" to={routes.home} aria-label="Noshiro DB">
              <img
                className="size-7 rounded-[var(--ui-radius-control)]"
                src="/brand/icon.svg"
                alt=""
                aria-hidden="true"
              />
              <span className="truncate text-sm font-semibold">Noshiro DB</span>
            </Link>

            <nav className="absolute left-1/2 hidden -translate-x-1/2 items-center gap-0.5 rounded-sm border border-border bg-muted p-0.5 lg:flex">
              {publicNavItems.map((item) => (
                <Link
                  activeOptions={{ exact: item.to === routes.home }}
                  className="rounded-sm px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground data-[status=active]:bg-elevated data-[status=active]:text-foreground data-[status=active]:shadow-[var(--ui-shadow-control)]"
                  key={item.to}
                  {...resolvedRouteHref(item.to)}
                >
                  {item.label}
                </Link>
              ))}
            </nav>

            <div className="flex items-center gap-2">
              <DropdownMenu>
                <DropdownMenuTrigger
                  render={
                    <Button
                      aria-label={t('nav.openNavigation')}
                      className="lg:hidden"
                      size="icon"
                      tooltip={t('nav.openNavigation')}
                      variant="ghost"
                    />
                  }
                >
                  <Menu className="size-4" />
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="min-w-40 lg:hidden">
                  {publicNavItems.map((item) => (
                    <DropdownMenuItem key={item.to} render={<Link {...resolvedRouteHref(item.to)} />}>
                      {item.label}
                    </DropdownMenuItem>
                  ))}
                  <DropdownMenuSeparator />
                  <DropdownMenuItem render={<Link to={routes.login} />}>{t('auth.login')}</DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              <Button asChild className="hidden sm:inline-flex" size="sm" variant="ghost">
                <Link to={routes.login}>{t('auth.login')}</Link>
              </Button>
              <Button asChild size="sm">
                <Link to={routes.register}>{t('auth.register')}</Link>
              </Button>
            </div>
          </div>
        </header>
        <main>{children}</main>
        <PublicFooter />
      </div>
    );
  }

  return (
    <div
      className="min-h-screen bg-[var(--ui-bg-canvas)] lg:grid lg:h-screen lg:grid-cols-[var(--ui-sidebar-width)_minmax(0,1fr)] lg:overflow-hidden"
      data-app-shell="workspace"
    >
      <header className="sticky top-0 z-[var(--ui-layer-shell-header)] flex h-[var(--ui-shell-header-height)] items-center justify-between gap-3 border-b border-[var(--ui-border)] bg-[color-mix(in_srgb,var(--ui-bg-canvas)_92%,transparent)] px-3 backdrop-blur-xl lg:hidden">
        <Link className="flex min-w-0 items-center gap-2" to={routes.home} aria-label="Noshiro DB">
          <img className="size-6 rounded-[var(--ui-radius-control)]" src="/brand/icon.svg" alt="" aria-hidden="true" />
          <span className="truncate text-sm font-semibold">Noshiro DB</span>
        </Link>
        <div className="flex items-center gap-0.5">
          <NotificationControl label={t('nav.notifications')} />
          <Button
            aria-label={t('nav.openNavigation')}
            size="icon"
            tooltip={t('nav.openNavigation')}
            type="button"
            variant="ghost"
            onClick={() => {
              setMobileNavigationOpen(true);
            }}
          >
            <Menu className="size-4" />
          </Button>
        </div>
      </header>

      <Dialog open={mobileNavigationOpen} onOpenChange={setMobileNavigationOpen}>
        <DialogContent className="gap-0 p-0" closeLabel={t('nav.closeNavigation')} placement="left">
          <DialogHeader className="border-b border-[var(--ui-border)] px-4 py-3 pr-12">
            <DialogTitle className="flex items-center gap-2 text-sm">
              <img
                className="size-6 rounded-[var(--ui-radius-control)]"
                src="/brand/icon.svg"
                alt=""
                aria-hidden="true"
              />
              Noshiro DB
            </DialogTitle>
          </DialogHeader>
          <WorkspaceNavigation
            className="overflow-y-auto p-3"
            groups={appNavGroups}
            onNavigate={() => {
              setMobileNavigationOpen(false);
            }}
          />
          <div className="grid gap-0.5 border-t border-[var(--ui-border)] p-3">
            <Link
              className="flex h-8 min-w-0 items-center gap-2 rounded-[var(--ui-radius-control)] px-2 text-[13px] text-[var(--ui-text-muted)] outline-none transition-colors hover:bg-[var(--ui-bg-subtle)] hover:text-[var(--ui-text)] focus-visible:ring-2 focus-visible:ring-[var(--ui-focus)]"
              to={routes.me}
              onClick={() => {
                setMobileNavigationOpen(false);
              }}
            >
              <img
                className="size-5 rounded-sm object-cover"
                decoding="async"
                referrerPolicy="no-referrer"
                src={profile?.avatar || placeholderImagePaths.avatar}
                alt=""
              />
              <span className="min-w-0 truncate">{profile?.nickname || t(`auth.${role}`)}</span>
            </Link>
            <Link
              className="flex h-8 min-w-0 items-center gap-2 rounded-[var(--ui-radius-control)] px-2 text-[13px] text-[var(--ui-text-muted)] outline-none transition-colors hover:bg-[var(--ui-bg-subtle)] hover:text-[var(--ui-text)] focus-visible:ring-2 focus-visible:ring-[var(--ui-focus)]"
              to={routes.settings}
              onClick={() => {
                setMobileNavigationOpen(false);
              }}
            >
              <Settings className="size-4" />
              <span className="min-w-0 truncate">{t('settings.title')}</span>
            </Link>
          </div>
        </DialogContent>
      </Dialog>

      <aside className="hidden min-h-0 bg-[var(--ui-bg-sidebar)] px-3 py-3 lg:flex lg:h-screen lg:flex-col">
        <Link
          className="flex min-w-0 shrink-0 items-center gap-2 rounded-[var(--ui-radius-control)] px-2 py-1 transition-colors hover:bg-[var(--ui-bg-subtle)]"
          to={routes.home}
          aria-label="Noshiro DB"
        >
          <img className="size-6 rounded-[var(--ui-radius-control)]" src="/brand/icon.svg" alt="" aria-hidden="true" />
          <span className="grid min-w-0">
            <span className="truncate text-sm font-semibold">Noshiro DB</span>
          </span>
        </Link>

        <WorkspaceNavigation className="mt-4 min-h-0 flex-1 overflow-y-auto pr-1" groups={appNavGroups} />

        <div className="mt-3 grid shrink-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-1 border-t border-border-subtle pt-2">
          <WorkspaceAccountMenu />
          <NotificationControl label={t('nav.notifications')} />
        </div>
      </aside>
      <main className="min-h-[calc(100svh-var(--ui-shell-header-height))] p-[var(--ui-shell-gap)] lg:h-screen lg:min-h-0 lg:overflow-hidden lg:pl-0">
        <div className="flex min-h-full flex-col overflow-hidden rounded-lg border border-border bg-surface lg:h-full">
          <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
        </div>
      </main>
    </div>
  );
}
