import { useMemo, useState } from 'react';
import { useLocation } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useI18n } from '@/shared/i18n';
import { subjectQueries } from '@/entities/subject';
import type { CalendarBoardEntry } from '@/shared/api';
import { routeBackState } from '@/shared/routing/route-state';
import { routes } from '@/shared/routing/paths';
import { Seo } from '@/shared/seo/Seo';
import { Page } from '@/shared/ui/Page';
import { ResultsState, type ResultsStatus } from '@/shared/ui/DataView';
import {
  AIRING_TIME_ZONE,
  AIRING_TIME_ZONE_LABEL,
  addDays,
  buildOccurrences,
  groupOccurrences,
  monthGridRange,
  occurrenceFor,
  rangeDays,
  isWithin,
  boardWindow,
  shiftMonth,
  startOfWeek,
  weekRange,
  type CalendarOccurrence,
} from './calendar-model';
import { BroadcastBoard } from './ui/BroadcastBoard';
import { EventDetails } from './ui/EventDetails';
import { MonthGrid } from './ui/MonthGrid';
import { IconButton, SegmentedControl } from './ui/primitives';
import { TimeGrid } from './ui/TimeGrid';
import './calendar.css';

type CalendarLayout = 'calendar' | 'chart';
type CalendarView = 'month' | 'week' | 'day';

const layoutOptions: { value: CalendarLayout; labelKey: 'calendar.layoutCalendar' | 'calendar.layoutChart' }[] = [
  { value: 'calendar', labelKey: 'calendar.layoutCalendar' },
  { value: 'chart', labelKey: 'calendar.layoutChart' },
];

const viewOptions: { value: CalendarView; labelKey: 'calendar.month' | 'calendar.week' | 'calendar.day' }[] = [
  { value: 'month', labelKey: 'calendar.month' },
  { value: 'week', labelKey: 'calendar.week' },
  { value: 'day', labelKey: 'calendar.day' },
];

