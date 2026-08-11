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

const subject = {
  id: '01980f00-0000-7000-8000-000000000001',
  title: 'Subject',
  title_cn: null,
  subject_type: 'anime',
  date: null,
  platform: null,
  nsfw: false,
};

const userSubject = {
  id: 1,
  status: 'doing',
  simple_rating: null,
  rating: null,
  comment: '',
  watch_start_date: null,
  watch_end_date: null,
  is_public: true,
  subject,
};

const progress = { finished_count: 1, finished_episode_ids: [10] };
const review = { id: 2, title: 'Review', content: 'Body', is_public: true, is_spoiler: false };

describe('library response decoders', () => {
  it('accepts both compact context progress and the full progress response', () => {
    expect(decodeProgressSummary(progress)).toEqual(progress);
    expect(
      decodeProgressSummary({
        ...progress,
        subject_id: subject.id,
        user_subject_id: 1,
        total_episodes: 12,
        episodes: [{ id: 10, title: 'Episode', type: 'EP', ep_num: 1, sort: 1, date: null, is_finished: true }],
      }),
    ).toMatchObject({ total_episodes: 12 });
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

    expect(decodeUserSubjectContext(context)).toEqual(context);
    expect(() => decodeUserSubjectContext({ ...context, tags: [{ id: '1', name: 'favorite' }] })).toThrow(TypeError);
  });

  it('accepts the compact nested subject used by review endpoints', () => {
    expect(decodeReview({ ...review, subject: { ...subject, platform: undefined } })).toMatchObject({ id: 2 });
    expect(() => decodeReview({ ...review, viewer_state: { has_liked: 'yes', has_bookmarked: false } })).toThrow(
      TypeError,
    );
  });

  it('rejects invalid collection counters and ratings', () => {
    const collection = { id: 3, name: 'List', simple_rating: 5, note: '', is_public: true, item_count: 2 };
    expect(decodeCollection(collection)).toEqual(collection);
    expect(() => decodeCollection({ ...collection, item_count: -1 })).toThrow(TypeError);
    expect(() => decodeCollection({ ...collection, simple_rating: '5' })).toThrow(TypeError);
  });

  it('normalizes visibility omitted by public-only endpoints', () => {
    const publicUserSubject = {
      id: userSubject.id,
      status: userSubject.status,
      simple_rating: userSubject.simple_rating,
      rating: userSubject.rating,
      comment: userSubject.comment,
      watch_start_date: userSubject.watch_start_date,
      watch_end_date: userSubject.watch_end_date,
      subject: userSubject.subject,
    };
    const publicReview = {
      id: review.id,
      title: review.title,
      content: review.content,
      is_spoiler: review.is_spoiler,
    };
    const publicCollection = { id: 3, name: 'List', simple_rating: null, note: '', item_count: 2 };

    expect(decodePublicUserSubject(publicUserSubject).is_public).toBe(true);
    expect(decodePublicReview(publicReview).is_public).toBe(true);
    expect(decodePublicCollection(publicCollection).is_public).toBe(true);
  });
});
