import { describe, expect, it } from 'vitest';
import { buildSubjectSearchQuery, usesSubjectDatabaseSearch } from './search-request';

describe('subject search request', () => {
  it('uses calendar browsing for display-only filters', () => {
    expect(usesSubjectDatabaseSearch({ subject_type: 'anime', ordering: 'title', nsfw: false })).toBe(false);
    expect(buildSubjectSearchQuery({ subject_type: 'anime', ordering: 'title', nsfw: false }, 30)).toEqual({
      page: 1,
      page_size: 30,
    });
  });

  it('maps validated database filters to the API contract', () => {
    const search = {
      episodes: 'standard' as const,
      keyword: '  visual novel  ',
      nsfw: false as const,
      ordering: '-date' as const,
      page: 3,
      platform: 'PC' as const,
      season: 'winter' as const,
      source_id: '123',
      subject_type: 'galgame' as const,
      year: 2025,
    };

    expect(usesSubjectDatabaseSearch(search)).toBe(true);
    expect(buildSubjectSearchQuery(search, 30)).toEqual({
      query: 'visual novel',
      page: 3,
      page_size: 30,
    });
  });

  it('omits empty keyword queries', () => {
    expect(buildSubjectSearchQuery({ keyword: '  ' }, 20)).toEqual({ page: 1, page_size: 20 });
  });
});
