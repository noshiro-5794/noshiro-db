import type { CalendarBoardEntry } from '@/shared/api';

/**
 * Anime air times are published in Japan standard time. Every provider reports
 * the *day* in that zone too, so rendering the clock in the viewer's local zone
 * would show "Monday 06:30" for a show that airs Tuesday 07:30 JST. The calendar
 * therefore pins both the day and the clock to the broadcast zone.
 */
export const AIRING_TIME_ZONE = 'Asia/Tokyo';

/** Short label shown next to the toolbar title so the clock is unambiguous. */
export const AIRING_TIME_ZONE_LABEL = 'JST';

export type CalendarOccurrence = {
  key: string;
  entry: CalendarBoardEntry;
  date: Date;
  /** Minutes past midnight in {@link AIRING_TIME_ZONE}; `null` when unknown. */
  startMinutes: number | null;
  durationMinutes: number;
  tentative: boolean;
};

export type CalendarDay = {
  date: Date;
  key: string;
  timed: CalendarOccurrence[];
  tentative: CalendarOccurrence[];
};

export type WeekdayBucket = {
  /** ISO weekday, 1 = Monday … 7 = Sunday. `null` collects unscheduled works. */
  weekday: number | null;
  entries: CalendarBoardEntry[];
};

/** ISO weekday order used by both the grid header and the broadcast board. */
export const isoWeekdays = [1, 2, 3, 4, 5, 6, 7] as const;

export const sourceLabels: Record<string, string> = {
  anilist: 'AniList',
  mal: 'MAL',
  bangumi: 'Bangumi',
};

export function sourceLabel(provider: string): string {
  return sourceLabels[provider] ?? provider.toUpperCase();
}

export function dateKey(date: Date): string {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function addDays(date: Date, amount: number): Date {
  const next = new Date(date);
  next.setDate(next.getDate() + amount);
  return next;
}

export function addMonths(date: Date, amount: number): Date {
  return new Date(date.getFullYear(), date.getMonth() + amount, 1);
}

/** Move by whole months while keeping the day of month when it exists. */
export function shiftMonth(date: Date, amount: number): Date {
  const lastDay = new Date(date.getFullYear(), date.getMonth() + amount + 1, 0).getDate();
  return new Date(date.getFullYear(), date.getMonth() + amount, Math.min(date.getDate(), lastDay));
}

export function startOfWeek(date: Date): Date {
  const next = new Date(date);
  next.setHours(0, 0, 0, 0);
  const weekday = (next.getDay() + 6) % 7; // Monday = 0
  return addDays(next, -weekday);
}

export function startOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

export function monthGridRange(date: Date): { from: Date; to: Date } {
  const first = startOfMonth(date);
  const last = new Date(date.getFullYear(), date.getMonth() + 1, 0);
  return { from: startOfWeek(first), to: addDays(startOfWeek(last), 6) };
}

export function weekRange(date: Date): { from: Date; to: Date } {
  const from = startOfWeek(date);
  return { from, to: addDays(from, 6) };
}

export function rangeDays(from: Date, to: Date): Date[] {
  const days: Date[] = [];
  for (let cursor = new Date(from); cursor <= to; cursor = addDays(cursor, 1)) {
    days.push(new Date(cursor));
  }
  return days;
}

/**
 * Broadcast window of a board, derived from its season key (`2026Q3`).
 *
 * The board is a weekly schedule for one season, so projecting it onto every
 * week forever would show the same works in a future year. The calendar clamps
 * both its projection and its navigation to this window; when the season rolls
 * over the next board supplies the next window.
 */
export function seasonWindow(seasonKey: string): { from: Date; to: Date } | null {
  const match = /^(\d{4})Q([1-4])$/.exec(seasonKey.trim().toUpperCase());
  if (!match) return null;
  const year = Number(match[1]);
  const quarter = Number(match[2]);
  const startMonth = (quarter - 1) * 3;
  return {
    from: new Date(year, startMonth, 1),
    to: new Date(year, startMonth + 3, 0),
  };
}

export function isWithin(date: Date, window: { from: Date; to: Date | null } | null): boolean {
  if (!window) return true;
  const value = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
  return value >= window.from.getTime() && (window.to === null || value <= window.to.getTime());
}

/**
 * Months a visitor can browse for one board: the season plus the month before
 * and after it, so any month of the season can show its neighbours.
 */
export function boardWindow(seasonKey: string): { from: Date; to: Date } | null {
  const season = seasonWindow(seasonKey);
  if (!season) return null;
  return {
    from: new Date(season.from.getFullYear(), season.from.getMonth() - 1, 1),
    to: new Date(season.to.getFullYear(), season.to.getMonth() + 2, 0),
  };
}

/** Parse a `YYYY-MM-DD` payload value without shifting it into another zone. */
export function parseDateOnly(value: string | null): Date | null {
  if (!value) return null;
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value.trim());
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (!year || !month || !day) return null;
  return new Date(year, month - 1, day);
}

