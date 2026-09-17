import { describe, expect, it } from 'vitest';
import type { CalendarBoardEntry } from '@/shared/api';
import { buildOccurrences, dateKey, groupOccurrences } from './calendar-model';

function entry(overrides: Partial<CalendarBoardEntry>): CalendarBoardEntry {
  return {
    id: 'entry',
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
});
