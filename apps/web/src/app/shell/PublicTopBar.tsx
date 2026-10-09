import { useEffect, useState } from 'react';
import { Link, useLocation } from '@tanstack/react-router';
import { ChevronDown, Menu } from 'lucide-react';
import { publicAssetPaths } from '@/shared/assets/public-assets';
import { useI18n } from '@/shared/i18n';
import { cn } from '@/shared/lib/cn';
import { routes } from '@/shared/routing/paths';
import { resolvedRouteHref } from '@/shared/routing/resolved-href';
import { Button } from '@/shared/ui/Button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/shared/ui/Dialog';
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger } from '@/shared/ui/DropdownMenu';

const barLinkClassName = cn(
  'relative inline-flex h-8 items-center gap-1 rounded-[var(--ui-radius-control)] px-2.5 text-[13px] font-medium',
  'text-[var(--ui-text-muted)] outline-none',
  'transition-colors duration-[var(--ui-transition-standard)] ease-[var(--ui-ease-gentle)] hover:text-[var(--ui-text)]',
  'focus-visible:ring-2 focus-visible:ring-[var(--ui-focus)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--ui-bg-canvas)]',
  'data-[status=active]:text-[var(--ui-text)]',
  // A short underline marks the current section, the way Linear's site does.
  'after:pointer-events-none after:absolute after:inset-x-2.5 after:-bottom-1 after:h-[2px] after:rounded-full',
  'after:bg-[var(--ui-accent)] after:opacity-0',
  'after:transition-opacity after:duration-[var(--ui-transition-standard)] after:ease-[var(--ui-ease-gentle)]',
  'data-[status=active]:after:opacity-100',
);