/**
 * Broadcast run of one work.
 *
 * A weekly slot is only true between a work's premiere and its finale, so the
 * calendar projects an entry inside this window rather than across a whole
 * season. When the finale is unknown it is derived from the episode count, and
 * when even the premiere is unknown the entry falls back to the board window.
 */
export function runWindowOf(entry: CalendarBoardEntry): { from: Date; to: Date | null } | null {
  const from = parseDateOnly(entry.premieredOn);
  if (!from) return null;
  const explicitEnd = parseDateOnly(entry.endedOn);
  if (explicitEnd) return { from, to: explicitEnd };
  if (entry.episodeCount && entry.episodeCount > 0) {
    return { from, to: addDays(from, (entry.episodeCount - 1) * 7 + 6) };
  }
  // The board only lists works a provider reports as airing, so an entry with a
  // past premiere and no known length is a long runner: bound the start, leave
  // the end open rather than expiring a show that is still on air.
  return { from, to: null };
}

function entryWeekday(entry: CalendarBoardEntry): number | null {
  if (entry.weekday !== null) return entry.weekday;
  // A day-precision bar carries a one-off release date, not a weekly slot, so
  // it must never be projected onto a weekday column.
  if (entry.precision === 'day') return null;
  if (!entry.startsAt) return null;
  const parts = airingDateParts(entry.startsAt);
  if (!parts) return null;
  return parts.weekday;
}

type AiringParts = {
  hours: number;
  minutes: number;
  /** ISO weekday, 1 = Monday … 7 = Sunday. */
  weekday: number;
};

const airingFormatter = new Intl.DateTimeFormat('en-US', {
  timeZone: AIRING_TIME_ZONE,
  hour: '2-digit',
  minute: '2-digit',
  weekday: 'short',
  hour12: false,
});

const weekdayFromShortName: Record<string, number> = {
  Mon: 1,
  Tue: 2,
  Wed: 3,
  Thu: 4,
  Fri: 5,
  Sat: 6,
  Sun: 7,
};

const airingDateFormatter = new Intl.DateTimeFormat('en-CA', {
  timeZone: AIRING_TIME_ZONE,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
});

/** Calendar date of an instant in the broadcast zone. */
export function airingCalendarDate(value: string | null): Date | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  const [year, month, day] = airingDateFormatter.format(date).split('-').map(Number);
  if (year === undefined || month === undefined || day === undefined) return null;
  return new Date(year, month - 1, day);
}

function airingDateParts(value: string | null): AiringParts | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  const parts = airingFormatter.formatToParts(date);
  const lookup = new Map(parts.map((part) => [part.type, part.value]));
  const hours = Number(lookup.get('hour'));
  const minutes = Number(lookup.get('minute'));
  const weekday = weekdayFromShortName[lookup.get('weekday') ?? ''];
  if (!Number.isFinite(hours) || !Number.isFinite(minutes) || weekday === undefined) return null;
  return { hours: hours % 24, minutes, weekday };
}

/** Minutes past midnight in the broadcast zone, or `null` when unknown. */
export function startMinutesOf(entry: CalendarBoardEntry): number | null {
  const parts = airingDateParts(entry.startsAt);
  if (!parts) return null;
  return parts.hours * 60 + parts.minutes;
}

export function durationMinutesOf(entry: CalendarBoardEntry): number {
  if (entry.durationMinutes) return entry.durationMinutes;
  if (entry.startsAt && entry.endsAt) {
    const start = new Date(entry.startsAt).getTime();
    const end = new Date(entry.endsAt).getTime();
    if (Number.isFinite(start) && Number.isFinite(end) && end > start) {
      return Math.round((end - start) / 60_000);
    }
  }
  return 30;
}

