import { describe, expect, it } from 'vitest';
import {
  decodeCollection,
  decodeProgressSummary,
  decodePublicCollection,
  decodePublicReview,
  decodePublicUserSubject,
  decodeReview,
  decodeUserSubjectContext,
} from './library';

const entity = {
  id: '01980f00-0000-7000-8000-000000000001',
  entity_type: 'work',
  lifecycle: 'active',
  audience: 'general',
  work_type: 'anime',
  display_name: 'Subject',
  collections: [],
  media: [],
};

const userSubject = {
  id: 1,
  entity,
  status: 'doing',
  simple_rating: null,
  rating: null,
  comment: '',
  watch_start_date: null,
  watch_end_date: null,
  is_public: true,
  releases: [],
  created_at: '2026-07-29T00:00:00Z',
  updated_at: '2026-07-29T00:00:00Z',
};

const progress = {
  library_entry_id: 1,
  entity_id: entity.id,
  total_episodes: 0,
  finished_count: 1,
  finished_episode_ids: ['1'],
  episodes: [],
};

const review = {
  id: 2,
  title: 'Review',
  content: 'Body',
  is_public: true,
  is_spoiler: false,
  reaction_count: 0,
  created_at: '2026-07-29T00:00:00Z',
  updated_at: '2026-07-29T00:00:00Z',
  entity,
  library_entry_id: 1,
  user: { id: 3, nickname: 'User', avatar: null },
  viewer_state: { has_liked: false, has_bookmarked: false },
};

describe('library response decoders', () => {
  it('accepts full progress responses', () => {
    expect(decodeProgressSummary(progress)).toMatchObject({ finished_count: 1 });
    expect(
      decodeProgressSummary({
        ...progress,
        episodes: [
          { id: '1', title: 'Episode', title_cn: '', type: 'EP', number: '1', sort: '1', air_date: '', is_finished: true },
        ],
      }),
    ).toMatchObject({ total_episodes: 0 });
  });

  it('validates nested mark context records', () => {
    const context = {
      is_marked: true,
      user_subject: userSubject,
      tags: [{ id: 1, name: 'favorite' }],
      rating_details: [{ key: 'Music', value: '9.0' }],
      reviews: [review],
      progress,
    };

    expect(decodeUserSubjectContext(context)).toMatchObject({ is_marked: true });
    expect(() => decodeUserSubjectContext({ ...context, tags: [{ id: '1', name: 'favorite' }] })).toThrow(TypeError);
  });

  it('accepts review responses and validates viewer state', () => {
    expect(decodeReview(review)).toMatchObject({ id: 2 });
    expect(() => decodeReview({ ...review, viewer_state: { has_liked: 'yes', has_bookmarked: false } })).toThrow(
      TypeError,
    );
  });

  it('rejects invalid collection counters and ratings', () => {
    const collection = { id: 3, name: 'List', simple_rating: 5, note: '', is_public: true, item_count: 2 };
    expect(decodeCollection(collection)).toEqual(collection);
    expect(() => decodeCollection({ ...collection, simple_rating: '5' })).toThrow(TypeError);
  });

  it('normalizes public-only endpoint records', () => {
    expect(decodePublicUserSubject(userSubject).is_public).toBe(true);
    expect(decodePublicReview(review).is_public).toBe(true);
    expect(
      decodePublicCollection({ id: 3, name: 'List', simple_rating: null, note: '', is_public: true }).is_public,
    ).toBe(true);
  });
});
