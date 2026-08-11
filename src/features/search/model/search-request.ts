import type { SubjectListQuery } from '@/entities/subject';
import type { SearchPageSearch } from '@/shared/routing/route-search';

const defaultOrdering = '-date';

function episodeRangeParams(range: SearchPageSearch['episodes']) {
  if (range === 'short') return { episodes_min: 1, episodes_max: 12 };
  if (range === 'standard') return { episodes_min: 13, episodes_max: 24 };
  if (range === 'long') return { episodes_min: 25 };
  return {};
}

export function usesSubjectDatabaseSearch(search: SearchPageSearch) {
  return Boolean(
    search.keyword?.trim() || search.source_id || search.year || search.season || search.platform || search.episodes,
  );
}

export function buildSubjectSearchQuery(search: SearchPageSearch, pageSize: number): SubjectListQuery {
  const keyword = search.keyword?.trim();
  return {
    ...(keyword ? { keyword } : {}),
    ...(search.source_id ? { source_id: search.source_id } : {}),
    ...(search.subject_type ? { subject_type: search.subject_type } : {}),
    ordering: search.ordering ?? defaultOrdering,
    ...(search.nsfw === false ? { nsfw: false } : {}),
    ...(search.year ? { year: search.year } : {}),
    ...(search.season ? { season: search.season } : {}),
    ...(search.platform ? { platform: search.platform } : {}),
    ...episodeRangeParams(search.episodes),
    page: search.page ?? 1,
    page_size: pageSize,
  };
}
