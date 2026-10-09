import { describe, expect, it } from 'vitest';
import { parseUuid } from './validation';

describe('parseUuid', () => {
  it('accepts canonical UUIDs and normalizes their case', () => {
    expect(parseUuid('550E8400-E29B-41D4-A716-446655440000')).toBe('550e8400-e29b-41d4-a716-446655440000');
  });

  it('rejects malformed, non-RFC, and padded UUIDs', () => {
    expect(parseUuid('550e8400e29b41d4a716446655440000')).toBeNull();
    expect(parseUuid('550e8400-e29b-01d4-a716-446655440000')).toBeNull();
    expect(parseUuid(' 550e8400-e29b-41d4-a716-446655440000 ')).toBeNull();
    expect(parseUuid(null)).toBeNull();
  });
});
