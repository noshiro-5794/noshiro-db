import { afterEach, describe, expect, it, vi } from 'vitest';
import { indexApi } from './subject-api';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('indexApi.getBangumiSubject', () => {
  it('accepts a valid snapshot and sends a privacy-preserving request', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 4255,
          name: 'Noshiro',
          rank: null,
          rating: { total: 10, score: 8.2, count: { '8': 4 } },
          collection: { wish: 3, collect: 7 },
        }),
        { status: 200 },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(indexApi.getBangumiSubject(4255)).resolves.toMatchObject({ id: 4255, name: 'Noshiro' });
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(fetchMock.mock.calls[0]?.[0]).toBe('https://api.bgm.tv/v0/entities/4255');
    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({ referrerPolicy: 'no-referrer' });
  });

  it('rejects invalid IDs before issuing a request', async () => {
    const fetchMock = vi.fn<typeof fetch>();
    vi.stubGlobal('fetch', fetchMock);

    await expect(indexApi.getBangumiSubject(Number.NaN)).rejects.toMatchObject({
      kind: 'invalid-request',
    });
    await expect(indexApi.getBangumiSubject(-1)).rejects.toMatchObject({
      kind: 'invalid-request',
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('rejects malformed JSON and structurally invalid responses', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(new Response('{', { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: '4255', rating: [] }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: 9999 }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    await expect(indexApi.getBangumiSubject(4255)).rejects.toMatchObject({
      kind: 'invalid-response',
    });
    await expect(indexApi.getBangumiSubject(4255)).rejects.toMatchObject({
      kind: 'invalid-response',
    });
    await expect(indexApi.getBangumiSubject(4255)).rejects.toMatchObject({
      kind: 'invalid-response',
    });
  });

  it('classifies HTTP and network failures without exposing response bodies', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(new Response('private upstream details', { status: 503 }))
      .mockRejectedValueOnce(new TypeError('offline'));
    vi.stubGlobal('fetch', fetchMock);

    await expect(indexApi.getBangumiSubject(4255)).rejects.toMatchObject({
      kind: 'http',
      status: 503,
    });
    await expect(indexApi.getBangumiSubject(4255)).rejects.toMatchObject({
      kind: 'network',
      status: null,
    });
  });

  it('preserves caller cancellation instead of reporting a network failure', async () => {
    const controller = new AbortController();
    const abortError = new DOMException('cancelled', 'AbortError');
    const fetchMock = vi.fn<typeof fetch>().mockImplementation((_input, init) => {
      controller.abort();
      expect(init?.signal).toBeInstanceOf(AbortSignal);
      return Promise.reject(abortError);
    });
    vi.stubGlobal('fetch', fetchMock);

    await expect(indexApi.getBangumiSubject(4255, { signal: controller.signal })).rejects.toBe(abortError);
  });
});
