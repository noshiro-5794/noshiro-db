import { useMemo } from 'react';
import { useI18n } from '@/shared/i18n';
import { cn } from '@/shared/lib/cn';
import {
  AIRING_TIME_ZONE_LABEL,
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

const HOUR_HEIGHT = 56;
const MIN_VISIBLE_HOUR = 18;
const MAX_VISIBLE_HOUR = 29;
const GUTTER = '52px';

/**
 * Notion Calendar's time surface, used for both the week and the day view.
 *
 * The grid is almost colourless: hairline separators, a muted hour gutter and
 * one accent reserved for the live time line. Works are drawn as soft tinted
 * blocks with a spine, so the day reads as a list of air times rather than a
 * wall of saturated colour.
 */
export function TimeGrid({
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
  const gridTemplate = `${GUTTER} repeat(${days.length}, minmax(0, 1fr))`;

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
  const nowOffset = nowMinutes() - bounds.from * 60;
  const hasToday = days.some((day) => isSameDay(day, today));
  const minWidth = days.length > 1 ? 700 + days.length * 40 : undefined;

  return (
    <div className="overflow-hidden rounded-[var(--ui-radius-frame)] border border-[var(--cal-hairline)] bg-[var(--ui-bg-surface)]">
      <div className="grid border-b border-[var(--cal-hairline)]" style={{ gridTemplateColumns: gridTemplate }}>
        <div className="px-2 py-2 text-[11px] font-medium text-[var(--cal-muted)]">{AIRING_TIME_ZONE_LABEL}</div>
        {days.map((day) => (
          <div
            className="border-l border-[var(--cal-hairline)] px-2 py-2 text-center text-[13px] font-medium text-[var(--ui-text-muted)]"
            key={dateKey(day)}
          >
            <span className="inline-flex items-center gap-1.5">
              {formatWeekday(day, locale)}
              <span
                className={cn(
                  'inline-grid h-6 min-w-6 place-items-center rounded-[6px] px-1.5 tabular-nums',
                  isSameDay(day, today) ? 'calendar-today font-semibold' : 'text-[var(--ui-text)]',
                )}
              >
                {day.getDate()}
              </span>
            </span>
          </div>
        ))}
      </div>

      <div
        className="grid border-b border-[var(--cal-hairline)] bg-[var(--ui-bg-surface)]"
        style={{ gridTemplateColumns: gridTemplate }}
      >
        <div className="px-2 py-2 text-right text-[11px] text-[var(--cal-muted)]">{t('calendar.unscheduled')}</div>
        {days.map((day) => (
          <div
            className="grid min-h-[32px] gap-[3px] border-l border-[var(--cal-hairline)] px-1 py-1"
            key={dateKey(day)}
          >
            {(daysMap.get(dateKey(day))?.tentative ?? []).slice(0, 3).map((occurrence) => (
              <button
                className="calendar-bar w-full truncate rounded-[6px] py-[2px] pl-1.5 pr-2 text-left text-[11px] font-medium"
                data-cal-source={occurrence.entry.sources[0]?.provider ?? 'unknown'}
                key={occurrence.key}
                onClick={() => {
                  onOpenOccurrence(occurrence);
                }}
                type="button"
              >
                {titleOf(occurrence)}
              </button>
            ))}
          </div>
        ))}
      </div>

      <div className="calendar-grid-scroll overflow-x-auto">
        <div className="relative grid" style={{ gridTemplateColumns: gridTemplate, height, minWidth }}>
          <div className="relative border-r border-[var(--cal-hairline)]">
            {hours.map((hour) => (
              <div
                className="absolute right-2 -translate-y-1/2 text-[11px] tabular-nums text-[var(--cal-muted)]"
                key={hour}
                style={{ top: (hour - bounds.from) * HOUR_HEIGHT }}
              >
                {`${String(hour % 24).padStart(2, '0')}:00`}
              </div>
            ))}
            {hasToday ? (
              <span
                className="calendar-now-label absolute right-1 -translate-y-1/2"
                style={{ top: nowOffset * (HOUR_HEIGHT / 60) }}
              >
                {formatTime(nowMinutes(), locale)}
              </span>
            ) : null}
          </div>

          {days.map((day) => (
            <div className="relative border-l border-[var(--cal-hairline)]" key={dateKey(day)}>
              {hours.map((hour) => (
                <div
                  className="absolute inset-x-0 border-t border-[var(--cal-hairline)]"
                  key={hour}
                  style={{ top: (hour - bounds.from) * HOUR_HEIGHT }}
                />
              ))}
              {isSameDay(day, today) ? (
                <div
                  className="calendar-now-line absolute inset-x-0 z-20"
                  style={{ top: nowOffset * (HOUR_HEIGHT / 60) }}
                />
              ) : null}
              {layoutOccurrences(daysMap.get(dateKey(day))?.timed ?? []).map((positioned) => {
                const { occurrence } = positioned;
                if (occurrence.startMinutes === null) return null;
                const offsetMinutes = positioned.startMinutes - bounds.from * 60;
                const width = 100 / positioned.laneCount;
                return (
                  <button
                    className="calendar-bar absolute z-10 overflow-hidden rounded-[6px] py-1 pl-1.5 pr-2 text-left text-[11px] leading-tight transition-[filter] hover:brightness-[1.04]"
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
                    <span className="block truncate tabular-nums opacity-80">
                      {formatTime(occurrence.startMinutes, locale)}
                    </span>
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
