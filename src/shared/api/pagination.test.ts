import { describe, expect, it, vi } from 'vitest';
import type { ApiPage } from './contracts/common';
import { collectApiPages, decodeApiPage, decodeApiPageShape, getNextApiPageParam } from './pagination';

function page<T>(results: T[], options: Partial<ApiPage<T>> = {}): ApiPage<T> {
  return {
    count: options.count ?? results.length,
    next: options.next ?? null,
    previous: options.previous ?? null,
    results,
  };
}

describe('collectApiPages', () => {
  it('collects every page using the declared endpoint page size', async () => {
    const fetchPage = vi
      .fn()
      .mockResolvedValueOnce(page([1, 2], { count: 3, next: '/items?page=2' }))
      .mockResolvedValueOnce(page([3], { count: 3 }));

    await expect(collectApiPages(fetchPage, { pageSize: 2 })).resolves.toEqual([1, 2, 3]);
    expect(fetchPage).toHaveBeenNthCalledWith(1, { page: 1, page_size: 2 });
    expect(fetchPage).toHaveBeenNthCalledWith(2, { page: 2, page_size: 2 });
  });

  it('stops once the reported count is satisfied even if next is stale', async () => {
    const fetchPage = vi.fn().mockResolvedValue(page([1, 2], { count: 2, next: '/stale' }));

    await expect(collectApiPages(fetchPage, { pageSize: 2 })).resolves.toEqual([1, 2]);
    expect(fetchPage).toHaveBeenCalledOnce();
  });

  it('preserves cancellation before another page is requested', async () => {
    const controller = new AbortController();
    const fetchPage = vi.fn().mockImplementation(() => {
      controller.abort();
      return Promise.resolve(page([1], { count: 2, next: '/items?page=2' }));
    });

    await expect(collectApiPages(fetchPage, { pageSize: 1, signal: controller.signal })).rejects.toMatchObject({
      name: 'AbortError',
    });
    expect(fetchPage).toHaveBeenCalledOnce();
  });

  it('rejects non-advancing and unbounded pagination responses', async () => {
    await expect(
      collectApiPages(() => Promise.resolve(page([], { count: 1, next: '/items?page=2' })), { pageSize: 1 }),
    ).rejects.toThrow('empty page');

    await expect(
      collectApiPages(
        (query) => Promise.resolve(page([query.page], { count: 10, next: `/items?page=${query.page + 1}` })),
        {
          pageSize: 1,
          maxPages: 2,
        },
      ),
    ).rejects.toThrow('safety limit');
  });

  it('rejects malformed pages, repeated cursors, and oversized collections', async () => {
    await expect(
      collectApiPages(() => Promise.resolve({ count: Number.NaN, next: null, previous: null, results: [1] }), {
        pageSize: 1,
      }),
    ).rejects.toThrow('invalid page');

    await expect(
      collectApiPages(() => Promise.resolve(page([1], { count: 3, next: '/same' })), { pageSize: 1 }),
    ).rejects.toThrow('repeated next link');

    await expect(
      collectApiPages(() => Promise.resolve(page([1, 2], { count: 2 })), { pageSize: 2, maxItems: 1 }),
    ).rejects.toThrow('item safety limit');
  });
});

describe('getNextApiPageParam', () => {
  it('advances only while the count and safety limit require another page', () => {
    const first = page([1, 2], { count: 3, next: '/items?page=2' });
    expect(getNextApiPageParam(first, [first])).toBe(2);
    expect(getNextApiPageParam({ ...first, count: 2 }, [first])).toBeUndefined();
    expect(getNextApiPageParam(first, [first], 1)).toBeUndefined();
  });

  it('stops on an empty page even when the server advertises a next link', () => {
    const empty = page([], { count: 10, next: '/items?page=2' });
    expect(getNextApiPageParam(empty, [empty])).toBeUndefined();
  });
});

describe('decodeApiPageShape', () => {
  it('accepts a valid pagination envelope', () => {
    expect(
      decodeApiPageShape<{ id: number }>({
        count: 1,
        next: null,
        previous: null,
        results: [{ id: 1 }],
      }),
    ).toEqual({ count: 1, next: null, previous: null, results: [{ id: 1 }] });
  });

  it('applies an item decoder to every result', () => {
    const decoded = decodeApiPage({ count: 2, next: null, previous: null, results: [1, 2] }, (item) => {
      if (typeof item !== 'number') throw new TypeError('Expected a number');
      return String(item);
    });

    expect(decoded.results).toEqual(['1', '2']);
  });

  it.each([
    null,
    {},
    { count: -1, next: null, previous: null, results: [] },
    { count: 0, next: 1, previous: null, results: [] },
    { count: 0, next: null, previous: null, results: {} },
  ])('rejects malformed pagination envelopes', (value) => {
    expect(() => decodeApiPageShape(value)).toThrow(TypeError);
  });
});
