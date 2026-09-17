import { useMemo, useState } from 'react';
import { useLocation } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useI18n } from '@/shared/i18n';
import { subjectQueries } from '@/entities/subject';
import { routeBackState } from '@/shared/routing/route-state';
import { routes } from '@/shared/routing/paths';
import { Seo } from '@/shared/seo/Seo';
import { Page } from '@/shared/ui/Page';
import { ResultsState, type ResultsStatus } from '@/shared/ui/DataView';
import { CalendarEventDetails, DayView, MonthView, WeekView } from './CalendarViews';
import {
  addDays,
  addMonths,
  buildOccurrences,
  dateKey,
  groupOccurrences,
  monthGridRange,
  rangeDays,
  startOfWeek,
  weekRange,
  type CalendarOccurrence,
} from './calendar-model';

type CalendarViewMode = 'month' | 'week' | 'day';

const viewModes: CalendarViewMode[] = ['month', 'week', 'day'];

export function CalendarPage() {
  const { locale, t } = useI18n();
  const location = useLocation();
  const [view, setView] = useState<CalendarViewMode>('month');
  const [cursor, setCursor] = useState(() => new Date());
  const [selected, setSelected] = useState<CalendarOccurrence | null>(null);
  const calendarQuery = useQuery(subjectQueries.calendarBoard());
  const entries = useMemo(() => calendarQuery.data ?? [], [calendarQuery.data]);
  const subjectLinkState = useMemo(() => routeBackState(location, t('calendar.title')), [location, t]);

  const range = useMemo(() => {
    if (view === 'month') return monthGridRange(cursor);
    if (view === 'week') return weekRange(cursor);
    return { from: cursor, to: cursor };
  }, [cursor, view]);

  const days = useMemo(() => rangeDays(range.from, range.to), [range]);
  const daysMap = useMemo(() => groupOccurrences(buildOccurrences(entries, range.from, range.to)), [entries, range]);
  const status: ResultsStatus =
    calendarQuery.data === undefined && calendarQuery.isLoading
      ? 'loading'
      : calendarQuery.data === undefined && calendarQuery.isError
        ? 'error'
        : entries.length === 0
          ? 'empty'
          : 'ready';

  const move = (direction: -1 | 1) => {
    if (view === 'month') {
      setCursor((current) => addMonths(current, direction));
      return;
    }
    if (view === 'week') {
      setCursor((current) => addDays(current, direction * 7));
      return;
    }
    setCursor((current) => addDays(current, direction));
  };

  const title =
    view === 'month'
      ? new Intl.DateTimeFormat(locale, { year: 'numeric', month: 'long' }).format(cursor)
      : view === 'week'
        ? `${new Intl.DateTimeFormat(locale, { month: 'short', day: 'numeric' }).format(startOfWeek(cursor))} – ${new Intl.DateTimeFormat(locale, { month: 'short', day: 'numeric' }).format(addDays(startOfWeek(cursor), 6))}`
        : new Intl.DateTimeFormat(locale, { month: 'long', day: 'numeric', weekday: 'long' }).format(cursor);

  return (
    <Page title={t('calendar.title')} eyebrow={t('nav.groupDiscover')} seo={false}>
      <Seo
        title={t('calendar.title')}
        description="Browse the anime airing calendar by month, week, or day."
        path={routes.calendar}
      />
      <div className="grid gap-4 pb-10">
        <header className="grid gap-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1">
              <button
                aria-label="Previous"
                className="grid h-8 w-8 place-items-center rounded-full border border-[var(--ui-border)] text-[var(--ui-text-muted)]"
                onClick={() => {
                  move(-1);
                }}
                type="button"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                className="h-8 rounded-full border border-[var(--ui-border)] px-3 text-xs font-medium text-[var(--ui-text)]"
                onClick={() => {
                  setCursor(new Date());
                }}
                type="button"
              >
                {t('calendar.today')}
              </button>
              <button
                aria-label="Next"
                className="grid h-8 w-8 place-items-center rounded-full border border-[var(--ui-border)] text-[var(--ui-text-muted)]"
                onClick={() => {
                  move(1);
                }}
                type="button"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
            <h1 className="min-w-0 truncate text-base font-semibold text-[var(--ui-text)]">{title}</h1>
          </div>
          <div
            aria-label={t('calendar.title')}
            className="inline-flex w-fit items-center gap-1 rounded-full border border-[var(--ui-border)] bg-[var(--ui-bg-surface)] p-0.5"
            role="tablist"
          >
            {viewModes.map((mode) => (
              <button
                aria-selected={view === mode}
                className={[
                  'rounded-full px-3 py-1 text-xs font-medium transition-colors',
                  view === mode
                    ? 'bg-[var(--ui-accent)] text-[var(--ui-accent-contrast)]'
                    : 'text-[var(--ui-text-muted)]',
                ].join(' ')}
                key={mode}
                onClick={() => {
                  setView(mode);
                }}
                role="tab"
                type="button"
              >
                {t(`calendar.${mode}`)}
              </button>
            ))}
          </div>
        </header>

        <ResultsState
          emptyTitle={t('calendar.empty')}
          errorDescription={t('calendar.errorBody')}
          errorTitle={t('calendar.errorTitle')}
          loadingTitle={t('calendar.loading')}
          status={status}
        >
          {view === 'month' ? (
            <MonthView
              days={days}
              daysMap={daysMap}
              locale={locale}
              month={cursor}
              onOpenOccurrence={setSelected}
              onSelectDate={(date) => {
                setCursor(date);
                setView('day');
              }}
            />
          ) : null}
          {view === 'week' ? (
            <WeekView days={days} daysMap={daysMap} locale={locale} onOpenOccurrence={setSelected} />
          ) : null}
          {view === 'day' ? (
            <DayView date={cursor} day={daysMap.get(dateKey(cursor))} locale={locale} onOpenOccurrence={setSelected} />
          ) : null}
        </ResultsState>
      </div>
      {selected ? (
        <CalendarEventDetails
          locale={locale}
          occurrence={selected}
          state={subjectLinkState}
          onClose={() => {
            setSelected(null);
          }}
        />
      ) : null}
    </Page>
  );
}
