import { describe, expect, it } from 'vitest';
import { formatDate, formatDateTime, formatTime } from './date';

describe('date formatting', () => {
  it('returns the requested fallback for absent and invalid values', () => {
    expect(formatDate(undefined, 'Unknown')).toBe('Unknown');
    expect(formatDate('not-a-date', 'Unknown')).toBe('Unknown');
    expect(formatDateTime(Number.NaN)).toBe('');
    expect(formatTime(new Date(Number.NaN))).toBe('');
  });

  it('formats valid timestamps without changing the input', () => {
    const value = '2026-01-02T03:04:05Z';
    expect(formatDate(value)).not.toBe('');
    expect(formatDateTime(value)).not.toBe('');
    expect(formatTime(value)).not.toBe('');
    expect(value).toBe('2026-01-02T03:04:05Z');
  });
});
