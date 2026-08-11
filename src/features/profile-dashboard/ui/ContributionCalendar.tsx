import { useMemo } from 'react';
import { CalendarDays } from 'lucide-react';
import type { ProfileStats } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Toggle, ToggleGroup } from '@/shared/ui/Toggle';
import { buildYearDays, contributionLevel, getWeekIndex } from '../model/contribution-calendar';

const heatClasses = [
  'bg-[var(--ui-bg-subtle)] text-transparent',
  'bg-[var(--ui-accent-soft)] text-[var(--ui-accent-text)]',
  'bg-[var(--ui-accent)] text-white opacity-60',
  'bg-[var(--ui-accent)] text-white opacity-80',
  'bg-[var(--ui-accent-solid)] text-[var(--ui-accent-solid-text)]',
] as const;

function heatClass(count: number) {
  return heatClasses[contributionLevel(count)];
}

export function ContributionCalendar({
  availableYears,
  isError,
  isLoading,
  markCalendar,
  marksInYear,
  selectedYear,
  onYearChange,
}: {
  availableYears: number[];
  isError: boolean;
  isLoading: boolean;
  markCalendar: ProfileStats['mark_calendar'];
  marksInYear: number;
  selectedYear: number;
  onYearChange: (year: number) => void;
}) {
  const { locale, t } = useI18n();
  const currentYear = new Date().getFullYear();
  const days = useMemo(() => buildYearDays(selectedYear), [selectedYear]);
  const countByDate = useMemo(() => new Map(markCalendar.map((item) => [item.date, item.count])), [markCalendar]);
  const yearOptions = useMemo(() => {
    const years = new Set([currentYear, selectedYear, ...availableYears]);
    return [...years].sort((a, b) => b - a);
  }, [availableYears, currentYear, selectedYear]);
  const monthPositions = useMemo(
    () =>
      Array.from({ length: 12 }, (_, month) => {
        const date = new Date(Date.UTC(selectedYear, month, 1));
        return {
          label: new Intl.DateTimeFormat(locale, { month: 'short', timeZone: 'UTC' }).format(date),
          week: getWeekIndex(date.toISOString().slice(0, 10)),
        };
      }),
    [locale, selectedYear],
  );

  return (
    <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1fr)_96px]" data-slot="contribution-calendar">
      <div className="min-w-0 rounded-sm border border-border bg-surface p-3 sm:p-4" data-slot="contribution-grid">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <CalendarDays className="size-4 text-subtle-foreground" />
            <p className="text-sm font-medium text-foreground">
              {marksInYear} {t('me.dashboard.marksIn')} {selectedYear}
            </p>
          </div>
          <div className="flex items-center gap-1 text-xs text-muted-foreground" data-slot="contribution-legend">
            <span>{t('me.dashboard.less')}</span>
            {[0, 1, 3, 6, 8].map((count) => (
              <span aria-hidden="true" className={`size-3 rounded-[3px] ${heatClass(count)}`} key={count} />
            ))}
            <span>{t('me.dashboard.more')}</span>
          </div>
        </div>
        {isLoading ? <LoadingState title={t('me.dashboard.loadingActivity')} /> : null}
        {isError ? (
          <ErrorState title={t('profile.contentErrorTitle')} description={t('profile.contentErrorBody')} />
        ) : null}
        {!isLoading && !isError ? (
          <div className="mt-4 overflow-x-auto pb-2" data-slot="contribution-heatmap">
            <div className="min-w-[760px]">
              <div className="relative mb-2 h-4 text-[11px] text-subtle-foreground">
                {monthPositions.map((month) => (
                  <span
                    className="absolute"
                    key={`${month.week}:${month.label}`}
                    style={{ left: `${month.week * 18}px` }}
                  >
                    {month.label}
                  </span>
                ))}
              </div>
              <div className="grid grid-flow-col grid-rows-7 gap-1" style={{ gridAutoColumns: '14px' }}>
                {days.map((day) => {
                  const count = countByDate.get(day) ?? 0;
                  return (
                    <span
                      aria-label={`${day}: ${count}`}
                      className={`grid size-3.5 place-items-center rounded-[3px] text-[9px] font-semibold leading-none ${heatClass(count)}`}
                      key={day}
                      title={`${day}: ${count}`}
                    />
                  );
                })}
              </div>
            </div>
          </div>
        ) : null}
      </div>

      <ToggleGroup
        aria-label={t('me.dashboard.activity')}
        className="flex min-w-0 gap-1 overflow-x-auto border-0 border-t border-border-subtle bg-transparent pt-3 lg:grid lg:content-start lg:overflow-visible lg:border-l lg:border-t-0 lg:pl-3 lg:pt-0"
        data-slot="contribution-year-selector"
        orientation="vertical"
        value={[String(selectedYear)]}
        onValueChange={(values) => {
          const nextYear = Number(values[0]);
          if (Number.isSafeInteger(nextYear)) onYearChange(nextYear);
        }}
      >
        {yearOptions.map((year) => (
          <Toggle
            className="min-w-16 rounded-sm px-2.5 py-2 text-left text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground data-[pressed]:bg-[var(--ui-accent-soft)] data-[pressed]:text-[var(--ui-accent-text)] lg:min-w-0"
            key={year}
            value={String(year)}
            variant="bare"
          >
            {year}
          </Toggle>
        ))}
      </ToggleGroup>
    </div>
  );
}
