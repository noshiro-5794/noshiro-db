import { describe, expect, it } from 'vitest';
import { buildSubjectSearchQuery } from './search-request';

describe('subject search request', () => {
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

    expect(buildSubjectSearchQuery(search, 30)).toEqual({
      query: 'visual novel',
      subject_type: 'galgame',
      nsfw: false,
      ordering: '-date',
      page: 3,
      page_size: 30,
    });
  });

  it('omits empty keyword queries and defaults to popularity', () => {
    expect(buildSubjectSearchQuery({ keyword: '  ' }, 20)).toEqual({
      ordering: 'popular',
      page: 1,
      page_size: 20,
    });
  });
});
