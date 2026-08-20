import type { SearchPageSearch } from '@/shared/routing/route-search';

export function usesSubjectDatabaseSearch(search: SearchPageSearch) {
  return Boolean(search.keyword?.trim());
}

export function buildSubjectSearchQuery(search: SearchPageSearch, pageSize: number) {
  const keyword = search.keyword?.trim();
  return {
    ...(keyword ? { query: keyword } : {}),
    page: search.page ?? 1,
    page_size: pageSize,
  };
}
