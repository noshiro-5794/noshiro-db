import { type SyntheticEvent, useEffect, useMemo, useState } from 'react';
import { Link } from '@tanstack/react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { MessageSquare } from 'lucide-react';
import { useAuth } from '@/entities/session';
import { invalidateCommunityTargetSummaries } from '../model/cache';
import { commentPageAfterLeafDeletion, optimisticCommentPageReaction } from '../model/comment-state';
import { buildCommentTree } from '../model/comment-tree';
import { communityMutations, communityQueries, communityQueryKeys } from '@/entities/community';
import { useI18n } from '@/shared/i18n';
import type { ApiPage, CommunityCommentSummary, CommunityTargetType } from '@/shared/api';
import { routes } from '@/shared/routing/paths';
import { Button } from '@/shared/ui/Button';
import { CheckboxField } from '@/shared/ui/Checkbox';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Pagination } from '@/shared/ui/Pagination';
import { Textarea } from '@/shared/ui/Textarea';
import { toast } from '@/shared/ui/toast';
import { CommentMutationDialogs } from './CommentMutationDialogs';
import { CommentThread } from './CommentThread';
import './activity-timeline.css';

const pageSize = 16;
const emptyComments: CommunityCommentSummary[] = [];

type CommunityCommentsSectionProps = {
  currentPage: number;
  targetType: Extract<CommunityTargetType, 'post' | 'review' | 'collection' | 'activity'>;
  targetId: number;
  locked?: boolean;
  onPageChange: (page: number) => void;
};