export function buildOccurrences(
  entries: CalendarBoardEntry[],
  from: Date,
  to: Date,
  window: { from: Date; to: Date } | null = null,
): CalendarOccurrence[] {
  const days = rangeDays(from, to);
  const occurrences: CalendarOccurrence[] = [];

  for (const entry of entries) {
    const weekday = entryWeekday(entry);
    if (weekday === null) continue;
    const startMinutes = startMinutesOf(entry);
    const durationMinutes = durationMinutesOf(entry);
    const run = runWindowOf(entry);
    // A run that ends before the board even starts is inconsistent source data:
    // the work is on this board, so it is still airing. Keep it rather than
    // hiding a live show behind a bad date.
    const boundedRun =
      run && run.to !== null && window !== null && run.to < window.from ? { from: run.from, to: null } : run;

    for (const day of days) {
      if (!isWithin(day, window)) continue;
      if (boundedRun && !isWithin(day, boundedRun)) continue;
      const isoWeekday = day.getDay() === 0 ? 7 : day.getDay();
      if (isoWeekday !== weekday) continue;
      occurrences.push({
        key: `${entry.id}:${dateKey(day)}`,
        entry,
        date: new Date(day),
        startMinutes,
        durationMinutes,
        tentative: startMinutes === null,
      });
    }
  }

  return occurrences;
}

export function groupOccurrences(occurrences: CalendarOccurrence[]): Map<string, CalendarDay> {
  const days = new Map<string, CalendarDay>();
  for (const occurrence of occurrences) {
    const key = dateKey(occurrence.date);
    const day = days.get(key) ?? {
      date: occurrence.date,
      key,
      timed: [],
      tentative: [],
    };
    if (occurrence.tentative) day.tentative.push(occurrence);
    else day.timed.push(occurrence);
    days.set(key, day);
  }
  for (const day of days.values()) {
    day.timed.sort((left, right) => (left.startMinutes ?? 0) - (right.startMinutes ?? 0));
    day.tentative.sort((left, right) => titleOf(left).localeCompare(titleOf(right)));
  }
  return days;
}

/**
 * Build the occurrence that represents an entry right now: the next date whose
 * weekday matches the entry's schedule, carrying its airtime when known. Used by
 * the broadcast board, which lists works rather than dated cells.
 */
export function occurrenceFor(entry: CalendarBoardEntry, reference: Date): CalendarOccurrence {
  const weekday = entryWeekday(entry);
  let date = new Date(reference);
  date.setHours(0, 0, 0, 0);
  if (weekday !== null) {
    for (let step = 0; step < 7; step += 1) {
      const candidate = addDays(date, step);
      const isoWeekday = candidate.getDay() === 0 ? 7 : candidate.getDay();
      if (isoWeekday === weekday) {
        date = candidate;
        break;
      }
    }
  } else {
    // A one-off release keeps its own date instead of snapping to the cursor.
    date = airingCalendarDate(entry.startsAt) ?? date;
  }
  const startMinutes = startMinutesOf(entry);
  return {
    key: `${entry.id}:${dateKey(date)}`,
    entry,
    date,
    startMinutes,
    durationMinutes: durationMinutesOf(entry),
    tentative: startMinutes === null,
  };
}

export type PositionedOccurrence = {
  occurrence: CalendarOccurrence;
  /** Minutes past midnight. */
  startMinutes: number;
  durationMinutes: number;
  /** Zero-based column inside its overlapping cluster. */
  lane: number;
  /** Width divisor for the cluster, so blocks never sit on top of each other. */
  laneCount: number;
};

/**
 * Assign side-by-side lanes to overlapping timed occurrences, the way a
 * calendar lays out concurrent events. Occurrences without a start time are
 * skipped — they belong to the unscheduled strip instead.
 */
export function layoutOccurrences(occurrences: CalendarOccurrence[]): PositionedOccurrence[] {
  const timed = occurrences.flatMap((occurrence) => {
    if (occurrence.startMinutes === null) return [];
    const startMinutes = occurrence.startMinutes;
    const durationMinutes = Math.max(15, occurrence.durationMinutes);
    return [{ occurrence, startMinutes, durationMinutes }];
  });
  timed.sort((left, right) => left.startMinutes - right.startMinutes || left.durationMinutes - right.durationMinutes);

  const laidOut: PositionedOccurrence[] = [];
  let cluster: PositionedOccurrence[] = [];
  let clusterEnd = Number.NEGATIVE_INFINITY;

  const flush = () => {
    if (cluster.length === 0) return;
    const laneCount = Math.max(...cluster.map((item) => item.lane)) + 1;
    laidOut.push(...cluster.map((item) => ({ ...item, laneCount })));
    cluster = [];
  };

  for (const item of timed) {
    if (item.startMinutes >= clusterEnd) {
      flush();
      clusterEnd = item.startMinutes + item.durationMinutes;
    } else {
      clusterEnd = Math.max(clusterEnd, item.startMinutes + item.durationMinutes);
    }
    const laneIndex = cluster.findIndex(
      (existing) => existing.startMinutes + existing.durationMinutes <= item.startMinutes,
    );
    if (laneIndex === -1) {
      cluster.push({ ...item, lane: cluster.length, laneCount: 1 });
    } else {
      const lane = cluster[laneIndex];
      cluster[laneIndex] = { ...item, lane: lane?.lane ?? 0, laneCount: 1 };
    }
  }
  flush();
  return laidOut;
}

