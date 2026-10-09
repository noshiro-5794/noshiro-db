import type { ApiPage, CursorPage, PageQuery } from './contracts/common';

export type CollectApiPagesOptions = {
  pageSize: number;
  signal?: AbortSignal;
  maxPages?: number;
  maxItems?: number;
};

const DEFAULT_MAX_PAGES = 1_000;
const DEFAULT_MAX_ITEMS = 100_000;
const DEFAULT_INFINITE_MAX_PAGES = 100;

function assertPageShape(value: unknown, pageSize?: number): asserts value is ApiPage<unknown> {
  if (typeof value !== 'object' || value === null) {
    throw new TypeError('Paginated API returned an invalid page');
  }

  const { count, next, previous, results } = value as Record<string, unknown>;
  if (
    typeof count !== 'number' ||
    !Number.isSafeInteger(count) ||
    count < 0 ||
    !Array.isArray(results) ||
    (next !== null && typeof next !== 'string') ||
    (previous !== null && typeof previous !== 'string') ||
    (pageSize !== undefined && results.length > pageSize)
  ) {
    throw new TypeError('Paginated API returned an invalid page');
  }
}

export function decodeApiPageShape<T>(value: unknown): ApiPage<T> {
  assertPageShape(value);
  return {
    count: value.count,
    next: value.next,
    previous: value.previous,
    results: value.results as T[],
  };
}

export function decodeApiPage<T>(value: unknown, decodeItem: (item: unknown) => T): ApiPage<T> {
  const page = decodeApiPageShape<unknown>(value);
  return {
    ...page,
    results: page.results.map((item) => decodeItem(item)),
  };
}

function assertCursorPageShape(value: unknown): asserts value is CursorPage<unknown> {
  if (typeof value !== 'object' || value === null) {
    throw new TypeError('Cursor paginated API returned an invalid page');
  }

  const { next, previous, results } = value as Record<string, unknown>;
  if (
    !Array.isArray(results) ||
    (next !== null && typeof next !== 'string') ||
    (previous !== null && typeof previous !== 'string')
  ) {
    throw new TypeError('Cursor paginated API returned an invalid page');
  }
}

export function decodeCursorPage<T>(value: unknown, decodeItem: (item: unknown) => T): CursorPage<T> {
  assertCursorPageShape(value);
  return {
    next: value.next,
    previous: value.previous,
    results: value.results.map(decodeItem),
  };
}

export function getNextCursorPageParam<T>(lastPage: CursorPage<T>, pages: Array<CursorPage<T>>) {
  const maxPages = 100;
  assertCursorPageShape(lastPage);
  if (!lastPage.next || pages.length >= maxPages || lastPage.results.length === 0) return undefined;
  return lastPage.next;
}

export function getNextApiPageParam<T>(
  lastPage: ApiPage<T>,
  pages: Array<ApiPage<T>>,
  maxPages = DEFAULT_INFINITE_MAX_PAGES,
) {
  if (!Number.isSafeInteger(maxPages) || maxPages <= 0) {
    throw new TypeError('maxPages must be a positive safe integer');
  }
  assertPageShape(lastPage);

  if (!lastPage.next || pages.length >= maxPages || lastPage.results.length === 0) return undefined;
  const loadedCount = pages.reduce((total, page) => {
    assertPageShape(page);
    return total + page.results.length;
  }, 0);
  return loadedCount < lastPage.count ? pages.length + 1 : undefined;
}

export async function collectApiPages<T>(
  fetchPage: (query: Required<PageQuery>) => Promise<ApiPage<T>>,
  { pageSize, signal, maxPages = DEFAULT_MAX_PAGES, maxItems = DEFAULT_MAX_ITEMS }: CollectApiPagesOptions,
) {
  if (!Number.isSafeInteger(pageSize) || pageSize <= 0) {
    throw new TypeError('pageSize must be a positive safe integer');
  }
  if (!Number.isSafeInteger(maxPages) || maxPages <= 0) {
    throw new TypeError('maxPages must be a positive safe integer');
  }
  if (!Number.isSafeInteger(maxItems) || maxItems <= 0) {
    throw new TypeError('maxItems must be a positive safe integer');
  }

  const results: T[] = [];
  const nextLinks = new Set<string>();
  for (let page = 1; page <= maxPages; page += 1) {
    signal?.throwIfAborted();
    const response = await fetchPage({ page, page_size: pageSize });
    assertPageShape(response, pageSize);
    if (results.length + response.results.length > maxItems) {
      throw new Error(`Paginated API exceeded the ${maxItems}-item safety limit`);
    }
    results.push(...response.results);

    if (!response.next || results.length >= response.count) return results;
    if (response.results.length === 0) {
      throw new Error('Paginated API returned an empty page with a next link');
    }
    if (nextLinks.has(response.next)) {
      throw new Error('Paginated API returned a repeated next link');
    }
    nextLinks.add(response.next);
  }

  throw new Error(`Paginated API exceeded the ${maxPages}-page safety limit`);
}
