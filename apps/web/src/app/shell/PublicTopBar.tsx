import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Link, useLocation } from '@tanstack/react-router';
import { CalendarDays, ChevronDown, Clapperboard, LayoutGrid, Menu, Search, Sparkles } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { publicAssetPaths } from '@/shared/assets/public-assets';
import { useI18n } from '@/shared/i18n';
import { cn } from '@/shared/lib/cn';
import { easeStandard } from '@/shared/lib/motion';
import { routes } from '@/shared/routing/paths';
import { resolvedRouteHref } from '@/shared/routing/resolved-href';
import { Button } from '@/shared/ui/Button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/shared/ui/Dialog';

type MenuEntry = { body?: string; icon: ReactNode; label: string; to: string };
type MenuSection = { entries: MenuEntry[]; key: string; label: string };

/** How long the pointer may leave the bar before the panel closes. */
const closeGraceMs = 140;

const triggerClassName = cn(
  'group inline-flex h-9 items-center gap-1 rounded-[var(--ui-radius-control)] px-3 text-[14px] font-medium',
  'text-[var(--ui-text-muted)] outline-none',
  'transition-colors duration-[var(--ui-transition-standard)] ease-[var(--ui-ease-gentle)] hover:text-[var(--ui-text)]',
  'focus-visible:ring-2 focus-visible:ring-[var(--ui-focus)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--ui-bg-canvas)]',
  // dub marks the trigger whose panel is open with a soft surface, not a colour.
  'data-[open]:bg-[var(--ui-bg-subtle)] data-[open]:text-[var(--ui-text)]',
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
      className="flex min-w-0 items-center gap-2 rounded-[var(--ui-radius-control)] outline-none focus-visible:ring-2 focus-visible:ring-[var(--ui-focus)]"
      to={routes.home}
    >
      <img alt="" aria-hidden="true" className="size-6 rounded-[6px]" src={publicAssetPaths.appIcon} />
      <span className="truncate text-[15px] font-semibold tracking-[-0.01em]">Noshiro DB</span>
    </Link>
  );
}

/**
 * The bar a visitor sees, built on dub's.
 *
 * The wordmark holds the left edge, the sections sit centred, and the account
 * actions close the right. Sections with more than one destination open a panel
 * spanning the bar; moving between two menus slides the panel's contents
 * sideways rather than closing and reopening it, and the trigger underneath
 * stays highlighted while its panel is up.
 */
