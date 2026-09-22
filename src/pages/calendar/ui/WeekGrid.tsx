import { useMemo } from 'react';
import { useI18n } from '@/shared/i18n';
import { cn } from '@/shared/lib/cn';
import {
  dateKey,
  formatTime,
  formatWeekday,
  isSameDay,
  layoutOccurrences,
  nowMinutes,
  titleOf,
  type CalendarDay,
  type CalendarOccurrence,
} from '../calendar-model';
import { Panel } from './primitives';

const HOUR_HEIGHT = 56;
const MIN_VISIBLE_HOUR = 18;
const MAX_VISIBLE_HOUR = 29;

/**
 * Google Calendar week grid: an all-day/unscheduled strip above an hour grid
 * with positioned, provider-tinted blocks and a current-time indicator.
 */
export function WeekGrid({
  days,
  daysMap,
  onOpenOccurrence,
}: {
  days: Date[];
  daysMap: Map<string, CalendarDay>;
  onOpenOccurrence: (occurrence: CalendarOccurrence) => void;
}) {
  const { locale, t } = useI18n();
  const today = new Date();
  const bounds = useMemo(() => {
    const hours = days.flatMap((day) =>
      (daysMap.get(dateKey(day))?.timed ?? []).flatMap((occurrence) =>
        occurrence.startMinutes === null ? [] : [Math.floor(occurrence.startMinutes / 60)],
      ),
    );
    const from = Math.max(0, Math.min(MIN_VISIBLE_HOUR, ...hours) - 1);
    const to = Math.min(MAX_VISIBLE_HOUR, Math.max(MIN_VISIBLE_HOUR + 6, ...hours.map((hour) => hour + 1)));
    return { from, to };
  }, [days, daysMap]);

  const hours = Array.from({ length: bounds.to - bounds.from }, (_, index) => bounds.from + index);
  const height = hours.length * HOUR_HEIGHT;

  return (
    <Panel>
      <div className="grid grid-cols-[52px_repeat(7,minmax(104px,1fr))] border-b border-[var(--ui-border-subtle)]">
        <div />
        {days.map((day) => (
          <div
            className={cn(
              'border-l border-[var(--ui-border-subtle)] px-2 py-1.5 text-center',
              isSameDay(day, today) ? 'text-[var(--ui-accent-text)]' : 'text-[var(--ui-text-muted)]',
            )}
            key={dateKey(day)}
          >
            <div className="text-[10px] font-semibold uppercase tracking-[0.06em]">{formatWeekday(day, locale)}</div>
            <div
              className={cn(
                'mx-auto mt-0.5 grid size-6 place-items-center rounded-full text-[12px] font-medium tabular-nums',
                isSameDay(day, today)
                  ? 'bg-[var(--ui-accent)] text-[var(--ui-accent-contrast)]'
                  : 'text-[var(--ui-text)]',
              )}
            >
              {day.getDate()}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-[52px_repeat(7,minmax(104px,1fr))] border-b border-[var(--ui-border-subtle)] bg-[var(--ui-bg-inset)]">
        <div className="px-1 py-1.5 text-right text-[10px] font-medium uppercase tracking-wide text-[var(--ui-text-subtle)]">
          {t('calendar.unscheduled')}
        </div>
        {days.map((day) => (
          <div className="grid min-h-[30px] gap-0.5 border-l border-[var(--ui-border-subtle)] p-1" key={dateKey(day)}>
            {(daysMap.get(dateKey(day))?.tentative ?? []).slice(0, 3).map((occurrence) => (
              <UnscheduledChip key={occurrence.key} occurrence={occurrence} onOpen={onOpenOccurrence} />
            ))}
          </div>
        ))}
      </div>

      <div className="calendar-grid-scroll overflow-x-auto">
        <div className="relative grid min-w-[780px] grid-cols-[52px_repeat(7,minmax(104px,1fr))]" style={{ height }}>
          <div className="relative border-r border-[var(--ui-border-subtle)]">
            {hours.map((hour) => (
              <div
                className="absolute right-1.5 -translate-y-1.5 text-[10px] tabular-nums text-[var(--ui-text-subtle)]"
                key={hour}
                style={{ top: (hour - bounds.from) * HOUR_HEIGHT }}
              >
                {`${String(hour % 24).padStart(2, '0')}:00`}
              </div>
            ))}
          </div>
          {days.map((day) => (
            <div className="relative border-l border-[var(--ui-border-subtle)]" key={dateKey(day)}>
              {hours.map((hour) => (
                <div
                  className="absolute inset-x-0 border-t border-[var(--ui-border-subtle)]"
                  key={hour}
                  style={{ top: (hour - bounds.from) * HOUR_HEIGHT }}
                />
              ))}
              {isSameDay(day, today) ? <NowIndicator bounds={bounds} /> : null}
              {layoutOccurrences(daysMap.get(dateKey(day))?.timed ?? []).map((positioned) => {
                const { occurrence } = positioned;
                if (occurrence.startMinutes === null) return null;
                const offsetMinutes = positioned.startMinutes - bounds.from * 60;
                const width = 100 / positioned.laneCount;
                return (
                  <button
                    className="calendar-bar absolute z-10 overflow-hidden rounded-[4px] px-1.5 py-1 text-left text-[11px] leading-tight shadow-[var(--ui-shadow-control)] transition-transform hover:z-30 hover:brightness-110"
                    data-cal-source={occurrence.entry.sources[0]?.provider ?? 'unknown'}
                    key={occurrence.key}
                    onClick={() => {
                      onOpenOccurrence(occurrence);
                    }}
                    style={{
                      top: offsetMinutes * (HOUR_HEIGHT / 60),
                      height: Math.max(22, positioned.durationMinutes * (HOUR_HEIGHT / 60)),
                      left: `calc(${positioned.lane * width}% + 3px)`,
                      width: `calc(${width}% - 6px)`,
                    }}
                    type="button"
                  >
                    <span className="block truncate font-medium">{titleOf(occurrence)}</span>
                    <span className="block truncate tabular-nums opacity-90">
                      {formatTime(occurrence.startMinutes, locale)}
                    </span>
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </Panel>
  );
}

function NowIndicator({ bounds }: { bounds: { from: number; to: number } }) {
  const offset = nowMinutes() - bounds.from * 60;
  return (
    <div className="absolute inset-x-0 z-20" style={{ top: offset * (HOUR_HEIGHT / 60) }}>
      <div className="relative border-t border-rose-500">
        <span className="absolute -left-1 -top-[4px] size-2 rounded-full bg-rose-500" />
      </div>
    </div>
  );
}

function UnscheduledChip({
  occurrence,
  onOpen,
}: {
  occurrence: CalendarOccurrence;
  onOpen: (occurrence: CalendarOccurrence) => void;
}) {
  return (
    <button
      className="calendar-tint w-full truncate rounded-[4px] px-1.5 py-[2px] text-left text-[10px] font-medium"
      data-cal-source={occurrence.entry.sources[0]?.provider ?? 'unknown'}
      onClick={() => {
        onOpen(occurrence);
      }}
      type="button"
    >
      {titleOf(occurrence)}
    </button>
  );
}
