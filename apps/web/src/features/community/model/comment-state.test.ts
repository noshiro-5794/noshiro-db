import { describe, expect, it } from 'vitest';
import type { ApiPage, CommunityCommentSummary } from '@/shared/api';
import {
  commentPageAfterLeafDeletion,
  optimisticCommentPageReaction,
  optimisticCommentReaction,
} from './comment-state';

const comment: CommunityCommentSummary = {
  id: 1,
  content: 'Comment',
  visibility: 'public',
  is_spoiler: false,
  reaction_count: 2,
  viewer_state: { has_liked: false, is_following_author: false },
};

describe('optimistic comment reaction', () => {
  it('updates the count once and preserves unrelated viewer state', () => {
    const liked = optimisticCommentReaction(comment, true);

    expect(liked.reaction_count).toBe(3);
    expect(liked.viewer_state).toEqual({ has_liked: true, is_following_author: false });
    expect(optimisticCommentReaction(liked, true)).toBe(liked);
  });

  it('clamps reaction counts at zero', () => {
    const liked = { ...comment, reaction_count: 0, viewer_state: { has_liked: true, is_following_author: false } };
    expect(optimisticCommentReaction(liked, false).reaction_count).toBe(0);
  });

  it('updates a matching paginated comment without changing unrelated pages', () => {
    const page: ApiPage<CommunityCommentSummary> = {
      count: 1,
      next: null,
      previous: null,
      results: [comment],
    };

    const updated = optimisticCommentPageReaction(page, comment.id, true);

    expect(updated).not.toBe(page);
    expect(updated.results[0]?.reaction_count).toBe(3);
    expect(optimisticCommentPageReaction(page, 99, true)).toBe(page);
  });
});

describe('comment deletion pagination', () => {
  it('moves back when deleting the only leaf comment on a later page', () => {
    expect(commentPageAfterLeafDeletion(3, [comment], comment)).toBe(2);
  });

  it('keeps the page when the deleted comment has replies or siblings', () => {
    const reply = { ...comment, id: 2, parent_id: comment.id };
    expect(commentPageAfterLeafDeletion(3, [comment, reply], comment)).toBe(3);
    expect(commentPageAfterLeafDeletion(3, [{ ...comment, reply_count: 1 }], { ...comment, reply_count: 1 })).toBe(3);
    expect(commentPageAfterLeafDeletion(1, [comment], comment)).toBe(1);
  });
});
