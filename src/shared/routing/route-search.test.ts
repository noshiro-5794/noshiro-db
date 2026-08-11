import { describe, expect, it } from 'vitest';
import {
  validateCollectionsSearch,
  validateLibrarySearch,
  validatePublicCollectionsSearch,
  validatePublicReviewsSearch,
  validatePublicSubjectsSearch,
  validateRootSearch,
  validateSearchPageSearch,
} from './route-search';

describe('route search contracts', () => {
  it('normalizes collection filters and rejects unbounded values', () => {
    expect(
      validateCollectionsSearch({ collection: '42', keyword: 'noshiro', ordering: '-item_count', page: '3' }),
    ).toEqual({ collection: 42, keyword: 'noshiro', ordering: '-item_count', page: 3 });
    expect(
      validateCollectionsSearch({ collection: '-1', keyword: '\u0000bad', ordering: 'random', page: '0' }),
    ).toEqual({
      collection: undefined,
      keyword: undefined,
      ordering: undefined,
      page: undefined,
    });
  });

  it('bounds typed library identifiers and filters', () => {
    expect(validateLibrarySearch({ status: 'done', subject_type: 'anime', tag_id: '7' })).toMatchObject({
      status: 'done',
      subject_type: 'anime',
      tag_id: 7,
    });
    expect(validateLibrarySearch({ status: 'unknown', subject_type: 'book', tag_id: 'NaN' })).toMatchObject({
      status: undefined,
      subject_type: undefined,
      tag_id: undefined,
    });
  });

  it('accepts only the explicit safe-search value and bounded years', () => {
    expect(validateSearchPageSearch({ nsfw: 'false', year: '2025' })).toMatchObject({ nsfw: false, year: 2025 });
    expect(validateSearchPageSearch({ nsfw: 'true', year: '9999' })).toMatchObject({
      nsfw: undefined,
      year: undefined,
    });
  });

  it('keeps comment pagination bounded at the shared root', () => {
    expect(validateRootSearch({ post_comments_page: '4', review_comments_page: '-2' })).toMatchObject({
      post_comments_page: 4,
      review_comments_page: undefined,
    });
  });

  it('only accepts status and subject type on public subject listings', () => {
    const raw = { status: 'done', subject_type: 'anime' };

    expect(validatePublicSubjectsSearch(raw)).toMatchObject(raw);
    expect(validatePublicReviewsSearch(raw)).not.toHaveProperty('status');
    expect(validatePublicReviewsSearch(raw)).not.toHaveProperty('subject_type');
    expect(validatePublicCollectionsSearch(raw)).not.toHaveProperty('status');
    expect(validatePublicCollectionsSearch(raw)).not.toHaveProperty('subject_type');
  });

  it('keeps public subject ordering within the backend contract', () => {
    expect(validatePublicSubjectsSearch({ ordering: '-id' })).toMatchObject({ ordering: '-id' });
    expect(validatePublicSubjectsSearch({ ordering: '-updated_at' }).ordering).toBeUndefined();
    expect(validateLibrarySearch({ ordering: '-updated_at' })).toMatchObject({ ordering: '-updated_at' });
  });
});