export function PublicTopBar() {
  const { t } = useI18n();
  const location = useLocation();
  const isElevated = useHeaderElevation();
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [openMenuKey, setOpenMenuKey] = useState<string | null>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const menus: MenuSection[] = [
    {
      entries: [
        {
          body: t('public.searchBody'),
          icon: <Search className="size-4" />,
          label: t('nav.catalog'),
          to: routes.search,
        },
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
        {
          body: t('nav.airingCalendarBody'),
          icon: <CalendarDays className="size-4" />,
          label: t('nav.airingCalendar'),
          to: routes.calendar,
        },
        {
          body: t('nav.broadcastBoardBody'),
          icon: <LayoutGrid className="size-4" />,
          label: t('nav.broadcastBoard'),
          to: routes.airing,
        },
      ],
      key: 'airing',
      label: t('nav.airing'),
    },
  ];

  const openIndex = menus.findIndex((menu) => menu.key === openMenuKey);
  const isOpen = openIndex >= 0;

  function cancelClose() {
    if (closeTimer.current !== null) {
      clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
  }

  function openMenu(key: string) {
    cancelClose();
    setOpenMenuKey(key);
  }

  function scheduleClose() {
    cancelClose();
    closeTimer.current = setTimeout(() => {
      setOpenMenuKey(null);
    }, closeGraceMs);
  }

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpenMenuKey(null);
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  // Navigating always leaves the panel behind.
  useEffect(() => {
    setOpenMenuKey(null);
  }, [location.pathname]);

  useEffect(
    () => () => {
      cancelClose();
    },
    [],
  );

  return (
    <>
      <header
        className={cn(
          'sticky top-0 z-[var(--ui-layer-shell-header)] h-[var(--ui-shell-header-height)] border-b',
          'bg-[color-mix(in_srgb,var(--ui-bg-canvas)_85%,transparent)] backdrop-blur-xl',
          'transition-[border-color,box-shadow] duration-[var(--ui-transition-standard)] ease-[var(--ui-ease-gentle)]',
          isElevated || isOpen
            ? 'border-[var(--ui-border)] shadow-[var(--ui-shadow-header)]'
            : 'border-[var(--ui-border-subtle)]',
        )}
      >
        <div className="relative mx-auto h-full max-w-[1160px] px-4 sm:px-5" onMouseLeave={scheduleClose}>
          <div className="flex h-full items-center gap-3">
            <Wordmark />

            <nav className="absolute left-1/2 hidden h-full -translate-x-1/2 items-center gap-0.5 lg:flex">
              <Link
                activeOptions={{ exact: true }}
                className={cn(triggerClassName, 'data-[status=active]:text-[var(--ui-text)]')}
                {...resolvedRouteHref(routes.home)}
              >
                {t('nav.home')}
              </Link>

              {menus.map((menu) => (
                <button
                  aria-expanded={openMenuKey === menu.key}
                  className={triggerClassName}
                  data-open={openMenuKey === menu.key ? '' : undefined}
                  key={menu.key}
                  type="button"
                  onClick={() => {
                    setOpenMenuKey((current) => (current === menu.key ? null : menu.key));
                  }}
                  onFocus={() => {
                    openMenu(menu.key);
                  }}
                  onMouseEnter={() => {
                    openMenu(menu.key);
                  }}
                >
                  {menu.label}
                  <ChevronDown className="size-3.5 transition-transform duration-[var(--ui-transition-standard)] ease-[var(--ui-ease-standard)] group-data-[open]:rotate-180" />
                </button>
              ))}

              <Link className={triggerClassName} {...resolvedRouteHref(routes.docsIntroduction)}>
                {t('nav.docs')}
              </Link>
            </nav>

            <div className="ml-auto flex items-center gap-1.5">
              <Button asChild className="hidden sm:inline-flex" size="default" variant="secondary">
                <Link to={routes.login}>{t('auth.login')}</Link>
              </Button>
              <Button asChild size="default">
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
                  setIsDrawerOpen(true);
                }}
              >
                <Menu className="size-4" />
              </Button>
            </div>
          </div>

          {/*
           * One panel for every menu: the open section owns the visible column,
           * and the row slides sideways when the pointer moves to a sibling
           * trigger.
           */}
          <AnimatePresence>
            {isOpen ? (
              <motion.div
                animate={{ opacity: 1, y: 0 }}
                className="absolute inset-x-4 top-full hidden sm:inset-x-5 lg:block"
                exit={{ opacity: 0, y: -6 }}
                initial={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.18, ease: easeStandard }}
              >
                <div className="overflow-hidden rounded-[var(--ui-radius-frame)] border border-[var(--ui-border)] bg-[var(--ui-bg-elevated)] shadow-[var(--ui-shadow-popup)]">
                  <motion.div
                    animate={{ x: `${String(openIndex * -100)}%` }}
                    className="flex"
                    transition={{ duration: 0.24, ease: easeStandard }}
                  >
                    {menus.map((menu) => (
                      <div
                        className={cn(
                          'grid w-full shrink-0 gap-1 p-2',
                          menu.entries.length > 2 ? 'sm:grid-cols-3' : 'sm:grid-cols-2',
                        )}
                        key={menu.key}
                      >
                        {menu.entries.map((entry) => (
                          <Link
                            className="grid grid-cols-[auto_minmax(0,1fr)] items-start gap-3 rounded-[var(--ui-radius-surface)] px-3 py-3 transition-colors duration-[var(--ui-transition-fast)] hover:bg-[var(--ui-bg-subtle)]"
                            key={entry.to}
                            onClick={() => {
                              setOpenMenuKey(null);
                            }}
                            {...resolvedRouteHref(entry.to)}
                          >
                            <span className="mt-0.5 grid size-8 place-items-center rounded-[var(--ui-radius-control)] border border-[var(--ui-border-subtle)] bg-[var(--ui-bg-surface)] text-[var(--ui-text-muted)]">
                              {entry.icon}
                            </span>
                            <span className="grid gap-1">
                              <span className="text-[13.5px] font-medium text-[var(--ui-text)]">{entry.label}</span>
                              {entry.body === undefined ? null : (
                                <span className="text-[12.5px] leading-5 text-[var(--ui-text-muted)]">
                                  {entry.body}
                                </span>
                              )}
                            </span>
                          </Link>
                        ))}
                      </div>
                    ))}
                  </motion.div>
                </div>
              </motion.div>
            ) : null}
          </AnimatePresence>
        </div>
      </header>

      <Dialog open={isDrawerOpen} onOpenChange={setIsDrawerOpen}>
        <DialogContent className="gap-0 p-0" closeLabel={t('public.closeMenu')} placement="left">
          <DialogHeader className="border-b border-[var(--ui-border-subtle)] px-4 py-3 pr-12">
            <DialogTitle className="flex items-center gap-2 text-sm">
              <img alt="" aria-hidden="true" className="size-6 rounded-[6px]" src={publicAssetPaths.appIcon} />
              Noshiro DB
            </DialogTitle>
          </DialogHeader>

          <div className="grid min-h-0 content-start gap-0.5 overflow-y-auto p-3">
            {[
              { label: t('nav.home'), to: routes.home },
              ...menus.flatMap((menu) => menu.entries.map((entry) => ({ label: entry.label, to: entry.to }))),
              { label: t('nav.docs'), to: routes.docsIntroduction },
            ].map((item) => (
              <Link
                className="inline-flex h-9 min-w-0 items-center rounded-[var(--ui-radius-control)] px-2 text-[13.5px] font-medium text-[var(--ui-text-muted)] transition-colors hover:bg-[var(--ui-bg-subtle)] hover:text-[var(--ui-text)] data-[status=active]:bg-[var(--ui-bg-muted)] data-[status=active]:text-[var(--ui-text)]"
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
            <Button asChild>
              <Link
                to={routes.register}
                onClick={() => {
                  setIsDrawerOpen(false);
                }}
              >
                {t('auth.register')}
              </Link>
            </Button>
            <Button asChild variant="secondary">
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
