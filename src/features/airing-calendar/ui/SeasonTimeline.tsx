import { useMemo } from 'react';
import { Link } from '@tanstack/react-router';
import { useI18n } from '@/shared/i18n';
import { placeholderImagePaths } from '@/shared/assets/public-assets';
import { routes } from '@/shared/routing/paths';
import type { RouteBackState } from '@/shared/routing/route-state';
import type { CalendarBoardEntry } from '@/shared/api';
import {
  AIRING_TIME_ZONE_LABEL,
  boardWindow,
  formatAiringDate,
  providerOf,
  seasonBars,
  sourceLabel,
  titleOfEntry,
} from '../model/calendar-model';

const coverPlaceholder = placeholderImagePaths.subjectCover;
const DAY = 86_400_000;

/**
 * Season timeline.
 *
 * Linear's roadmap bars, applied to a broadcast quarter: the x-axis is the
 * board window, one row per work, and a bar spanning premiere to finale. It
 * answers "what is running which weeks" — something neither a month grid nor a
 * per-weekday board shows, because both repeat a weekly slot instead of a run.
 */
export function SeasonTimeline({ entries, state }: { entries: CalendarBoardEntry[]; state: RouteBackState }) {
  const { locale, t } = useI18n();
  const window = useMemo(() => boardWindow(entries[0]), [entries]);
  const bars = useMemo(() => seasonBars(entries, window), [entries, window]);

  const months = useMemo(() => {
    if (!window) return [];
    const total = window.to.getTime() - window.from.getTime() + DAY;
    const result: { key: string; label: string; left: number; width: number }[] = [];
    for (
      let cursor = new Date(window.from.getFullYear(), window.from.getMonth(), 1);
      cursor <= window.to;
      cursor = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1)
    ) {
      const start = Math.max(cursor.getTime(), window.from.getTime());
      const next = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1);
      const end = Math.min(next.getTime(), window.to.getTime() + DAY);
      result.push({
        key: `${cursor.getFullYear()}-${cursor.getMonth()}`,
        label: new Intl.DateTimeFormat(locale, { month: 'long' }).format(cursor),
        left: ((start - window.from.getTime()) / total) * 100,
        width: ((end - start) / total) * 100,
      });
    }
    return result;
  }, [locale, window]);

  if (!window || bars.length === 0) {
    return (
      <div className="grid min-h-48 place-items-center rounded-[var(--ui-radius-frame)] border border-dashed border-[var(--ui-border)] text-sm text-[var(--ui-text-muted)]">
        {t('calendar.empty')}
      </div>
    );
  }

  const total = window.to.getTime() - window.from.getTime() + DAY;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const todayOffset = ((today.getTime() - window.from.getTime()) / total) * 100;
  const showToday = todayOffset >= 0 && todayOffset <= 100;

  return (
    <div className="overflow-hidden rounded-[var(--ui-radius-frame)] border border-[var(--ui-border)] bg-[var(--ui-bg-surface)]">
      <div className="grid grid-cols-[220px_minmax(0,1fr)] border-b border-[var(--cal-hairline)]">
        <div className="px-4 py-2.5 text-[12px] text-[var(--cal-muted)]">
          {`${bars.length} ${t('calendar.itemsUnit')}`}
        </div>
        <div className="relative px-4 py-2.5">
          {months.map((month) => (
            <span
              className="absolute text-[12px] font-medium text-[var(--ui-text-muted)]"
              key={month.key}
              style={{ left: `${month.left}%`, width: `${month.width}%` }}
            >
              {month.label}
            </span>
          ))}
        </div>
      </div>

      <div className="relative max-h-[68vh] overflow-y-auto">
        {showToday ? (
          <div
            className="calendar-now-line pointer-events-none absolute bottom-0 top-0 z-10"
            style={{ left: `calc(220px + ${todayOffset}% * ((100% - 220px) / 100%))` }}
          />
        ) : null}
        <ul className="divide-y divide-[var(--cal-hairline)]">
          {bars.map((bar) => {
            const left = ((bar.from.getTime() - window.from.getTime()) / total) * 100;
            const width = ((bar.to.getTime() - bar.from.getTime() + DAY) / total) * 100;
            const provider = providerOf(bar.entry);
            const work = bar.entry.work;
            return (
              <li className="grid grid-cols-[220px_minmax(0,1fr)] items-center" key={bar.entry.id}>
                <Link
                  className="flex min-w-0 items-center gap-2 px-3 py-1.5 transition-colors hover:bg-[var(--ui-bg-inset)]"
                  state={state}
                  to={routes.entity(bar.entry.workId)}
                >
                  <img
                    alt=""
                    className="h-8 w-6 shrink-0 rounded-[4px] bg-[var(--ui-bg-subtle)] object-cover"
                    decoding="async"
                    loading="lazy"
                    referrerPolicy="no-referrer"
                    src={work?.cover || coverPlaceholder}
                  />
                  <span className="min-w-0">
                    <span className="line-clamp-1 text-[12px] font-medium text-[var(--ui-text)]">
                      {titleOfEntry(bar.entry)}
                    </span>
                    <span className="line-clamp-1 text-[10px] text-[var(--ui-text-muted)]">
                      {`${sourceLabel(provider)} · ${formatAiringDate(bar.from.toISOString(), locale)}`}
                    </span>
                  </span>
                </Link>
                <div className="relative h-9">
                  <div
                    className="calendar-bar absolute top-1/2 h-[18px] -translate-y-1/2 rounded-[4px] px-1.5 text-[10px] leading-[18px]"
                    data-cal-source={provider}
                    style={{ left: `${left}%`, width: `max(${width}%, 8px)` }}
                    title={`${titleOfEntry(bar.entry)} · ${formatAiringDate(bar.from.toISOString(), locale)} – ${formatAiringDate(bar.to.toISOString(), locale)} (${AIRING_TIME_ZONE_LABEL})`}
                  >
                    <span className="block truncate">{bar.entry.episodeCount ? `${bar.entry.episodeCount}` : ''}</span>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
