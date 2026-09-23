import { useI18n } from '@/shared/i18n';
import { cn } from '@/shared/lib/cn';
import {
  dateKey,
  formatTime,
  isSameDay,
  titleOf,
  weekdayLabels,
  type CalendarDay,
  type CalendarOccurrence,
} from '../model/calendar-model';
import { Panel } from './primitives';

const MAX_BARS_PER_DAY = 3;

function dayEntries(day: CalendarDay | undefined): CalendarOccurrence[] {
  if (!day) return [];
  return [...day.timed, ...day.tentative];
}

/**
 * Google Calendar month grid: a hairline grid of day cells with solid,
 * provider-tinted event bars and a per-day overflow counter.
 */
export function MonthGrid({
  days,
  daysMap,
  month,
  onOpenOccurrence,
  onSelectDate,
}: {
  days: Date[];
  daysMap: Map<string, CalendarDay>;
  month: Date;
  onOpenOccurrence: (occurrence: CalendarOccurrence) => void;
  onSelectDate: (date: Date) => void;
}) {
  const { locale, t } = useI18n();
  const labels = weekdayLabels(locale);
  const today = new Date();

  return (
    <Panel>
      <div className="grid grid-cols-7 border-b border-[var(--cal-hairline)]">
        {labels.map((label) => (
          <div className="py-2.5 text-center text-[13px] font-medium text-[var(--cal-muted)]" key={label}>
            {label}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-7">
        {days.map((day) => {
          const entries = dayEntries(daysMap.get(dateKey(day)));
          const outside = day.getMonth() !== month.getMonth();
          const isToday = isSameDay(day, today);
          return (
            <div
              className={cn(
                'group/cell relative min-h-[132px] border-b border-r border-[var(--cal-hairline)] px-1.5 pb-2 pt-2 last:border-r-0',
                'hover:bg-[var(--ui-bg-inset)]',
              )}
              key={dateKey(day)}
            >
              <div className="mb-1.5 flex justify-center">
                <button
                  className={cn(
                    'grid h-6 min-w-6 place-items-center rounded-[6px] px-1.5 text-[13px] tabular-nums transition-colors',
                    outside ? 'text-[var(--ui-text-placeholder)]' : 'text-[var(--ui-text-muted)]',
                    isToday
                      ? 'calendar-today font-semibold'
                      : 'hover:bg-[var(--ui-bg-muted)] hover:text-[var(--ui-text)]',
                  )}
                  onClick={() => {
                    onSelectDate(day);
                  }}
                  type="button"
                >
                  {day.getDate()}
                </button>
              </div>
              <div className={cn('grid gap-[3px]', outside && 'opacity-45')}>
                {entries.slice(0, MAX_BARS_PER_DAY).map((occurrence) => (
                  <EventBar key={occurrence.key} occurrence={occurrence} onOpen={onOpenOccurrence} />
                ))}
                {entries.length > MAX_BARS_PER_DAY ? (
                  <button
                    className="rounded px-1.5 py-0.5 text-left text-[10px] font-medium text-[var(--ui-text-muted)] hover:bg-[var(--ui-bg-muted)] hover:text-[var(--ui-text)]"
                    onClick={() => {
                      onSelectDate(day);
                    }}
                    type="button"
                  >
                    {`+${entries.length - MAX_BARS_PER_DAY} ${t('calendar.more')}`}
                  </button>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}

function EventBar({
  occurrence,
  onOpen,
}: {
  occurrence: CalendarOccurrence;
  onOpen: (occurrence: CalendarOccurrence) => void;
}) {
  const { locale } = useI18n();
  const time = formatTime(occurrence.startMinutes, locale);
  const provider = occurrence.entry.sources[0]?.provider ?? 'unknown';
  return (
    <button
      className={cn(
        'calendar-bar flex w-full min-w-0 items-center gap-1 overflow-hidden rounded-[6px] py-[3px] pl-1.5 pr-2 text-left text-[12px] font-medium',
        occurrence.tentative && 'opacity-75',
      )}
      data-cal-source={provider}
      onClick={(event) => {
        event.stopPropagation();
        onOpen(occurrence);
      }}
      title={`${time ? `${time} ` : ''}${titleOf(occurrence)}`}
      type="button"
    >
      {time ? <span className="shrink-0 tabular-nums opacity-90">{time}</span> : null}
      <span className="truncate">{titleOf(occurrence)}</span>
    </button>
  );
}
