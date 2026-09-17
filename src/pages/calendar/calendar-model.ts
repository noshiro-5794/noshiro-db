import type { CalendarBoardEntry } from '@/shared/api';

export type CalendarOccurrence = {
  key: string;
  entry: CalendarBoardEntry;
  date: Date;
  startsAt: Date | null;
  endsAt: Date | null;
  tentative: boolean;
};

export type CalendarDay = {
  date: Date;
  key: string;
  timed: CalendarOccurrence[];
  tentative: CalendarOccurrence[];
};

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

function entryWeekday(entry: CalendarBoardEntry): number | null {
  if (entry.weekday !== null) return entry.weekday;
  if (!entry.startsAt) return null;
  const date = new Date(entry.startsAt);
  if (Number.isNaN(date.getTime())) return null;
  return date.getDay() === 0 ? 7 : date.getDay();
}

function localTimeParts(value: string | null): { hours: number; minutes: number } | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return { hours: date.getHours(), minutes: date.getMinutes() };
}

export function buildOccurrences(entries: CalendarBoardEntry[], from: Date, to: Date): CalendarOccurrence[] {
  const days = rangeDays(from, to);
  const occurrences: CalendarOccurrence[] = [];

  for (const entry of entries) {
    const weekday = entryWeekday(entry);
    if (weekday === null) continue;
    const time = localTimeParts(entry.startsAt);
    const duration = entry.durationMinutes ?? 24;

    for (const day of days) {
      const isoWeekday = day.getDay() === 0 ? 7 : day.getDay();
      if (isoWeekday !== weekday) continue;
      let startsAt: Date | null = null;
      let endsAt: Date | null = null;
      if (time) {
        startsAt = new Date(day);
        startsAt.setHours(time.hours, time.minutes, 0, 0);
        endsAt = new Date(startsAt.getTime() + duration * 60_000);
      }
      occurrences.push({
        key: `${entry.id}:${dateKey(day)}`,
        entry,
        date: new Date(day),
        startsAt,
        endsAt,
        tentative: startsAt === null,
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
    day.timed.sort((left, right) => (left.startsAt?.getTime() ?? 0) - (right.startsAt?.getTime() ?? 0));
    day.tentative.sort((left, right) => titleOf(left).localeCompare(titleOf(right)));
  }
  return days;
}

export function titleOf(occurrence: CalendarOccurrence): string {
  return occurrence.entry.work?.displayName || occurrence.entry.workId;
}

export function primaryProvider(occurrence: CalendarOccurrence): string {
  return occurrence.entry.sources[0]?.provider ?? '';
}

export function formatTime(date: Date | null, locale: string): string {
  if (!date) return '';
  return new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit', hour12: false }).format(date);
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