export function CommunityCommentsSection({
  currentPage,
  targetType,
  targetId,
  locked = false,
  onPageChange,
}: CommunityCommentsSectionProps) {
  const { t } = useI18n();
  const auth = useAuth();
  const queryClient = useQueryClient();
  const [comment, setComment] = useState('');
  const [commentSpoiler, setCommentSpoiler] = useState(false);
  const [replyTarget, setReplyTarget] = useState<CommunityCommentSummary | null>(null);
  const [reportTarget, setReportTarget] = useState<CommunityCommentSummary | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<CommunityCommentSummary | null>(null);
  const [editTarget, setEditTarget] = useState<CommunityCommentSummary | null>(null);
  const showMutationError = () => toast.error(t('common.requestFailed'));
  const commentQueryKey = communityQueryKeys.commentTarget(targetType, targetId);
  const commentsQuery = useQuery(
    communityQueries.comments({ target_type: targetType, target_id: targetId, page: currentPage, page_size: pageSize }),
  );
  const comments = commentsQuery.data?.results ?? emptyComments;
  const commentTree = useMemo(() => buildCommentTree(comments), [comments]);
  const totalPages = Math.max(1, Math.ceil((commentsQuery.data?.count ?? 0) / pageSize));
  const createCommentMutation = useMutation({
    ...communityMutations.createComment(),
    onError: showMutationError,
    onSuccess: async () => {
      const nextPage = Math.max(1, Math.ceil(((commentsQuery.data?.count ?? 0) + 1) / pageSize));
      setComment('');
      setCommentSpoiler(false);
      setReplyTarget(null);
      if (nextPage !== currentPage) onPageChange(nextPage);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: commentQueryKey }),
        invalidateCommunityTargetSummaries(queryClient),
      ]);
    },
  });
  const reactionMutation = useMutation({
    ...communityMutations.setReaction(),
    onMutate: async ({ active, target_id: commentId }) => {
      await queryClient.cancelQueries({ queryKey: commentQueryKey });
      const snapshots = queryClient.getQueriesData<ApiPage<CommunityCommentSummary>>({ queryKey: commentQueryKey });
      queryClient.setQueriesData<ApiPage<CommunityCommentSummary>>({ queryKey: commentQueryKey }, (page) =>
        page ? optimisticCommentPageReaction(page, commentId, active) : page,
      );
      return { snapshots };
    },
    onError: (_error, _variables, context) => {
      for (const [queryKey, page] of context?.snapshots ?? []) {
        if (page) queryClient.setQueryData(queryKey, page);
      }
      showMutationError();
    },
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: commentQueryKey });
    },
  });

  useEffect(() => {
    if (commentsQuery.isLoading || !window.location.hash.startsWith('#comment-')) return;
    const id = window.location.hash.slice(1);
    const element = document.getElementById(id);
    if (!element) return;
    element.scrollIntoView({ block: 'center' });
    element.classList.add('is-highlighted');
    const timer = window.setTimeout(() => {
      element.classList.remove('is-highlighted');
    }, 2200);
    return () => {
      window.clearTimeout(timer);
    };
  }, [commentsQuery.isLoading, comments]);

  function submitComment(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (createCommentMutation.isPending || !comment.trim()) return;
    createCommentMutation.mutate({
      target_type: targetType,
      target_id: targetId,
      ...(replyTarget ? { parent_id: replyTarget.id } : {}),
      content: comment,
      visibility: 'public',
      is_spoiler: commentSpoiler,
    });
  }

  function toggleCommentReaction(targetComment: CommunityCommentSummary) {
    reactionMutation.mutate({
      target_type: 'comment',
      target_id: targetComment.id,
      reaction_type: 'like',
      active: !targetComment.viewer_state?.has_liked,
    });
  }

  async function handleCommentDeleted(deletedComment: CommunityCommentSummary) {
    const nextPage = commentPageAfterLeafDeletion(currentPage, comments, deletedComment);
    if (nextPage !== currentPage) onPageChange(nextPage);
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: commentQueryKey }),
      invalidateCommunityTargetSummaries(queryClient),
    ]);
  }

  function replyTargetName(target: CommunityCommentSummary) {
    if (target.is_hidden) return t('community.deletedComment');
    return target.author?.nickname || t('common.anonymous');
  }

  return (
    <section className="timeline-comments">
      <div className="timeline-comments-header">
        <h2>{t('community.comments')}</h2>
        <span>{commentsQuery.data?.count ?? 0}</span>
      </div>

      {locked ? (
        <EmptyState title={t('community.postLockedTitle')} description={t('community.postLockedBody')} />
      ) : null}
      {!locked && auth.isAuthenticated ? (
        <form className="timeline-comment-form" onSubmit={submitComment}>
          {replyTarget ? (
            <div className="timeline-reply-pill">
              <span>
                {t('community.replyingTo')}{' '}
                <strong className="text-[var(--ui-text)]">{replyTargetName(replyTarget)}</strong>
              </span>
              <Button
                className="font-semibold text-[var(--ui-accent-text)]"
                variant="unstyled"
                onClick={() => {
                  setReplyTarget(null);
                }}
              >
                {t('community.cancelReply')}
              </Button>
            </div>
          ) : null}
          <Textarea
            aria-label={replyTarget ? t('community.replyPlaceholder') : t('community.commentPlaceholder')}
            className="timeline-comment-textarea"
            maxLength={5_000}
            value={comment}
            placeholder={replyTarget ? t('community.replyPlaceholder') : t('community.commentPlaceholder')}
            onChange={(event) => {
              setComment(event.target.value);
            }}
          />
          <div className="timeline-comment-form-footer">
            <CheckboxField checked={commentSpoiler} onCheckedChange={setCommentSpoiler}>
              {t('community.markSpoiler')}
            </CheckboxField>
            <Button disabled={createCommentMutation.isPending || !comment.trim()} type="submit">
              <MessageSquare className="size-4" /> {t('community.sendComment')}
            </Button>
          </div>
        </form>
      ) : null}
      {!locked && !auth.isAuthenticated ? (
        <EmptyState
          title={t('community.loginToCommentTitle')}
          description={t('community.loginToCommentBody')}
          action={
            <Button asChild size="sm" type="button" variant="secondary">
              <Link to={routes.login}>{t('auth.login')}</Link>
            </Button>
          }
        />
      ) : null}

      {commentsQuery.isLoading ? <LoadingState title={t('community.loadingComments')} /> : null}
      {commentsQuery.isError ? (
        <ErrorState title={t('community.commentsErrorTitle')} description={t('community.commentsErrorBody')} />
      ) : null}
      {!commentsQuery.isLoading && !commentsQuery.isError && comments.length === 0 ? (
        <EmptyState title={t('community.noCommentsTitle')} description={t('community.noCommentsBody')} />
      ) : null}
      <div className="timeline-comment-list">
        {commentTree.map((item) => (
          <CommentThread
            key={item.id}
            node={item}
            canInteract={auth.isAuthenticated}
            canReply={auth.isAuthenticated && !locked}
            currentUserId={auth.profile?.user_id}
            pending={reactionMutation.isPending}
            onDelete={setDeleteTarget}
            onEdit={setEditTarget}
            onLike={toggleCommentReaction}
            onReport={setReportTarget}
            onReply={setReplyTarget}
          />
        ))}
      </div>
      <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={onPageChange} />
      <CommentMutationDialogs
        deleteTarget={deleteTarget}
        editTarget={editTarget}
        reportTarget={reportTarget}
        targetId={targetId}
        targetType={targetType}
        onCloseDelete={() => {
          setDeleteTarget(null);
        }}
        onCloseEdit={() => {
          setEditTarget(null);
        }}
        onCloseReport={() => {
          setReportTarget(null);
        }}
        onDeleted={handleCommentDeleted}
      />
    </section>
  );
}
