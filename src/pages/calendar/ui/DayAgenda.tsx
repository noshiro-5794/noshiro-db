import { useI18n } from '@/shared/i18n';
import { cn } from '@/shared/lib/cn';
import {
  formatDayTitle,
  formatTime,
  sourceLabel,
  titleOf,
  type CalendarDay,
  type CalendarOccurrence,
} from '../calendar-model';
import { Panel, SourceDot } from './primitives';

/**
 * Google Calendar "day" reading: a single-column agenda that keeps the airing
 * time anchored on the left and the work on the right.
 */
export function DayAgenda({
  date,
  day,
  onOpenOccurrence,
}: {
  date: Date;
  day: CalendarDay | undefined;
  onOpenOccurrence: (occurrence: CalendarOccurrence) => void;
}) {
  const { locale, t } = useI18n();
  const entries = [...(day?.timed ?? []), ...(day?.tentative ?? [])];
  return (
    <Panel>
      <div className="flex items-center justify-between gap-2 border-b border-[var(--ui-border-subtle)] px-4 py-3">
        <span className="text-sm font-semibold text-[var(--ui-text)]">{formatDayTitle(date, locale)}</span>
        <span className="text-xs tabular-nums text-[var(--ui-text-muted)]">{entries.length}</span>
      </div>
      {entries.length === 0 ? (
        <div className="grid min-h-32 place-items-center text-sm text-[var(--ui-text-muted)]">—</div>
      ) : (
        <ul className="divide-y divide-[var(--ui-border-subtle)]">
          {entries.map((occurrence) => (
            <li key={occurrence.key}>
              <button
                className="grid w-full grid-cols-[64px_minmax(0,1fr)_auto] items-center gap-3 px-4 py-2.5 text-left transition-colors hover:bg-[var(--ui-bg-inset)]"
                onClick={() => {
                  onOpenOccurrence(occurrence);
                }}
                type="button"
              >
                <span
                  className={cn(
                    'text-xs font-semibold tabular-nums',
                    occurrence.tentative ? 'text-[var(--ui-text-subtle)]' : 'text-[var(--ui-text)]',
                  )}
                >
                  {formatTime(occurrence.startMinutes, locale) || t('calendar.unscheduled')}
                </span>
                <span className="min-w-0">
                  <span className="line-clamp-1 text-sm font-medium text-[var(--ui-text)]">{titleOf(occurrence)}</span>
                  <span className="mt-0.5 flex items-center gap-1.5 text-[11px] text-[var(--ui-text-muted)]">
                    {occurrence.entry.sources.slice(0, 3).map((source) => (
                      <span className="inline-flex items-center gap-1" key={`${source.provider}:${source.external_id}`}>
                        <SourceDot className="size-1.5" provider={source.provider} />
                        {sourceLabel(source.provider)}
                      </span>
                    ))}
                    {occurrence.entry.episodeNumber === null ? null : (
                      <span className="tabular-nums">EP{occurrence.entry.episodeNumber}</span>
                    )}
                  </span>
                </span>
                <span
                  className="calendar-dot hidden size-2.5 rounded-full sm:block"
                  data-cal-source={occurrence.entry.sources[0]?.provider ?? 'unknown'}
                />
              </button>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
