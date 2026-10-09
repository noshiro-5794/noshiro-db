import { describe, expect, it } from 'vitest';
import { ApiError } from '@/shared/api';
import { shouldRetryQuery } from './query-client';

function apiError(status: number) {
  return new ApiError('Request failed', {
    code: -1,
    data: null,
    status,
    url: '/api/test/',
  });
}

describe('query retry policy', () => {
  it.each([400, 401, 403, 404, 409, 422])('does not retry terminal HTTP %i responses', (status) => {
    expect(shouldRetryQuery(0, apiError(status))).toBe(false);
  });

  it.each([408, 429, 500, 502, 503])('retries transient HTTP %i responses', (status) => {
    expect(shouldRetryQuery(0, apiError(status))).toBe(true);
  });

  it('retries network errors within the retry budget', () => {
    expect(shouldRetryQuery(0, new TypeError('Failed to fetch'))).toBe(true);
    expect(shouldRetryQuery(2, new TypeError('Failed to fetch'))).toBe(false);
  });
});
