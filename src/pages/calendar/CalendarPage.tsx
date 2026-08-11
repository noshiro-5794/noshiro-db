import { placeholderImagePaths } from '@/shared/assets/public-assets';
import { useMemo, useState } from 'react';
import { Link, useLocation } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { formatWeekday, type Locale, useI18n } from '@/shared/i18n';
import { calendarImageOf, flattenCalendarGroups, sortCalendarItems } from '@/features/search';
import { subjectQueries } from '@/entities/subject';
import type { CalendarGroup, CalendarSubjectItem, WeekdayEn } from '@/shared/api';
import { routes } from '@/shared/routing/paths';
import type { RouteBackState } from '@/shared/routing/route-state';
import { routeBackState } from '@/shared/routing/route-state';
import { Seo } from '@/shared/seo/Seo';
import { Badge } from '@/shared/ui/Badge';
import { ListSurface, ResultsMeta, ResultsState, type ResultsStatus } from '@/shared/ui/DataView';
import { Page } from '@/shared/ui/Page';
import { Toggle, ToggleGroup } from '@/shared/ui/Toggle';

const coverPlaceholder = placeholderImagePaths.subjectCover;
const weekdays = ['', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const;

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
      className="grid min-w-0 grid-cols-[72px_minmax(0,1fr)_auto] gap-4 border-b border-border-subtle p-3 transition-colors last:border-b-0 hover:bg-muted max-sm:grid-cols-[64px_minmax(0,1fr)]"
      data-slot="calendar-subject-row"
      state={state}
      to={routes.subject(item.subject_id)}
    >
      <img
        className="h-24 w-[72px] rounded-sm bg-muted object-cover ring-1 ring-border-subtle max-sm:h-[88px] max-sm:w-16"
        src={calendarImageOf(item) || coverPlaceholder}
        alt={titleOf(item, titleFallback)}
        decoding="async"
        loading="lazy"
        referrerPolicy="no-referrer"
      />
      <span className="grid min-w-0 content-center gap-2">
        <span className="line-clamp-2 text-base font-semibold leading-6 text-[var(--ui-text)]">
          {titleOf(item, titleFallback)}
        </span>
        {item.display_subtitle ? (
          <span className="line-clamp-1 text-sm text-[var(--ui-text-muted)]">{item.display_subtitle}</span>
        ) : null}
        <span className="flex min-w-0 flex-wrap items-center gap-2 text-xs font-medium text-[var(--ui-text-muted)]">
          <Badge>{item.subject_type}</Badge>
          <span>{item.weekday_en}</span>
          {item.platform ? <span className="min-w-0 truncate">{item.platform}</span> : null}
        </span>
      </span>
      <span className="self-center text-sm font-semibold tabular-nums text-[var(--ui-text-muted)] max-sm:col-start-2 max-sm:w-fit">
        {formatHeat(item.doing, locale)}
      </span>
    </Link>
  );
}

export function CalendarPage() {
  const { locale, t } = useI18n();
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
  const resultsStatus: ResultsStatus =
    calendarQuery.data === undefined && calendarQuery.isLoading
      ? 'loading'
      : calendarQuery.data === undefined && calendarQuery.isError
        ? 'error'
        : visibleItemCount === 0
          ? 'empty'
          : 'ready';
  const subjectLinkState = useMemo(() => routeBackState(location, t('calendar.title')), [location, t]);

  return (
    <Page title={t('calendar.title')} eyebrow={t('nav.groupDiscover')} seo={false}>
      <Seo
        title={t('calendar.title')}
        description="Browse the weekly anime calendar, discover airing titles by weekday, and open detailed subject pages."
        path={routes.calendar}
      />
      <div className="grid gap-6 pb-8">
        <ToggleGroup
          aria-label={t('calendar.title')}
          className="flex w-full overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
          variant="tab"
          value={[selectedWeekday || 'all']}
          onValueChange={(values) => {
            const nextWeekday = values[0];
            if (nextWeekday) setSelectedWeekday(nextWeekday === 'all' ? '' : nextWeekday);
          }}
        >
          {weekdays.map((weekday) => {
            const count = weekday ? (findGroup(groups, weekday)?.items.length ?? 0) : allItems.length;

            return (
              <Toggle key={weekday || 'all'} value={weekday || 'all'} variant="tab">
                {weekday ? formatWeekday(locale, weekday) : t('common.all')}
                <span className="ml-1 tabular-nums text-subtle-foreground">{count}</span>
              </Toggle>
            );
          })}
        </ToggleGroup>

        <ResultsMeta
          count={calendarQuery.data === undefined ? undefined : visibleItemCount}
          label={t('calendar.visibleItems')}
          pending={calendarQuery.isFetching && !calendarQuery.isLoading}
          pendingLabel={t('calendar.loading')}
        />

        <ResultsState
          emptyTitle={t('calendar.empty')}
          errorDescription={t('calendar.errorBody')}
          errorTitle={t('calendar.errorTitle')}
          loadingTitle={t('calendar.loading')}
          status={resultsStatus}
        >
          <div className="grid gap-6">
            {visibleGroups.map((group) => (
              <section className="grid gap-2" key={group.weekday.en}>
                <div className="flex items-center justify-between gap-3 px-1">
                  <h2 className="text-sm font-semibold text-foreground">{formatWeekday(locale, group.weekday.en)}</h2>
                  <span className="text-xs tabular-nums text-muted-foreground">
                    {group.items.length} {t('common.items')}
                  </span>
                </div>
                <ListSurface>
                  {group.items.map((item) => (
                    <CalendarSubjectRow
                      item={item}
                      key={item.subject_id}
                      locale={locale}
                      state={subjectLinkState}
                      titleFallback={t('common.untitledSubject')}
                    />
                  ))}
                </ListSurface>
              </section>
            ))}
          </div>
        </ResultsState>
      </div>
    </Page>
  );
}
