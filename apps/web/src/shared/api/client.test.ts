import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  API_BASE_URL,
  ApiError,
  api,
  getAccessToken,
  setAccessToken,
  setAccessTokenRefresher,
  setSessionExpiredHandler,
} from './client';

function envelopeResponse(data: unknown, init?: ResponseInit) {
  return new Response(JSON.stringify({ code: 0, message: 'ok', data }), {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
}

function requestHeaders(fetchMock: ReturnType<typeof vi.fn<typeof fetch>>, callIndex = 0) {
  const call = fetchMock.mock.calls[callIndex];
  if (!call) {
    throw new Error(`Missing fetch call at index ${callIndex}`);
  }

  return new Headers(call[1]?.headers);
}

afterEach(() => {
  setAccessToken(null);
  setAccessTokenRefresher(null);
  setSessionExpiredHandler(null);
  vi.unstubAllGlobals();
});

describe('API client', () => {
  it('serializes query values and omits empty values', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(envelopeResponse({ id: 1 }));
    vi.stubGlobal('fetch', fetchMock);

    await api.get('/api/items/', {
      query: {
        active: false,
        empty: '',
        ignored: undefined,
        page: 2,
        tag: ['first', 'second'],
      },
      skipAuth: true,
    });

    expect(fetchMock).toHaveBeenCalledOnce();
    expect(fetchMock.mock.calls[0]?.[0]).toBe(`${API_BASE_URL}/api/items/?active=false&page=2&tag=first&tag=second`);
  });

  it.each(['https://attacker.example/api/', '//attacker.example/api/', 'api/items/', '/api\\items/', '/api/items/\n'])(
    'rejects unsafe API path %j before starting a request',
    async (path) => {
      const fetchMock = vi.fn<typeof fetch>();
      vi.stubGlobal('fetch', fetchMock);

      await expect(api.get(path)).rejects.toThrow(TypeError);
      expect(fetchMock).not.toHaveBeenCalled();
    },
  );

  it('accepts a raw JSON success body', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ code: 0, value: 'missing data and message' }), {
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const request = api.get('/api/items/');

    await expect(request).resolves.toEqual({ code: 0, value: 'missing data and message' });
  });

  it('converts response decoder failures into a safe API error', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(envelopeResponse({ privilege: 'admin' }));
    vi.stubGlobal('fetch', fetchMock);

    const request = api.get<{ privilege: boolean }>('/api/profile/', {
      decode: (value) => {
        if (typeof value !== 'object' || value === null || !('privilege' in value)) throw new TypeError();
        if (typeof value.privilege !== 'boolean') throw new TypeError('server payload should remain private');
        return { privilege: value.privilege };
      },
      skipAuth: true,
    });

    await expect(request).rejects.toMatchObject({
      code: -1,
      data: null,
      message: 'Invalid API response data',
      status: 200,
    } satisfies Partial<ApiError>);
  });

  it('adds the in-memory access token without overriding caller headers', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(envelopeResponse(null));
    vi.stubGlobal('fetch', fetchMock);
    setAccessToken('access-token');

    await api.get('/api/profile/', { headers: { 'X-Request-Id': 'request-id' } });

    const headers = requestHeaders(fetchMock);
    expect(headers.get('Authorization')).toBe('Bearer access-token');
    expect(headers.get('X-Request-Id')).toBe('request-id');
  });

  it('shares one token refresh between concurrent unauthorized requests', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockImplementation((_input, init) => {
      const authorization = new Headers(init?.headers).get('Authorization');
      return Promise.resolve(
        authorization === 'Bearer refreshed-token'
          ? envelopeResponse({ authorized: true })
          : envelopeResponse(null, { status: 401, statusText: 'Unauthorized' }),
      );
    });
    const refresh = vi.fn(() => Promise.resolve('refreshed-token'));
    const sessionExpired = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    setAccessToken('expired-token');
    setAccessTokenRefresher(refresh);
    setSessionExpiredHandler(sessionExpired);

    const responses = await Promise.all([api.get('/api/first/'), api.get('/api/second/')]);

    expect(responses).toEqual([{ authorized: true }, { authorized: true }]);
    expect(refresh).toHaveBeenCalledOnce();
    expect(fetchMock).toHaveBeenCalledTimes(4);
    expect(sessionExpired).not.toHaveBeenCalled();
  });

  it('expires the session once when a shared token refresh fails', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockImplementation(() => Promise.resolve(envelopeResponse(null, { status: 401, statusText: 'Unauthorized' })));
    const refreshError = new Error('Refresh failed');
    const refresh = vi.fn(() => Promise.reject(refreshError));
    const sessionExpired = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    setAccessToken('expired-token');
    setAccessTokenRefresher(refresh);
    setSessionExpiredHandler(sessionExpired);

    const results = await Promise.allSettled([api.get('/api/first/'), api.get('/api/second/')]);

    expect(results).toEqual([
      { status: 'rejected', reason: refreshError },
      { status: 'rejected', reason: refreshError },
    ]);
    expect(refresh).toHaveBeenCalledOnce();
    expect(sessionExpired).toHaveBeenCalledOnce();
  });

  it('does not restore a token when the session is cleared during a pending refresh', async () => {
    let resolveRefresh: ((token: string) => void) | undefined;
    const refreshResult = new Promise<string>((resolve) => {
      resolveRefresh = resolve;
    });
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockImplementation(() => Promise.resolve(envelopeResponse(null, { status: 401, statusText: 'Unauthorized' })));
    const sessionExpired = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    setAccessToken('expired-token');
    const refresh = vi.fn(() => refreshResult);
    setAccessTokenRefresher(refresh);
    setSessionExpiredHandler(sessionExpired);

    const request = api.get('/api/profile/');
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    setAccessToken(null);
    resolveRefresh?.('late-refreshed-token');

    await expect(request).rejects.toThrow('session changed');
    expect(getAccessToken()).toBeNull();
    expect(sessionExpired).not.toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it('does not refresh an unauthorized request after its token has already been cleared', async () => {
    let resolveRequest: ((response: Response) => void) | undefined;
    const response = new Promise<Response>((resolve) => {
      resolveRequest = resolve;
    });
    const fetchMock = vi.fn<typeof fetch>().mockReturnValue(response);
    const refresh = vi.fn(() => Promise.resolve('refreshed-token'));
    vi.stubGlobal('fetch', fetchMock);
    setAccessToken('expired-token');
    setAccessTokenRefresher(refresh);

    const request = api.get('/api/profile/');
    setAccessToken(null);
    resolveRequest?.(envelopeResponse(null, { status: 401, statusText: 'Unauthorized' }));

    await expect(request).rejects.toMatchObject({ status: 401 } satisfies Partial<ApiError>);
    expect(refresh).not.toHaveBeenCalled();
    expect(getAccessToken()).toBeNull();
  });

  it('passes AbortSignal through without treating cancellation as session expiry', async () => {
    const controller = new AbortController();
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(envelopeResponse({ id: 1 }));
    const sessionExpired = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    setSessionExpiredHandler(sessionExpired);

    await api.get('/api/items/', { signal: controller.signal });

    expect(fetchMock.mock.calls[0]?.[1]?.signal).toBe(controller.signal);
    expect(sessionExpired).not.toHaveBeenCalled();
  });
});
