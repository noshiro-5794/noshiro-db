import { describe, expect, it } from 'vitest';
import { buildYearDays, contributionLevel, getWeekIndex } from './contribution-calendar';

describe('contribution calendar', () => {
  it('builds complete UTC years including leap days', () => {
    expect(buildYearDays(2024)).toHaveLength(366);
    expect(buildYearDays(2025)).toHaveLength(365);
    expect(buildYearDays(2024)).toContain('2024-02-29');
  });

  it('maps dates to stable calendar columns', () => {
    expect(getWeekIndex('2026-01-01')).toBe(0);
    expect(getWeekIndex('2026-01-04')).toBe(1);
  });

  it('normalizes arbitrary counts into five visual levels', () => {
    expect([-1, 0, 1, 2, 4, 7].map(contributionLevel)).toEqual([0, 0, 1, 2, 3, 4]);
  });
});
