import { useState, type ReactNode } from 'react';
import { Link } from '@tanstack/react-router';
import { CalendarDays, Clapperboard, LayoutGrid, Menu, Search, Sparkles } from 'lucide-react';
import { publicAssetPaths } from '@/shared/assets/public-assets';
import { useI18n } from '@/shared/i18n';
import { cn } from '@/shared/lib/cn';
import { routes } from '@/shared/routing/paths';
import { resolvedRouteHref } from '@/shared/routing/resolved-href';
import { Button } from '@/shared/ui/Button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/shared/ui/Dialog';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/shared/ui/DropdownMenu';

type MenuEntry = { icon: ReactNode; label: string; to: string };
type MenuSection = { entries: MenuEntry[]; key: string; label: string };

/**
 * plane's marketing nav: plain links on the bar itself, at the bar's own text
 * size, with no pill to separate them from the page they sit on.
 */
const navItemClassName = cn(
  'inline-flex shrink-0 cursor-pointer items-center gap-1 whitespace-nowrap text-[15px] font-normal',
  'text-[var(--ui-text)] outline-none transition-colors duration-150 ease-out',
  'hover:text-[var(--ui-text-muted)] focus-visible:ring-2 focus-visible:ring-[var(--ui-focus-halo)]',
  'data-[popup-open]:text-[var(--ui-text-muted)]',
  'data-[status=active]:text-[var(--ui-text)]',
);

/**
 * The bar a visitor sees, built on plane's.
 *
 * plane's marketing header is one row on `surface-1`: the lockup holds the left
 * edge, the sections sit centred at the bar's own text size, and the account
 * links close the right edge beside the one filled action. Sections with more
 * than one destination open an anchored menu under their link rather than a
 * panel spanning the bar.
 */
export function PublicTopBar() {
  const { t } = useI18n();
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const menus: MenuSection[] = [
    {
      entries: [
        { icon: <Search className="size-4" />, label: t('nav.catalog'), to: routes.search },
        {
          icon: <Clapperboard className="size-4" />,
          label: t('search.anime'),
          to: `${routes.search}?subject_type=anime`,
        },
        {
          icon: <Sparkles className="size-4" />,
          label: t('search.galgame'),
          to: `${routes.search}?subject_type=galgame`,
        },
      ],
      key: 'catalogue',
      label: t('nav.catalog'),
    },
    {
      entries: [
        { icon: <CalendarDays className="size-4" />, label: t('nav.airingCalendar'), to: routes.calendar },
        { icon: <LayoutGrid className="size-4" />, label: t('nav.broadcastBoard'), to: routes.airing },
      ],
      key: 'airing',
      label: t('nav.airing'),
    },
  ];

  const drawerLinks = [
    { label: t('nav.home'), to: routes.home },
    ...menus.flatMap((menu) => menu.entries.map((entry) => ({ label: entry.label, to: entry.to }))),
    { label: t('nav.docs'), to: routes.docsIntroduction },
  ];

  return (
    <>
      <header className="sticky top-0 z-[var(--ui-layer-shell-header)] h-[var(--ui-public-header-height)] border-b border-[var(--ui-border-subtle)] bg-[var(--ui-bg-public)] text-[var(--ui-text)]">
        <div className="mx-auto flex h-full w-full max-w-[1280px] items-center justify-between gap-6 px-6 lg:grid lg:grid-cols-[1fr_auto_1fr] lg:px-10">
          <div className="flex min-w-0 shrink-0 items-center">
            <Link
              aria-label="Noshiro DB"
              className="flex min-w-0 shrink-0 items-center gap-2.5 outline-none"
              to={routes.home}
            >
              <img
                alt=""
                aria-hidden="true"
                className="size-7 shrink-0 rounded-[var(--ui-radius-control)] object-cover"
                src={publicAssetPaths.appIcon}
              />
              <span className="wordmark truncate text-[23px] text-[var(--ui-text)]">Noshiro DB</span>
            </Link>
          </div>

          <nav className="hidden min-w-0 items-center justify-center gap-8 lg:flex xl:gap-9">
            <Link {...resolvedRouteHref(routes.home)} activeOptions={{ exact: true }} className={navItemClassName}>
              {t('nav.home')}
            </Link>

            {menus.map((menu) => (
              <DropdownMenu key={menu.key}>
                <DropdownMenuTrigger
                  render={
                    <button aria-label={menu.label} className={cn(navItemClassName, 'group/nav-item')} type="button" />
                  }
                >
                  {menu.label}
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" sideOffset={10}>
                  {menu.entries.map((entry) => (
                    <DropdownMenuItem key={entry.to} render={<Link {...resolvedRouteHref(entry.to)} />}>
                      <span className="shrink-0 text-[var(--ui-text-subtle)]">{entry.icon}</span>
                      <span className="min-w-0 truncate">{entry.label}</span>
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            ))}

            <Link {...resolvedRouteHref(routes.docsIntroduction)} className={navItemClassName}>
              {t('nav.docs')}
            </Link>
          </nav>

          <div className="flex shrink-0 items-center justify-end gap-5">
            <Link className={cn(navItemClassName, 'hidden sm:inline-flex')} to={routes.login}>
              {t('auth.login')}
            </Link>
            <Button asChild className="public-button public-button-primary hidden sm:inline-flex" variant="unstyled">
              <Link to={routes.register}>{t('auth.register')}</Link>
            </Button>
            <Button
              aria-label={t('public.openMenu')}
              className="text-[var(--ui-text)] lg:hidden"
              size="icon-sm"
              tooltip={t('public.openMenu')}
              type="button"
              variant="ghost"
              onClick={() => {
                setIsDrawerOpen(true);
              }}
            >
              <Menu className="size-4" />
            </Button>
          </div>
        </div>
      </header>

      <Dialog open={isDrawerOpen} onOpenChange={setIsDrawerOpen}>
        <DialogContent className="gap-0 p-0" closeLabel={t('public.closeMenu')} placement="left">
          <DialogHeader className="border-b border-[var(--ui-border-subtle)] px-4 py-3 pr-12">
            <DialogTitle className="flex items-center gap-2 text-sm">
              <img
                alt=""
                aria-hidden="true"
                className="size-7 rounded-[var(--ui-radius-control)]"
                src={publicAssetPaths.appIcon}
              />
              <span className="wordmark text-[15px]">Noshiro DB</span>
            </DialogTitle>
          </DialogHeader>

          <div className="grid min-h-0 content-start gap-0.5 overflow-y-auto p-2">
            {drawerLinks.map((item) => (
              <Link
                className={cn(navItemClassName, 'h-8 w-full justify-start')}
                key={item.to}
                onClick={() => {
                  setIsDrawerOpen(false);
                }}
                {...resolvedRouteHref(item.to)}
              >
                <span className="min-w-0 truncate">{item.label}</span>
              </Link>
            ))}
          </div>

          <div className="grid gap-2 border-t border-[var(--ui-border-subtle)] p-3">
            <Button asChild size="sm">
              <Link
                to={routes.register}
                onClick={() => {
                  setIsDrawerOpen(false);
                }}
              >
                {t('auth.register')}
              </Link>
            </Button>
            <Button asChild size="sm" variant="secondary">
              <Link
                to={routes.login}
                onClick={() => {
                  setIsDrawerOpen(false);
                }}
              >
                {t('auth.login')}
              </Link>
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
