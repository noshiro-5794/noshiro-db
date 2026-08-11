import type { ApiPage, CommunityCommentSummary } from '@/shared/api';

export function optimisticCommentReaction(comment: CommunityCommentSummary, shouldLike: boolean) {
  const wasLiked = Boolean(comment.viewer_state?.has_liked);
  if (wasLiked === shouldLike) return comment;

  return {
    ...comment,
    reaction_count: Math.max(0, (comment.reaction_count ?? 0) + (shouldLike ? 1 : -1)),
    viewer_state: {
      has_liked: shouldLike,
      is_following_author: comment.viewer_state?.is_following_author ?? false,
    },
  };
}

export function optimisticCommentPageReaction(
  page: ApiPage<CommunityCommentSummary>,
  commentId: number,
  shouldLike: boolean,
) {
  const comment = page.results.find((candidate) => candidate.id === commentId);
  if (!comment) return page;

  const updatedComment = optimisticCommentReaction(comment, shouldLike);
  if (updatedComment === comment) return page;

  return {
    ...page,
    results: page.results.map((candidate) => (candidate.id === commentId ? updatedComment : candidate)),
  };
}

export function commentPageAfterLeafDeletion(
  currentPage: number,
  pageComments: readonly CommunityCommentSummary[],
  deletedComment: CommunityCommentSummary,
) {
  const hasReplies =
    (deletedComment.reply_count ?? 0) > 0 || pageComments.some((comment) => comment.parent_id === deletedComment.id);

  return currentPage > 1 && pageComments.length === 1 && !hasReplies ? currentPage - 1 : currentPage;
}
