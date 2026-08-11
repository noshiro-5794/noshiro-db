import { describe, expect, it } from 'vitest';
import { buildSubjectSearchQuery, usesSubjectDatabaseSearch } from './search-request';

describe('subject search request', () => {
  it('uses calendar browsing for display-only filters', () => {
    expect(usesSubjectDatabaseSearch({ subject_type: 'anime', ordering: 'title', nsfw: false })).toBe(false);
    expect(buildSubjectSearchQuery({ subject_type: 'anime', ordering: 'title', nsfw: false }, 30)).toEqual({
      subject_type: 'anime',
      ordering: 'title',
      nsfw: false,
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
      episodes_max: 24,
      episodes_min: 13,
      keyword: 'visual novel',
      nsfw: false,
      ordering: '-date',
      page: 3,
      page_size: 30,
      platform: 'PC',
      season: 'winter',
      source_id: '123',
      subject_type: 'galgame',
      year: 2025,
    });
  });

  it('maps open-ended episode ranges without inventing a maximum', () => {
    expect(buildSubjectSearchQuery({ episodes: 'long' }, 20)).toMatchObject({ episodes_min: 25 });
    expect(buildSubjectSearchQuery({ episodes: 'long' }, 20)).not.toHaveProperty('episodes_max');
  });
});
