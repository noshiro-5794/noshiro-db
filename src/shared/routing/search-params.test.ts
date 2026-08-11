import { describe, expect, it } from 'vitest';
import { parseEnumParam, parseIntegerParam, parsePageParam, parseTextParam } from './search-params';

describe('search parameter parsing', () => {
  it('accepts only declared enum values', () => {
    const values = ['latest', 'oldest'] as const;
    expect(parseEnumParam('latest', values, 'oldest')).toBe('latest');
    expect(parseEnumParam('invalid', values, 'oldest')).toBe('oldest');
    expect(parseEnumParam(null, values, 'oldest')).toBe('oldest');
  });

  it('rejects fractional, unsafe, negative, and unreasonably large pages', () => {
    expect(parsePageParam('2')).toBe(2);
    expect(parsePageParam('1.5')).toBe(1);
    expect(parsePageParam('Infinity')).toBe(1);
    expect(parsePageParam('-2')).toBe(1);
    expect(parsePageParam('10001')).toBe(1);
  });

  it('parses bounded integers and text without control characters', () => {
    expect(parseIntegerParam('2026', { min: 1900, max: 2030 })).toBe(2026);
    expect(parseIntegerParam('9999', { min: 1900, max: 2030 })).toBeNull();
    expect(parseTextParam(' value ', { maxLength: 16, trim: true })).toBe('value');
    expect(parseTextParam('bad\nvalue', { maxLength: 16 })).toBe('');
    expect(parseTextParam('x'.repeat(17), { maxLength: 16 })).toBe('');
  });
});
