import { describe, expect, it } from 'vitest';
import type { UserSubjectContext } from '@/shared/api';
import { createMarkDraft, parseMarkDraft } from './mark-draft';

const emptyContext: UserSubjectContext = {
  is_marked: false,
  user_subject: null,
  tags: [],
  rating_details: [],
  reviews: [],
  progress: { finished_count: 0, finished_episode_ids: [] },
};

describe('mark draft', () => {
  it('creates a stable empty draft and sends null when ratings are cleared', () => {
    const draft = createMarkDraft(emptyContext);
    expect(parseMarkDraft(draft)).toMatchObject({
      body: { status: 'wish', simple_rating: null, rating: null, comment: '', is_public: true },
      ratingDetails: [],
      tagNames: [],
    });
  });

  it('normalizes duplicate tags and valid decimal details', () => {
    const parsed = parseMarkDraft({
      ...createMarkDraft(emptyContext),
      rating: '10.0',
      tagText: 'favorite, favorite, rewatch',
      ratingDetails: [{ key: 'Music', value: '8.5' }],
    });

    expect(parsed).toMatchObject({
      body: { rating: '10.0' },
      tagNames: ['favorite', 'rewatch'],
      ratingDetails: [{ key: 'Music', value: '8.5' }],
    });
  });

  it('rejects malformed values, duplicate detail keys, and oversized user input', () => {
    const base = createMarkDraft(emptyContext);
    expect(parseMarkDraft({ ...base, rating: '10.1' })).toBeNull();
    expect(parseMarkDraft({ ...base, comment: 'x'.repeat(2_001) })).toBeNull();
    expect(parseMarkDraft({ ...base, tagText: 'x'.repeat(65) })).toBeNull();
    expect(
      parseMarkDraft({
        ...base,
        ratingDetails: [
          { key: 'Music', value: '8' },
          { key: 'Music', value: '9' },
        ],
      }),
    ).toBeNull();
  });
});
