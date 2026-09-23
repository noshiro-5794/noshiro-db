import { describe, expect, it } from 'vitest';
import type { CalendarBoardEntry } from '@/shared/api';
import {
  buildOccurrences,
  dateKey,
  formatMinutesOfDay,
  groupEntriesByWeekday,
  groupOccurrences,
  layoutOccurrences,
  occurrenceFor,
} from './calendar-model';

function entry(overrides: Partial<CalendarBoardEntry>): CalendarBoardEntry {
  return {
    id: 'entry',
    seasonKey: '2026Q3',
    windowStart: '2026-08-01',
    windowEnd: '2026-10-31',
    workId: 'work',
    episodeEntityId: null,
    episodeNumber: null,
    startsAt: null,
    endsAt: null,
    timezone: 'Asia/Tokyo',
    region: '',
    weekday: 1,
    durationMinutes: 24,
    precision: 'minute',
    format: 'TV',
    premieredOn: '2026-07-01',
    endedOn: null,
    episodeCount: 12,
    status: 'scheduled',
    decision: 'consensus',
    confidence: 1,
    sources: [],
    work: null,
    ...overrides,
  };
}

describe('calendar-model', () => {
  it('expands weekly entries into dated occurrences', () => {
    const precise = entry({
      id: 'precise',
      weekday: 1,
      startsAt: '2026-09-21T13:30:00Z',
    });
    const tentative = entry({
      id: 'tentative',
      weekday: 2,
      startsAt: null,
      precision: 'weekday',
    });

    const occurrences = buildOccurrences([precise, tentative], new Date(2026, 8, 21), new Date(2026, 8, 27));
    const days = groupOccurrences(occurrences);

    expect(occurrences).toHaveLength(2);
    expect(days.get(dateKey(new Date(2026, 8, 21)))?.timed).toHaveLength(1);
    expect(days.get(dateKey(new Date(2026, 8, 22)))?.tentative).toHaveLength(1);
  });

  it('buckets board entries by weekday and keeps unscheduled works', () => {
    const buckets = groupEntriesByWeekday([
      entry({ id: 'late', weekday: 3, startsAt: '2026-09-23T05:00:00Z' }),
      entry({ id: 'early', weekday: 3, startsAt: '2026-09-23T01:00:00Z' }),
      entry({ id: 'movie', weekday: null, startsAt: null, precision: 'weekday' }),
    ]);

    expect(buckets.map((bucket) => bucket.weekday)).toEqual([3, null]);
    expect(buckets[0]?.entries.map((item) => item.id)).toEqual(['early', 'late']);
  });

  it('assigns side-by-side lanes to overlapping occurrences', () => {
    const [first, second] = [
      entry({ id: 'a', weekday: 1, startsAt: '2026-09-21T13:00:00Z', durationMinutes: 60 }),
      entry({ id: 'b', weekday: 1, startsAt: '2026-09-21T13:30:00Z', durationMinutes: 60 }),
    ];
    const occurrences = buildOccurrences([first, second], new Date(2026, 8, 21), new Date(2026, 8, 21));

    const laidOut = layoutOccurrences(occurrences);

    expect(laidOut).toHaveLength(2);
    expect(new Set(laidOut.map((item) => item.lane))).toEqual(new Set([0, 1]));
    expect(laidOut.every((item) => item.laneCount === 2)).toBe(true);
  });

  it('resolves the next dated occurrence for a board entry', () => {
    const occurrence = occurrenceFor(
      entry({ id: 'a', weekday: 1, startsAt: '2026-09-21T13:30:00Z', durationMinutes: 24 }),
      new Date(2026, 8, 23),
    );

    expect(dateKey(occurrence.date)).toBe('2026-09-28');
    expect(occurrence.tentative).toBe(false);
  });

  it('formats minutes past midnight as a wall clock label', () => {
    expect(formatMinutesOfDay(23 * 60 + 5, 'en-US')).toMatch(/23:05/);
  });
});
