import { useMemo, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/features/auth/use-auth';
import type { Locale } from '@/features/i18n/messages';
import { useI18n } from '@/features/i18n/use-i18n';
import { calendarImageOf, flattenCalendarGroups, sortCalendarItems } from '@/features/search/calendar-search';
import { subjectQueries } from '@/features/subjects/subject-queries';
import type { CalendarGroup, CalendarSubjectItem, WeekdayEn } from '@/lib/api/types';
import { routes } from '@/routes/paths';
import type { RouteBackState } from '@/shared/navigation/route-state';
import { routeBackState } from '@/shared/navigation/route-state';
import { Seo } from '@/shared/seo/Seo';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';

const coverPlaceholder = '/assets/placeholders/subject-cover.png';
const weekdays = ['', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const;

const weekdayLabels: Record<Locale, Record<(typeof weekdays)[number], string>> = {
  'zh-CN': {
    '': '全部',
    Mon: '周一',
    Tue: '周二',
    Wed: '周三',
    Thu: '周四',
    Fri: '周五',
    Sat: '周六',
    Sun: '周日',
  },
  'en-US': {
    '': 'All',
    Mon: 'Mon',
    Tue: 'Tue',
    Wed: 'Wed',
    Thu: 'Thu',
    Fri: 'Fri',
    Sat: 'Sat',
    Sun: 'Sun',
  },
  'ja-JP': {
    '': 'すべて',
    Mon: '月',
    Tue: '火',
    Wed: '水',
    Thu: '木',
    Fri: '金',
    Sat: '土',
    Sun: '日',
  },
};

function titleOf(item: CalendarSubjectItem, fallback: string) {
  return item.display_title || item.title || item.title_cn || fallback;
}

function formatHeat(value: number, locale: Locale) {
  return new Intl.NumberFormat(locale, { notation: value >= 10000 ? 'compact' : 'standard' }).format(value);
}

function findGroup(groups: CalendarGroup[], weekday: WeekdayEn) {
  return groups.find((group) => group.weekday.en === weekday);
}

function CalendarSubjectRow({
  item,
  locale,
  state,
  titleFallback,
}: {
  item: CalendarSubjectItem;
  locale: Locale;
  state: RouteBackState;
  titleFallback: string;
}) {
  return (
    <Link
      className="grid min-w-0 grid-cols-[72px_minmax(0,1fr)_auto] gap-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3 shadow-sm transition hover:-translate-y-0.5 hover:border-[var(--color-accent-border)] hover:shadow-[var(--shadow-soft)] max-sm:grid-cols-[64px_minmax(0,1fr)]"
      state={state}
      to={routes.subject(item.subject_id)}
    >
      <img
        className="h-24 w-[72px] rounded-lg bg-[var(--color-surface-muted)] object-cover max-sm:h-[88px] max-sm:w-16"
        src={calendarImageOf(item) || coverPlaceholder}
        alt={titleOf(item, titleFallback)}
        loading="lazy"
      />
      <span className="grid min-w-0 content-center gap-2">
        <span className="line-clamp-2 text-base font-semibold leading-6 text-[var(--color-text)]">{titleOf(item, titleFallback)}</span>
        {item.display_subtitle ? (
          <span className="line-clamp-1 text-sm text-neutral-500 dark:text-neutral-400">{item.display_subtitle}</span>
        ) : null}
        <span className="flex min-w-0 flex-wrap items-center gap-2 text-xs font-medium text-neutral-500 dark:text-neutral-400">
          <span className="rounded-full bg-[var(--color-surface-muted)] px-2 py-1">{item.subject_type}</span>
          <span>{item.weekday_en}</span>
          {item.platform ? <span className="min-w-0 truncate">{item.platform}</span> : null}
        </span>
      </span>
      <span className="self-center rounded-full bg-[var(--color-surface-muted)] px-3 py-1 text-sm font-semibold text-[var(--color-text-muted)] max-sm:col-start-2 max-sm:w-fit">
        {formatHeat(item.doing, locale)}
      </span>
    </Link>
  );
}

export function CalendarPage() {
  const { locale, t } = useI18n();
  const { role } = useAuth();
  const location = useLocation();
  const [selectedWeekday, setSelectedWeekday] = useState<WeekdayEn | ''>('');
  const calendarQuery = useQuery(subjectQueries.calendar());
  const groups = useMemo(() => calendarQuery.data ?? [], [calendarQuery.data]);

  const allItems = useMemo(() => sortCalendarItems(flattenCalendarGroups(groups)), [groups]);
  const visibleGroups = useMemo(() => {
    if (!selectedWeekday) {
      return groups;
    }
    const group = findGroup(groups, selectedWeekday);
    return group ? [group] : [];
  }, [groups, selectedWeekday]);
  const visibleItemCount = selectedWeekday ? (findGroup(groups, selectedWeekday)?.items.length ?? 0) : allItems.length;
  const hottestItems = allItems.slice(0, 5);
  const subjectLinkState = useMemo(() => routeBackState(location, t('calendar.title')), [location, t]);

  return (
    <Page
      title={t('calendar.title')}
      eyebrow={t('nav.groupDiscover')}
      hideHeader={role === 'guest'}
    >
      <Seo
        title={t('calendar.title')}
        description="Browse the weekly anime calendar, discover airing titles by weekday, and open detailed subject pages."
        path={routes.calendar}
      />
      <div className="grid gap-6 pb-8">
        <div className="flex flex-wrap gap-2">
            {weekdays.map((weekday) => {
              const isActive = selectedWeekday === weekday;
              const count = weekday ? (findGroup(groups, weekday)?.items.length ?? 0) : allItems.length;

              return (
                <button
                  className={`rounded-full border px-3 py-1.5 text-sm font-semibold transition ${
                    isActive
                      ? 'border-[var(--color-border)] bg-[var(--color-surface-elevated)] text-[var(--color-text)] shadow-sm'
                      : 'border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-text-muted)] hover:border-[var(--color-accent-border)] hover:text-[var(--color-text)]'
                  }`}
                  key={weekday || 'all'}
                  type="button"
                  onClick={() => setSelectedWeekday(weekday)}
                >
                  {weekdayLabels[locale][weekday]}
                  <span className="ml-1 opacity-60">{count}</span>
                </button>
              );
            })}
          </div>

        {calendarQuery.isLoading ? <LoadingState title={t('calendar.loading')} /> : null}
        {calendarQuery.isError ? <ErrorState title={t('search.errorTitle')} description={t('search.errorBody')} /> : null}

        {!calendarQuery.isLoading && !calendarQuery.isError && allItems.length === 0 ? (
          <EmptyState title={t('calendar.empty')} />
        ) : null}

        <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
          <aside className="grid content-start gap-3">
            <section className="content-filter-panel">
              <span className="text-xs font-semibold uppercase text-neutral-500 dark:text-neutral-400">{t('calendar.overview')}</span>
              <div className="mt-4 grid grid-cols-2 gap-3">
                <div>
                  <strong className="text-2xl text-[var(--color-text)]">{allItems.length}</strong>
                  <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">{t('calendar.weeklyItems')}</p>
                </div>
                <div>
                  <strong className="text-2xl text-[var(--color-text)]">{visibleItemCount}</strong>
                  <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">{t('calendar.visibleItems')}</p>
                </div>
              </div>
            </section>

            <section className="content-filter-panel">
              <span className="text-xs font-semibold uppercase text-neutral-500 dark:text-neutral-400">{t('calendar.trending')}</span>
              <div className="mt-3 grid gap-2">
                {hottestItems.map((item) => (
                  <Link className="grid min-w-0 grid-cols-[42px_minmax(0,1fr)] gap-2 rounded-lg p-1.5 transition hover:bg-[var(--color-surface-muted)]" key={item.subject_id} state={subjectLinkState} to={routes.subject(item.subject_id)}>
                    <img className="h-14 w-[42px] rounded-md bg-[var(--color-surface-muted)] object-cover" src={calendarImageOf(item) || coverPlaceholder} alt={titleOf(item, t('common.untitledSubject'))} loading="lazy" />
                    <span className="grid min-w-0 content-center">
                      <span className="truncate text-sm font-semibold text-[var(--color-text)]">{titleOf(item, t('common.untitledSubject'))}</span>
                      <span className="text-xs text-neutral-500 dark:text-neutral-400">{formatHeat(item.doing, locale)}</span>
                    </span>
                  </Link>
                ))}
              </div>
            </section>
          </aside>

          <div className="grid gap-6">
            {visibleGroups.map((group) => (
              <section className="grid gap-3" key={group.weekday.en}>
                <div className="flex items-center justify-between gap-3">
                  <h2 className="text-xl font-semibold tracking-tight text-[var(--color-text)]">
                    {weekdayLabels[locale][group.weekday.en]}
                  </h2>
                  <span className="text-sm text-neutral-500 dark:text-neutral-400">{group.items.length} {t('common.items')}</span>
                </div>
                <div className="grid gap-3">
                  {group.items.map((item) => (
                    <CalendarSubjectRow item={item} key={item.subject_id} locale={locale} state={subjectLinkState} titleFallback={t('common.untitledSubject')} />
                  ))}
                </div>
              </section>
            ))}
          </div>
        </div>
      </div>
    </Page>
  );
}
