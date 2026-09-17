import { placeholderImagePaths } from '@/shared/assets/public-assets';
import { Link } from '@tanstack/react-router';
import { X } from 'lucide-react';
import type { Locale } from '@/shared/i18n';
import type { RouteBackState } from '@/shared/routing/route-state';
import { routes } from '@/shared/routing/paths';
import {
  dateKey,
  formatDayTitle,
  formatTime,
  formatWeekday,
  titleOf,
  type CalendarDay,
  type CalendarOccurrence,
} from './calendar-model';

const coverPlaceholder = placeholderImagePaths.subjectCover;

const providerStyles: Record<string, string> = {
  anilist: 'border-indigo-400/50 bg-indigo-400/15 text-indigo-200',
  mal: 'border-emerald-400/50 bg-emerald-400/15 text-emerald-200',
  bangumi: 'border-amber-400/50 bg-amber-400/15 text-amber-200',
};

function providerClass(occurrence: CalendarOccurrence): string {
  const provider = occurrence.entry.sources[0]?.provider ?? '';
  return providerStyles[provider] ?? 'border-[var(--ui-border-strong)] bg-[var(--ui-bg-surface)] text-[var(--ui-text)]';
}

function isSameDay(left: Date, right: Date): boolean {
  return dateKey(left) === dateKey(right);
}

function dayOccurrences(day: CalendarDay | undefined): CalendarOccurrence[] {
  if (!day) return [];
  return [...day.timed, ...day.tentative];
}

export function CalendarEventChip({
  occurrence,
  locale,
  onOpen,
}: {
  occurrence: CalendarOccurrence;
  locale: Locale;
  onOpen: (occurrence: CalendarOccurrence) => void;
}) {
  const time = formatTime(occurrence.startsAt, locale);
  return (
    <button
      className={[
        'flex w-full min-w-0 items-center gap-1 rounded-md border px-1.5 py-0.5 text-left text-[11px] leading-4',
        occurrence.tentative ? 'border-dashed opacity-80' : '',
        providerClass(occurrence),
      ].join(' ')}
      onClick={(event) => {
        event.stopPropagation();
        onOpen(occurrence);
      }}
      type="button"
    >
      {time ? <span className="shrink-0 font-medium tabular-nums">{time}</span> : null}
      <span className="truncate">{titleOf(occurrence)}</span>
    </button>
  );
}