export function CalendarPage() {
  const { locale, t } = useI18n();
  const location = useLocation();
  const [layout, setLayout] = useState<CalendarLayout>('calendar');
  const [view, setView] = useState<CalendarView>('month');
  const [cursor, setCursor] = useState(() => new Date());
  const [selected, setSelected] = useState<CalendarOccurrence | null>(null);

  const calendarQuery = useQuery(subjectQueries.calendarBoard());
  const entries = useMemo(() => calendarQuery.data ?? [], [calendarQuery.data]);
  const subjectLinkState = useMemo(() => routeBackState(location, t('calendar.title')), [location, t]);
  /**
   * The board covers the previous, current and next month, so every month a
   * visitor lands on can show the month before and after it while the outer
   * bound still stops the weekly schedule from repeating forever.
   */
  const season = useMemo(() => boardWindow(entries[0]), [entries]);

  const range = useMemo(() => {
    if (layout === 'chart') return weekRange(cursor);
    if (view === 'month') return monthGridRange(cursor);
    if (view === 'week') return weekRange(cursor);
    return { from: cursor, to: cursor };
  }, [cursor, layout, view]);

  const daysMap = useMemo(
    () => groupOccurrences(buildOccurrences(entries, range.from, range.to, season)),
    [entries, range, season],
  );
  const days = useMemo(() => rangeDays(range.from, range.to), [range]);

  const status: ResultsStatus =
    calendarQuery.data === undefined && calendarQuery.isLoading
      ? 'loading'
      : calendarQuery.data === undefined && calendarQuery.isError
        ? 'error'
        : entries.length === 0
          ? 'empty'
          : 'ready';

  const move = (direction: -1 | 1) => {
    if (layout === 'chart') return;
    setCursor((current) => {
      const next = step(current, direction);
      return isWithin(next, season) ? next : current;
    });
  };

  const goToday = () => {
    const now = new Date();
    setCursor(season && !isWithin(now, season) ? new Date(season.to) : now);
  };

  const step = (from: Date, direction: -1 | 1) =>
    view === 'month' ? shiftMonth(from, direction) : addDays(from, direction * (view === 'week' ? 7 : 1));

  const canStep = (direction: -1 | 1) => layout === 'chart' || isWithin(step(cursor, direction), season);

  const openEntryInBoard = (entry: CalendarBoardEntry) => {
    setSelected(occurrenceFor(entry, cursor));
  };

  const title = useMemo(() => {
    if (layout === 'chart') return t('calendar.layoutChart');
    if (view === 'month') {
      return new Intl.DateTimeFormat(locale, { year: 'numeric', month: 'long' }).format(cursor);
    }
    if (view === 'week') {
      const from = startOfWeek(cursor);
      const to = addDays(from, 6);
      const formatter = new Intl.DateTimeFormat(locale, { month: 'short', day: 'numeric' });
      return `${formatter.format(from)} – ${formatter.format(to)}`;
    }
    return new Intl.DateTimeFormat(locale, { month: 'long', day: 'numeric', weekday: 'long' }).format(cursor);
  }, [cursor, layout, locale, t, view]);

  return (
    <Page eyebrow={t('nav.groupDiscover')} seo={false} title={t('calendar.title')} width="wide">
      <Seo
        description="Browse the anime airing calendar by month, week, or day."
        path={routes.calendar}
        title={t('calendar.title')}
      />
      <div className="grid gap-3 pb-10">
        <header className="grid gap-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <button
                className="h-8 shrink-0 rounded-[8px] border border-[var(--ui-border)] px-3.5 text-xs font-medium text-[var(--ui-text)] transition-colors hover:bg-[var(--ui-bg-subtle)]"
                onClick={goToday}
                type="button"
              >
                {t('calendar.today')}
              </button>
              <span className="flex items-center">
                <IconButton
                  className={canStep(-1) ? undefined : 'opacity-30'}
                  label={t('calendar.previous')}
                  onClick={() => {
                    move(-1);
                  }}
                >
                  <ChevronLeft className="size-4" />
                </IconButton>
                <IconButton
                  className={canStep(1) ? undefined : 'opacity-30'}
                  label={t('calendar.next')}
                  onClick={() => {
                    move(1);
                  }}
                >
                  <ChevronRight className="size-4" />
                </IconButton>
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <SegmentedControl
                ariaLabel={t('calendar.layoutAria')}
                onChange={setLayout}
                options={layoutOptions.map((option) => ({ value: option.value, label: t(option.labelKey) }))}
                value={layout}
              />
              {layout === 'calendar' ? (
                <SegmentedControl
                  ariaLabel={t('calendar.viewAria')}
                  onChange={setView}
                  options={viewOptions.map((option) => ({ value: option.value, label: t(option.labelKey) }))}
                  value={view}
                />
              ) : null}
            </div>
          </div>
          <div className="flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-1">
            <h1 className="min-w-0 truncate text-[28px] font-semibold tracking-tight text-[var(--ui-text)]">{title}</h1>
            {layout === 'chart' ? (
              <span className="text-xs tabular-nums text-[var(--ui-text-muted)]">
                {`${entries.length} ${t('calendar.itemsUnit')}`}
              </span>
            ) : null}
            <span
              className="rounded-[6px] border border-[var(--cal-hairline)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--ui-text-subtle)]"
              title={AIRING_TIME_ZONE}
            >
              {AIRING_TIME_ZONE_LABEL}
            </span>
          </div>
        </header>

        <ResultsState
          emptyTitle={t('calendar.empty')}
          errorDescription={t('calendar.errorBody')}
          errorTitle={t('calendar.errorTitle')}
          loadingTitle={t('calendar.loading')}
          status={status}
        >
          {layout === 'chart' ? (
            <BroadcastBoard
              emptyLabel={t('calendar.empty')}
              entries={entries}
              onOpen={openEntryInBoard}
              state={subjectLinkState}
            />
          ) : (
            <>
              {view === 'month' ? (
                <MonthGrid
                  days={days}
                  daysMap={daysMap}
                  month={cursor}
                  onOpenOccurrence={setSelected}
                  onSelectDate={(date) => {
                    setCursor(date);
                    setView('day');
                  }}
                />
              ) : null}
              {view === 'week' || view === 'day' ? (
                <TimeGrid days={days} daysMap={daysMap} onOpenOccurrence={setSelected} />
              ) : null}
            </>
          )}
        </ResultsState>
      </div>
      {selected ? (
        <EventDetails
          occurrence={selected}
          onClose={() => {
            setSelected(null);
          }}
          state={subjectLinkState}
        />
      ) : null}
    </Page>
  );
}
