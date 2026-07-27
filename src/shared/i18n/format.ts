import type { Locale } from './catalog';

const weekdayDates = {
  Mon: new Date(Date.UTC(2024, 0, 1)),
  Tue: new Date(Date.UTC(2024, 0, 2)),
  Wed: new Date(Date.UTC(2024, 0, 3)),
  Thu: new Date(Date.UTC(2024, 0, 4)),
  Fri: new Date(Date.UTC(2024, 0, 5)),
  Sat: new Date(Date.UTC(2024, 0, 6)),
  Sun: new Date(Date.UTC(2024, 0, 7)),
} as const;

export type Weekday = keyof typeof weekdayDates;

export function formatWeekday(locale: Locale, weekday: Weekday) {
  return new Intl.DateTimeFormat(locale, { timeZone: 'UTC', weekday: 'short' }).format(weekdayDates[weekday]);
}