export function MonthView({
  month,
  days,
  daysMap,
  locale,
  onSelectDate,
  onOpenOccurrence,
}: {
  month: Date;
  days: Date[];
  daysMap: Map<string, CalendarDay>;
  locale: Locale;
  onSelectDate: (date: Date) => void;
  onOpenOccurrence: (occurrence: CalendarOccurrence) => void;
}) {
  const today = new Date();
  return (
    <div className="overflow-hidden rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-bg-inset)]">
      <div className="grid grid-cols-7 border-b border-[var(--ui-border-subtle)] bg-[var(--ui-bg-surface)]">
        {days.slice(0, 7).map((day) => (
          <div
            className="px-2 py-2 text-center text-[11px] font-medium text-[var(--ui-text-muted)]"
            key={day.toISOString()}
          >
            {formatWeekday(day, locale)}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-7">
        {days.map((day) => {
          const dayData = daysMap.get(dateKey(day));
          const items = dayOccurrences(dayData);
          const outsideMonth = day.getMonth() !== month.getMonth();
          return (
            <button
              className={[
                'min-h-[92px] min-w-0 border-b border-r border-[var(--ui-border-subtle)] p-1 text-left transition-colors hover:bg-[var(--ui-bg-surface)]',
                outsideMonth ? 'opacity-45' : '',
              ].join(' ')}
              key={dateKey(day)}
              onClick={() => {
                onSelectDate(day);
              }}
              type="button"
            >
              <span
                className={[
                  'mb-1 inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1 text-[11px] tabular-nums',
                  isSameDay(day, today)
                    ? 'bg-[var(--ui-accent)] font-semibold text-[var(--ui-accent-contrast)]'
                    : 'text-[var(--ui-text-muted)]',
                ].join(' ')}
              >
                {day.getDate()}
              </span>
              <span className="grid gap-0.5">
                {items.slice(0, 2).map((occurrence) => (
                  <CalendarEventChip
                    key={occurrence.key}
                    locale={locale}
                    occurrence={occurrence}
                    onOpen={onOpenOccurrence}
                  />
                ))}
                {items.length > 2 ? (
                  <span className="px-1 text-[10px] font-medium text-[var(--ui-text-muted)]">+{items.length - 2}</span>
                ) : null}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function WeekView({
  days,
  daysMap,
  locale,
  onOpenOccurrence,
}: {
  days: Date[];
  daysMap: Map<string, CalendarDay>;
  locale: Locale;
  onOpenOccurrence: (occurrence: CalendarOccurrence) => void;
}) {
  const timed = days.flatMap((day) => daysMap.get(dateKey(day))?.timed ?? []);
  const hours = timed.flatMap((occurrence) => (occurrence.startsAt ? [occurrence.startsAt.getHours()] : []));
  const minHour = Math.max(0, Math.min(18, ...hours) - 1);
  const maxHour = Math.min(29, Math.max(24, ...hours.map((hour) => hour + 1)));
  const hourHeight = 64;
  const totalHeight = (maxHour - minHour) * hourHeight;
  const hoursList = Array.from({ length: maxHour - minHour }, (_, index) => minHour + index);
  const today = new Date();
  const now = new Date();

  return (
    <div className="overflow-hidden rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-bg-inset)]">
      <div className="grid grid-cols-[56px_repeat(7,minmax(112px,1fr))] border-b border-[var(--ui-border-subtle)] bg-[var(--ui-bg-surface)]">
        <div />
        {days.map((day) => (
          <div
            className={[
              'border-l border-[var(--ui-border-subtle)] px-2 py-2 text-center text-xs',
              isSameDay(day, today) ? 'font-semibold text-[var(--ui-accent-text)]' : 'text-[var(--ui-text-muted)]',
            ].join(' ')}
            key={dateKey(day)}
          >
            <div>{formatWeekday(day, locale)}</div>
            <div className="text-[11px] tabular-nums">{day.getDate()}</div>
          </div>
        ))}
      </div>
      <div className="overflow-x-auto">
        <div
          className="relative grid min-w-[840px] grid-cols-[56px_repeat(7,minmax(112px,1fr))]"
          style={{ height: totalHeight }}
        >
          <div className="relative border-r border-[var(--ui-border-subtle)]">
            {hoursList.map((hour) => (
              <div
                className="absolute right-1 -translate-y-2 text-[10px] tabular-nums text-[var(--ui-text-muted)]"
                key={hour}
                style={{ top: (hour - minHour) * hourHeight }}
              >
                {`${`${hour % 24}`.padStart(2, '0')}:00`}
              </div>
            ))}
          </div>
          {days.map((day) => {
            const dayData = daysMap.get(dateKey(day));
            return (
              <div className="relative border-l border-[var(--ui-border-subtle)]" key={dateKey(day)}>
                {hoursList.map((hour) => (
                  <div
                    className="absolute inset-x-0 border-t border-[var(--ui-border-subtle)]"
                    key={hour}
                    style={{ top: (hour - minHour) * hourHeight }}
                  />
                ))}
                {isSameDay(day, today) ? (
                  <div
                    className="absolute inset-x-0 z-20 border-t border-rose-400"
                    style={{ top: ((now.getHours() - minHour) * 60 + now.getMinutes()) * (hourHeight / 60) }}
                  />
                ) : null}
                {(dayData?.timed ?? []).map((occurrence) => {
                  if (!occurrence.startsAt) return null;
                  const startMinutes =
                    (occurrence.startsAt.getHours() - minHour) * 60 + occurrence.startsAt.getMinutes();
                  const duration = Math.max(
                    30,
                    occurrence.endsAt
                      ? (occurrence.endsAt.getTime() - occurrence.startsAt.getTime()) / 60_000
                      : (occurrence.entry.durationMinutes ?? 24),
                  );
                  return (
                    <button
                      className={[
                        'absolute inset-x-1 z-10 overflow-hidden rounded-md border px-2 py-1 text-left text-[11px] shadow-sm transition-transform hover:z-30 hover:scale-[1.02]',
                        providerClass(occurrence),
                      ].join(' ')}
                      key={occurrence.key}
                      onClick={() => {
                        onOpenOccurrence(occurrence);
                      }}
                      style={{
                        top: startMinutes * (hourHeight / 60),
                        height: Math.max(30, duration * (hourHeight / 60)),
                      }}
                      type="button"
                    >
                      <div className="truncate font-medium">{titleOf(occurrence)}</div>
                      <div className="truncate opacity-80">
                        {formatTime(occurrence.startsAt, locale)}
                        {occurrence.entry.episodeNumber ? ` · EP${occurrence.entry.episodeNumber}` : ''}
                      </div>
                    </button>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>
      <div className="border-t border-[var(--ui-border-subtle)] p-2">
        <div className="mb-1 px-1 text-[10px] font-medium uppercase tracking-wide text-[var(--ui-text-muted)]">TBD</div>
        <div className="grid grid-cols-7 gap-1">
          {days.map((day) => (
            <div className="grid min-h-6 gap-1" key={dateKey(day)}>
              {(daysMap.get(dateKey(day))?.tentative ?? []).slice(0, 3).map((occurrence) => (
                <CalendarEventChip
                  key={occurrence.key}
                  locale={locale}
                  occurrence={occurrence}
                  onOpen={onOpenOccurrence}
                />
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function DayView({
  date,
  day,
  locale,
  onOpenOccurrence,
}: {
  date: Date;
  day: CalendarDay | undefined;
  locale: Locale;
  onOpenOccurrence: (occurrence: CalendarOccurrence) => void;
}) {
  const timed = day?.timed ?? [];
  const tentative = day?.tentative ?? [];
  return (
    <div className="grid gap-3">
      <h2 className="px-1 text-sm font-semibold text-[var(--ui-text)]">{formatDayTitle(date, locale)}</h2>
      {timed.length === 0 && tentative.length === 0 ? (
        <div className="grid min-h-40 place-items-center rounded-2xl border border-dashed border-[var(--ui-border)] text-sm text-[var(--ui-text-muted)]">
          —
        </div>
      ) : null}
      {timed.map((occurrence) => (
        <OccurrenceCard key={occurrence.key} locale={locale} occurrence={occurrence} onOpen={onOpenOccurrence} />
      ))}
      {tentative.length > 0 ? (
        <div className="grid gap-2">
          <div className="px-1 text-[11px] font-medium uppercase tracking-wide text-[var(--ui-text-muted)]">TBD</div>
          {tentative.map((occurrence) => (
            <OccurrenceCard key={occurrence.key} locale={locale} occurrence={occurrence} onOpen={onOpenOccurrence} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function OccurrenceCard({
  occurrence,
  locale,
  onOpen,
}: {
  occurrence: CalendarOccurrence;
  locale: Locale;
  onOpen: (occurrence: CalendarOccurrence) => void;
}) {
  return (
    <button
      className="grid grid-cols-[56px_minmax(0,1fr)_auto] items-center gap-3 rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-bg-surface)] p-3 text-left"
      onClick={() => {
        onOpen(occurrence);
      }}
      type="button"
    >
      <span className="text-sm font-semibold tabular-nums text-[var(--ui-text)]">
        {formatTime(occurrence.startsAt, locale) || '—'}
      </span>
      <span className="min-w-0">
        <span className="line-clamp-1 text-sm font-semibold text-[var(--ui-text)]">{titleOf(occurrence)}</span>
        <span className="line-clamp-1 text-xs text-[var(--ui-text-muted)]">
          {occurrence.entry.sources.map((source) => source.provider).join(' · ')}
        </span>
      </span>
      {occurrence.entry.episodeNumber ? (
        <span className="text-xs font-medium tabular-nums text-[var(--ui-text-muted)]">
          EP{occurrence.entry.episodeNumber}
        </span>
      ) : null}
    </button>
  );
}

export function CalendarEventDetails({
  occurrence,
  locale,
  state,
  onClose,
}: {
  occurrence: CalendarOccurrence;
  locale: Locale;
  state: RouteBackState;
  onClose: () => void;
}) {
  const entry = occurrence.entry;
  const work = entry.work;
  return (
    <div
      className="fixed inset-0 z-50 flex items-end bg-black/40 p-0 sm:items-center sm:justify-center sm:p-4"
      role="presentation"
    >
      <div className="max-h-[85vh] w-full overflow-y-auto rounded-t-3xl border border-[var(--ui-border)] bg-[var(--ui-bg-surface)] p-4 sm:max-w-md sm:rounded-3xl">
        <div className="mb-3 flex items-center justify-between gap-3">
          <span className="text-sm font-semibold text-[var(--ui-text)]">{formatDayTitle(occurrence.date, locale)}</span>
          <button
            aria-label="Close"
            className="grid h-8 w-8 place-items-center rounded-full border border-[var(--ui-border)] text-[var(--ui-text-muted)]"
            onClick={onClose}
            type="button"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        {work ? (
          <Link className="mb-4 grid grid-cols-[72px_minmax(0,1fr)] gap-3" state={state} to={routes.entity(work.id)}>
            <img
              alt={work.displayName}
              className="h-24 w-[72px] rounded-xl bg-[var(--ui-bg-subtle)] object-cover"
              referrerPolicy="no-referrer"
              src={work.cover || coverPlaceholder}
            />
            <span className="grid content-center gap-1">
              <span className="line-clamp-2 text-base font-semibold text-[var(--ui-text)]">{work.displayName}</span>
              <span className="text-xs text-[var(--ui-text-muted)]">
                {work.workType ?? ''} {entry.episodeNumber ? `· EP${entry.episodeNumber}` : ''}
              </span>
            </span>
          </Link>
        ) : null}
        <dl className="grid gap-2 text-sm">
          <div className="flex items-center justify-between gap-3">
            <dt className="text-[var(--ui-text-muted)]">Time</dt>
            <dd className="font-medium tabular-nums text-[var(--ui-text)]">
              {formatTime(occurrence.startsAt, locale) || 'TBD'}
              {occurrence.endsAt ? ` – ${formatTime(occurrence.endsAt, locale)}` : ''}
            </dd>
          </div>
          <div className="flex items-center justify-between gap-3">
            <dt className="text-[var(--ui-text-muted)]">Status</dt>
            <dd className="font-medium text-[var(--ui-text)]">{entry.status}</dd>
          </div>
          <div className="flex items-center justify-between gap-3">
            <dt className="text-[var(--ui-text-muted)]">Decision</dt>
            <dd className="font-medium text-[var(--ui-text)]">{entry.decision || '—'}</dd>
          </div>
        </dl>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {entry.sources.map((source) => (
            <span
              className="rounded-full border border-[var(--ui-border)] px-2 py-0.5 text-[11px] text-[var(--ui-text-muted)]"
              key={`${source.provider}:${source.external_id}`}
            >
              {source.provider} · {source.role || source.precision}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