function useHeaderElevation() {
  const [isElevated, setIsElevated] = useState(false);

  useEffect(() => {
    function handleScroll() {
      setIsElevated(window.scrollY > 4);
    }

    handleScroll();
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);

  return isElevated;
}

function Wordmark() {
  return (
    <Link
      aria-label="Noshiro DB"
      className="flex min-w-0 items-center gap-2 rounded-[var(--ui-radius-control)]"
      to={routes.home}
    >
      <img alt="" aria-hidden="true" className="size-6 rounded-[6px]" src={publicAssetPaths.appIcon} />
      <span className="truncate text-[15px] font-semibold tracking-[-0.01em]">Noshiro DB</span>
    </Link>
  );
}

/**
 * The bar a visitor sees.
 *
 * Linear's composition: the wordmark holds the left edge, the sections sit
 * centred in the bar, and only the account actions live on the right. It
 * carries no search field — search belongs to the page, not to the chrome.
 */
export function PublicTopBar() {
  const { t } = useI18n();
  const location = useLocation();
  const isElevated = useHeaderElevation();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const navItems = [
    { exact: true, label: t('nav.home'), to: routes.home },
    { exact: false, label: t('nav.catalog'), to: routes.search },
  ];
  const airingItems = [
    { body: t('nav.airingCalendarBody'), label: t('nav.airingCalendar'), to: routes.calendar },
    { body: t('nav.broadcastBoardBody'), label: t('nav.broadcastBoard'), to: routes.airing },
  ];
  const menuItems = [
    ...navItems,
    { exact: false, label: t('nav.airingCalendar'), to: routes.calendar },
    { exact: false, label: t('nav.broadcastBoard'), to: routes.airing },
    { exact: false, label: t('nav.docs'), to: routes.docsIntroduction },
  ];
  const isAiringActive = [routes.calendar, routes.airing].some((path) => location.pathname.startsWith(path));

  return (
    <>
      <header
        className={cn(
          'sticky top-0 z-[var(--ui-layer-shell-header)] h-[var(--ui-shell-header-height)] border-b',
          'bg-[color-mix(in_srgb,var(--ui-bg-canvas)_85%,transparent)] backdrop-blur-xl',
          'transition-[border-color,box-shadow] duration-[var(--ui-transition-standard)] ease-[var(--ui-ease-gentle)]',
          isElevated
            ? 'border-[var(--ui-border)] shadow-[var(--ui-shadow-header)]'
            : 'border-[var(--ui-border-subtle)]',
        )}
      >
        <div className="mx-auto flex h-full max-w-[1160px] items-center gap-3 px-4 sm:px-5">
          <Wordmark />

          <nav className="absolute left-1/2 hidden -translate-x-1/2 items-center gap-1 lg:flex">
            {navItems.map((item) => (
              <Link
                activeOptions={{ exact: item.exact }}
                className={barLinkClassName}
                key={item.to}
                {...resolvedRouteHref(item.to)}
              >
                {item.label}
              </Link>
            ))}

            <DropdownMenu>
              <DropdownMenuTrigger
                render={
                  <button
                    className={cn('group', barLinkClassName, isAiringActive && 'text-[var(--ui-text)]')}
                    type="button"
                  >
                    {t('nav.airing')}
                    <ChevronDown className="size-3.5 transition-transform group-data-[popup-open]:rotate-180" />
                  </button>
                }
              />
              <DropdownMenuContent align="center" className="w-[460px] p-2">
                <div className="grid grid-cols-2 gap-1">
                  {airingItems.map((item) => (
                    <Link
                      className="grid gap-1 rounded-[8px] px-2.5 py-2 transition-colors hover:bg-[var(--ui-bg-subtle)]"
                      key={item.to}
                      to={item.to}
                    >
                      <span className="text-[13.5px] font-medium text-foreground">{item.label}</span>
                      <span className="text-[12.5px] leading-5 text-muted-foreground">{item.body}</span>
                    </Link>
                  ))}
                </div>
              </DropdownMenuContent>
            </DropdownMenu>

            <Link className={barLinkClassName} {...resolvedRouteHref(routes.docsIntroduction)}>
              {t('nav.docs')}
            </Link>
          </nav>

          <div className="ml-auto flex items-center gap-1.5">
            <Button asChild className="hidden sm:inline-flex" size="sm" variant="ghost">
              <Link to={routes.login}>{t('auth.login')}</Link>
            </Button>
            <Button asChild size="sm">
              <Link to={routes.register}>{t('auth.register')}</Link>
            </Button>
            <Button
              aria-label={t('public.openMenu')}
              className="lg:hidden"
              size="icon"
              tooltip={t('public.openMenu')}
              type="button"
              variant="ghost"
              onClick={() => {
                setIsMenuOpen(true);
              }}
            >
              <Menu className="size-4" />
            </Button>
          </div>
        </div>
      </header>

      <Dialog open={isMenuOpen} onOpenChange={setIsMenuOpen}>
        <DialogContent className="gap-0 p-0" closeLabel={t('public.closeMenu')} placement="left">
          <DialogHeader className="border-b border-[var(--ui-border-subtle)] px-4 py-3 pr-12">
            <DialogTitle className="flex items-center gap-2 text-sm">
              <img alt="" aria-hidden="true" className="size-6 rounded-[6px]" src={publicAssetPaths.appIcon} />
              Noshiro DB
            </DialogTitle>
          </DialogHeader>

          <div className="grid min-h-0 content-start gap-5 overflow-y-auto p-3">
            <nav className="grid gap-0.5" aria-label={t('public.menuBrowse')}>
              <h2 className="px-2 pb-1 text-[11px] font-medium text-[var(--ui-text-subtle)]">
                {t('public.menuBrowse')}
              </h2>
              {menuItems.map((item) => (
                <Link
                  activeOptions={{ exact: item.exact }}
                  className="inline-flex h-9 min-w-0 items-center rounded-[var(--ui-radius-control)] px-2 text-[13.5px] font-medium text-[var(--ui-text-muted)] transition-colors hover:bg-[var(--ui-bg-subtle)] hover:text-[var(--ui-text)] data-[status=active]:bg-[var(--ui-bg-muted)] data-[status=active]:text-[var(--ui-text)]"
                  key={item.to}
                  onClick={() => {
                    setIsMenuOpen(false);
                  }}
                  {...resolvedRouteHref(item.to)}
                >
                  <span className="min-w-0 truncate">{item.label}</span>
                </Link>
              ))}
            </nav>
          </div>

          <div className="grid gap-2 border-t border-[var(--ui-border-subtle)] p-3">
            <Button asChild>
              <Link
                to={routes.register}
                onClick={() => {
                  setIsMenuOpen(false);
                }}
              >
                {t('auth.register')}
              </Link>
            </Button>
            <Button asChild variant="secondary">
              <Link
                to={routes.login}
                onClick={() => {
                  setIsMenuOpen(false);
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