export function titleOf(occurrence: CalendarOccurrence): string {
  return titleOfEntry(occurrence.entry);
}

export function providerOf(entry: CalendarBoardEntry): string {
  return entry.sources[0]?.provider ?? 'unknown';
}

export function weekdaysOf(entry: CalendarBoardEntry): (number | null)[] {
  const weekday = entryWeekday(entry);
  return weekday === null ? [null] : [weekday];
}

/** Format minutes past midnight as a wall-clock label in the active locale. */
export function formatMinutesOfDay(minutes: number, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(2024, 0, 1, Math.floor(minutes / 60) % 24, minutes % 60));
}

/** Current time inside the broadcast zone, expressed as minutes past midnight. */
export function nowMinutes(): number {
  const parts = airingDateParts(new Date().toISOString());
  return parts ? parts.hours * 60 + parts.minutes : 0;
}

/**
 * Bucket raw board entries by ISO weekday for the broadcast board. Entries
 * without a weekday land in the trailing "unscheduled" bucket so nothing is
 * silently dropped from the view.
 */
export function groupEntriesByWeekday(entries: CalendarBoardEntry[]): WeekdayBucket[] {
  const buckets = new Map<number | null, CalendarBoardEntry[]>([...isoWeekdays, null].map((weekday) => [weekday, []]));

  for (const entry of entries) {
    for (const weekday of weekdaysOf(entry)) {
      buckets.get(weekday)?.push(entry);
    }
  }

  return [...buckets.entries()]
    .filter(([, items]) => items.length > 0)
    .map(([weekday, items]) => ({
      weekday,
      entries: [...items].sort(compareBoardEntries),
    }));
}

function compareBoardEntries(left: CalendarBoardEntry, right: CalendarBoardEntry): number {
  const leftMinutes = startMinutesOf(left);
  const rightMinutes = startMinutesOf(right);
  if (leftMinutes !== rightMinutes) {
    if (leftMinutes === null) return 1;
    if (rightMinutes === null) return -1;
    return leftMinutes - rightMinutes;
  }
  return titleOfEntry(left).localeCompare(titleOfEntry(right));
}

export function titleOfEntry(entry: CalendarBoardEntry): string {
  return entry.work?.displayName || entry.workId;
}

/** Whether the work has no weekly slot (films, OVAs, one-off specials). */
export function isWeekdayless(entry: CalendarBoardEntry): boolean {
  return entryWeekday(entry) === null;
}

/** Localised release date in the broadcast zone, e.g. "7月24日". */
export function formatAiringDate(value: string | null, locale: string): string {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat(locale, {
    timeZone: AIRING_TIME_ZONE,
    month: 'short',
    day: 'numeric',
  }).format(date);
}

export function formatTime(minutes: number | null, locale: string): string {
  if (minutes === null) return '';
  return formatMinutesOfDay(minutes, locale);
}

export function formatDayTitle(date: Date, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  }).format(date);
}

export function formatMonthTitle(date: Date, locale: string): string {
  return new Intl.DateTimeFormat(locale, { year: 'numeric', month: 'long' }).format(date);
}

export function formatWeekday(date: Date, locale: string): string {
  return new Intl.DateTimeFormat(locale, { weekday: 'short' }).format(date);
}

/**
 * Monday-first weekday labels. Both the month grid and the broadcast board use
 * the ISO week so a single header component can serve either layout.
 */
export function weekdayLabels(locale: string): string[] {
  const monday = new Date(2024, 0, 1); // 2024-01-01 is a Monday.
  return Array.from({ length: 7 }, (_, index) => formatWeekday(addDays(monday, index), locale));
}

/** Long weekday name for a 1-based ISO weekday. */
export function weekdayName(locale: string, isoWeekday: number): string {
  const monday = new Date(2024, 0, 1);
  return new Intl.DateTimeFormat(locale, { weekday: 'long' }).format(addDays(monday, isoWeekday - 1));
}

export function isSameDay(left: Date, right: Date): boolean {
  return dateKey(left) === dateKey(right);
}
