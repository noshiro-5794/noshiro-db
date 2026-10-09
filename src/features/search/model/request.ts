import type { SearchPageSearch } from '@/shared/routing/route-search';

export function buildSubjectSearchQuery(search: SearchPageSearch, pageSize: number) {
  const keyword = search.keyword?.trim();
  return {
    ...(keyword ? { query: keyword } : {}),
    ...(search.subject_type === undefined ? {} : { subject_type: search.subject_type }),
    ...(search.nsfw === false ? { nsfw: false } : {}),
    // The catalogue is ranked by engagement unless the visitor picks another
    // order, so a blank search shows the works people actually care about.
    ordering: search.ordering ?? 'popular',
    page: search.page ?? 1,
    page_size: pageSize,
  };
}
