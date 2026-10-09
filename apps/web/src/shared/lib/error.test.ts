import { describe, expect, it } from 'vitest';
import { getErrorMessage } from './error';

describe('getErrorMessage', () => {
  it('uses non-empty Error messages', () => {
    expect(getErrorMessage(new Error('Request rejected'), 'Fallback')).toBe('Request rejected');
  });

  it('falls back for empty or non-Error values', () => {
    expect(getErrorMessage(new Error(''), 'Fallback')).toBe('Fallback');
    expect(getErrorMessage({ message: 'untrusted shape' }, 'Fallback')).toBe('Fallback');
  });
});
