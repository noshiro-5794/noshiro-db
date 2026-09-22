import { Link } from '@tanstack/react-router';
import { useI18n } from '@/shared/i18n';
import { placeholderImagePaths } from '@/shared/assets/public-assets';
import { cn } from '@/shared/lib/cn';
import { routes } from '@/shared/routing/paths';
import type { RouteBackState } from '@/shared/routing/route-state';
import type { CalendarBoardEntry } from '@/shared/api';
import {
  formatAiringDate,
  formatMinutesOfDay,
  groupEntriesByWeekday,
  providerOf,
  startMinutesOf,
  sourceLabel,
  titleOfEntry,
  weekdayName,
} from '../calendar-model';
import { SourceDot } from './primitives';

const coverPlaceholder = placeholderImagePaths.subjectCover;

/**
 * AniChart-style broadcast board: one column per weekday, each holding dense
 * cards with artwork, airtime and provenance, plus a hover panel that exposes
 * the curation facts the bar itself has no room for.
 */
export function BroadcastBoard({
  emptyLabel,
  entries,
  onOpen,
  state,
}: {
  emptyLabel: string;
  entries: CalendarBoardEntry[];
  onOpen: (entry: CalendarBoardEntry) => void;
  state: RouteBackState;
}) {
  const { locale, t } = useI18n();
  const buckets = groupEntriesByWeekday(entries);
  const weekdays = buckets.filter((bucket) => bucket.weekday !== null);
  const extras = buckets.find((bucket) => bucket.weekday === null)?.entries ?? [];

  if (weekdays.length === 0 && extras.length === 0) {
    return (
      <div className="grid min-h-48 place-items-center rounded-[var(--ui-radius-frame)] border border-dashed border-[var(--ui-border)] text-sm text-[var(--ui-text-muted)]">
        {emptyLabel}
      </div>
    );
  }

  return (
    <div className="grid gap-4">
      <div className="calendar-grid-scroll overflow-x-auto pb-1">
        <div className="grid grid-cols-1 gap-2.5 md:min-w-[1000px] md:grid-cols-7">
          {weekdays.map((bucket) => (
            <section className="grid content-start gap-2" key={bucket.weekday}>
              <header className="flex items-center justify-between gap-2 border-b border-[var(--ui-border-subtle)] pb-1.5">
                <span className="flex items-center gap-1.5 text-xs font-semibold text-[var(--ui-text)]">
                  {weekdayName(locale, bucket.weekday ?? 1)}
                </span>
                <span className="text-[11px] tabular-nums text-[var(--ui-text-subtle)]">{bucket.entries.length}</span>
              </header>
              {bucket.entries.map((entry) => (
                <BroadcastCard entry={entry} key={entry.id} onOpen={onOpen} state={state} />
              ))}
            </section>
          ))}
        </div>
      </div>

      {extras.length > 0 ? (
        <section className="grid gap-2 border-t border-[var(--ui-border-subtle)] pt-3">
          <header className="flex items-baseline gap-2">
            <h3 className="text-xs font-semibold text-[var(--ui-text)]">{t('calendar.filmsAndSpecials')}</h3>
            <span className="text-[11px] tabular-nums text-[var(--ui-text-subtle)]">{extras.length}</span>
          </header>
          <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
            {extras.map((entry) => (
              <BroadcastCard entry={entry} key={entry.id} onOpen={onOpen} state={state} />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}

function BroadcastCard({
  entry,
  onOpen,
  state,
}: {
  entry: CalendarBoardEntry;
  onOpen: (entry: CalendarBoardEntry) => void;
  state: RouteBackState;
}) {
  const { locale, t } = useI18n();
  const work = entry.work;
  const title = titleOfEntry(entry);
  const provider = providerOf(entry);
  const minutes = startMinutesOf(entry);
  const isDateOnly = entry.precision === 'day';
  const dateLabel = formatAiringDate(entry.startsAt, locale);
  const time = isDateOnly
    ? dateLabel || t('calendar.unscheduled')
    : minutes === null
      ? t('calendar.unscheduled')
      : formatMinutesOfDay(minutes, locale);
  const status = entry.status === 'scheduled' ? t('calendar.statusScheduled') : t('calendar.statusTentative');
  const precision = entry.precision === 'minute' ? t('calendar.precisionMinute') : t('calendar.precisionWeekday');

  return (
    <div className="group/card relative" data-cal-source={provider}>
      <Link
        className={cn(
          'grid grid-cols-[42px_minmax(0,1fr)] gap-2 rounded-[var(--ui-radius-surface)] border border-[var(--ui-border)] bg-[var(--ui-bg-surface)] p-1.5 transition-colors',
          'hover:border-[var(--ui-border-strong)] hover:bg-[var(--ui-bg-elevated)]',
        )}
        state={state}
        to={routes.entity(entry.workId)}
      >
        <img
          alt=""
          className="h-[58px] w-[42px] rounded-[5px] bg-[var(--ui-bg-subtle)] object-cover"
          decoding="async"
          loading="lazy"
          referrerPolicy="no-referrer"
          src={work?.cover || coverPlaceholder}
        />
        <span className="grid min-w-0 content-center gap-1">
          <span className="line-clamp-2 text-[12px] font-semibold leading-[15px] text-[var(--ui-text)]">{title}</span>
          <span className="flex min-w-0 items-center gap-1.5 text-[10px] text-[var(--ui-text-muted)]">
            <span className="calendar-tint shrink-0 rounded-[4px] px-1 py-[1px] font-medium tabular-nums">{time}</span>
            {isDateOnly && entry.format ? (
              <span className="shrink-0 rounded-[4px] border border-[var(--ui-border)] px-1 py-[1px] font-medium uppercase">
                {entry.format}
              </span>
            ) : null}
            {entry.episodeNumber === null ? null : (
              <span className="shrink-0 tabular-nums">EP{entry.episodeNumber}</span>
            )}
            <span className="flex min-w-0 items-center gap-1 truncate">
              <SourceDot className="size-1.5" provider={provider} />
              <span className="truncate">{sourceLabel(provider)}</span>
            </span>
          </span>
        </span>
      </Link>

      <div className="absolute left-0 top-full z-30 hidden w-60 pt-1 group-hover/card:block group-focus-within/card:block">
        <div className="rounded-[var(--ui-radius-surface)] border border-[var(--ui-border)] bg-[var(--ui-bg-elevated)] p-2.5 text-[11px] shadow-[var(--ui-shadow-popup)]">
          <p className="mb-1.5 font-semibold text-[var(--ui-text)]">{title}</p>
          <dl className="grid gap-1 text-[var(--ui-text-muted)]">
            <Row label={t('calendar.detailTime')} value={`${time} · ${precision}`} />
            <Row label={t('calendar.detailStatus')} value={`${status} · ${Math.round(entry.confidence * 100)}%`} />
            <Row
              label={t('calendar.detailSources')}
              value={entry.sources.map((source) => sourceLabel(source.provider)).join(' · ') || '—'}
            />
          </dl>
          <button
            className="mt-2 w-full rounded-[4px] border border-[var(--ui-border)] px-2 py-1 text-[11px] font-medium text-[var(--ui-text-muted)] transition-colors hover:text-[var(--ui-text)]"
            onClick={() => {
              onOpen(entry);
            }}
            type="button"
          >
            {t('calendar.detailTitle')}
          </button>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-2">
      <dt className="shrink-0">{label}</dt>
      <dd className="min-w-0 truncate text-right text-[var(--ui-text)]">{value}</dd>
    </div>
  );
}
