import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Flag, Heart, MessageSquare, PencilLine, ShieldAlert, Trash2 } from 'lucide-react';
import { useAuth } from '@/features/auth/use-auth';
import { invalidateCommunityTargets } from '@/features/community/cache';
import { communityMutations, communityQueries, communityQueryKeys } from '@/features/community/community-queries';
import { useI18n } from '@/features/i18n/use-i18n';
import type { CommunityCommentSummary, CommunityReportReason, CommunityTargetType } from '@/lib/api/types';
import { routes } from '@/routes/paths';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/shared/ui/Dialog';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Pagination } from '@/shared/ui/Pagination';

const pageSize = 16;
const reportReasons = ['spam', 'harassment', 'spoiler', 'illegal', 'other'] as const satisfies CommunityReportReason[];
const emptyComments: CommunityCommentSummary[] = [];

type CommentNode = CommunityCommentSummary & {
  children: CommentNode[];
};

type ReportTarget = {
  id: number;
  label: string;
};

type EditTarget = {
  id: number;
  content: string;
  is_spoiler: boolean;
};

type CommunityCommentsSectionProps = {
  targetType: Extract<CommunityTargetType, 'review' | 'collection' | 'activity'>;
  targetId: number;
  locked?: boolean;
};

function formatDate(value?: string) {
  if (!value) return '';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

function buildCommentTree(comments: CommunityCommentSummary[]) {
  const nodeMap = new Map<number, CommentNode>();
  const roots: CommentNode[] = [];

  comments.forEach((comment) => {
    nodeMap.set(comment.id, { ...comment, children: [] });
  });

  nodeMap.forEach((node) => {
    const parent = node.parent_id ? nodeMap.get(node.parent_id) : null;
    if (parent) parent.children.push(node);
    else roots.push(node);
  });

  return roots;
}

function CommentItem({
  comment,
  canInteract,
  canEdit,
  canReply,
  pending,
  onDelete,
  onEdit,
  onLike,
  onReport,
  onReply,
}: {
  comment: CommunityCommentSummary;
  canInteract: boolean;
  canEdit: boolean;
  canReply: boolean;
  pending: boolean;
  onDelete: (comment: CommunityCommentSummary) => void;
  onEdit: (comment: CommunityCommentSummary) => void;
  onLike: (comment: CommunityCommentSummary) => void;
  onReport: (comment: CommunityCommentSummary) => void;
  onReply: (comment: CommunityCommentSummary) => void;
}) {
  const { t } = useI18n();
  const isDeleted = Boolean(comment.is_hidden);

  return (
    <article className="community-comment-item scroll-mt-24" id={`comment-${comment.id}`}>
      {comment.author?.id && !isDeleted ? (
        <Link to={routes.userProfile(comment.author.id)}>
          <img className="size-9 rounded-full bg-neutral-100 object-cover transition hover:ring-2 hover:ring-[var(--color-accent-border)] dark:bg-neutral-900" src={comment.author.avatar || '/assets/placeholders/avatar.png'} alt="" />
        </Link>
      ) : (
        <img className="size-9 rounded-full bg-neutral-100 object-cover dark:bg-neutral-900" src="/assets/placeholders/avatar.png" alt="" />
      )}
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          {comment.author?.id && !isDeleted ? (
            <Link className="font-semibold text-neutral-950 transition hover:text-[var(--color-accent-strong)] dark:text-white" to={routes.userProfile(comment.author.id)}>
              {comment.author.nickname || t('common.anonymous')}
            </Link>
          ) : (
            <span className="font-semibold text-neutral-950 dark:text-white">{isDeleted ? t('community.deletedComment') : t('common.anonymous')}</span>
          )}
          <span className="text-neutral-400">{formatDate(comment.created_at)}</span>
          {comment.is_locked ? <Badge>{t('community.locked')}</Badge> : null}
          {comment.is_spoiler ? <Badge><ShieldAlert className="mr-1 size-3" /> {t('common.spoiler')}</Badge> : null}
        </div>
        <p className={`mt-2 whitespace-pre-wrap text-sm leading-6 ${isDeleted ? 'text-neutral-400 dark:text-neutral-500' : 'text-neutral-700 dark:text-neutral-300'} ${comment.is_spoiler && !isDeleted ? 'blur-sm transition hover:blur-none' : ''}`}>
          {isDeleted ? t('community.deletedCommentBody') : comment.content}
        </p>
        {canInteract && !isDeleted ? (
          <div className="mt-3 flex flex-wrap gap-2">
            <Button disabled={pending} size="sm" type="button" variant={comment.viewer_state?.has_liked ? 'accent' : 'ghost'} onClick={() => onLike(comment)}>
              <Heart className="size-4" /> {comment.reaction_count ?? 0}
            </Button>
            {canReply ? (
              <Button disabled={pending} size="sm" type="button" variant="ghost" onClick={() => onReply(comment)}>
                <MessageSquare className="size-4" /> {t('community.reply')}
              </Button>
            ) : null}
            <Button size="sm" type="button" variant="ghost" onClick={() => onReport(comment)}>
              <Flag className="size-4" /> {t('community.report')}
            </Button>
            {canEdit ? (
              <>
                <Button disabled={pending} size="sm" type="button" variant="ghost" onClick={() => onEdit(comment)}>
                  <PencilLine className="size-4" /> {t('common.edit')}
                </Button>
                <Button disabled={pending} size="sm" type="button" variant="ghost" onClick={() => onDelete(comment)}>
                  <Trash2 className="size-4" /> {t('common.delete')}
                </Button>
              </>
            ) : null}
          </div>
        ) : null}
      </div>
    </article>
  );
}

function CommentThread({
  node,
  canInteract,
  canReply,
  currentUserId,
  pending,
  onDelete,
  onEdit,
  onLike,
  onReport,
  onReply,
}: {
  node: CommentNode;
  canInteract: boolean;
  canReply: boolean;
  currentUserId?: string | number;
  pending: boolean;
  onDelete: (comment: CommunityCommentSummary) => void;
  onEdit: (comment: CommunityCommentSummary) => void;
  onLike: (comment: CommunityCommentSummary) => void;
  onReport: (comment: CommunityCommentSummary) => void;
  onReply: (comment: CommunityCommentSummary) => void;
}) {
  const isOwnComment = Boolean(node.author?.id && currentUserId && String(node.author.id) === String(currentUserId));

  return (
    <div className="border-b border-neutral-200 last:border-b-0 dark:border-neutral-800">
      <CommentItem
        comment={node}
        canEdit={isOwnComment && !node.is_hidden && !node.is_locked}
        canInteract={canInteract}
        canReply={canReply && !node.is_hidden && !node.is_locked}
        pending={pending}
        onDelete={onDelete}
        onEdit={onEdit}
        onLike={onLike}
        onReport={onReport}
        onReply={onReply}
      />
      {node.children.length > 0 ? (
        <div className="ml-8 border-l border-neutral-200 pl-3 dark:border-neutral-800 sm:ml-14">
          {node.children.map((child) => (
            <CommentThread
              key={child.id}
              node={child}
              canInteract={canInteract}
              canReply={canReply}
              currentUserId={currentUserId}
              pending={pending}
              onDelete={onDelete}
              onEdit={onEdit}
              onLike={onLike}
              onReport={onReport}
              onReply={onReply}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function CommunityCommentsSection({ targetType, targetId, locked = false }: CommunityCommentsSectionProps) {
  const { t } = useI18n();
  const auth = useAuth();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const currentPage = Math.max(1, Number(searchParams.get(`${targetType}_comments_page`) ?? '1') || 1);
  const [comment, setComment] = useState('');
  const [commentSpoiler, setCommentSpoiler] = useState(false);
  const [replyTarget, setReplyTarget] = useState<CommunityCommentSummary | null>(null);
  const [reportTarget, setReportTarget] = useState<ReportTarget | null>(null);
  const [reportReason, setReportReason] = useState<CommunityReportReason>('spam');
  const [reportDescription, setReportDescription] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<CommunityCommentSummary | null>(null);
  const [editTarget, setEditTarget] = useState<EditTarget | null>(null);
  const commentsQuery = useQuery(communityQueries.comments({ target_type: targetType, target_id: targetId, page: currentPage, page_size: pageSize }));
  const comments = commentsQuery.data?.results ?? emptyComments;
  const commentTree = useMemo(() => buildCommentTree(comments), [comments]);
  const totalPages = Math.max(1, Math.ceil((commentsQuery.data?.count ?? 0) / pageSize));
  const createCommentMutation = useMutation({
    ...communityMutations.createComment(),
    onSuccess: async () => {
      setComment('');
      setCommentSpoiler(false);
      setReplyTarget(null);
      await invalidateComments();
    },
  });
  const updateCommentMutation = useMutation({ ...communityMutations.updateComment(), onSuccess: async () => { setEditTarget(null); await invalidateComments(); } });
  const deleteCommentMutation = useMutation({ ...communityMutations.deleteComment(), onSuccess: async () => { setDeleteTarget(null); await invalidateComments(); } });
  const reactMutation = useMutation({ ...communityMutations.react(), onSuccess: () => invalidateComments() });
  const unreactMutation = useMutation({ ...communityMutations.unreact(), onSuccess: () => invalidateComments() });
  const reportMutation = useMutation({
    ...communityMutations.createReport(),
    onSuccess: async () => {
      setReportTarget(null);
      setReportReason('spam');
      setReportDescription('');
      await invalidateComments();
    },
  });
  const pending = createCommentMutation.isPending || updateCommentMutation.isPending || deleteCommentMutation.isPending || reactMutation.isPending || unreactMutation.isPending;

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
    return () => window.clearTimeout(timer);
  }, [commentsQuery.isLoading, comments]);

  async function invalidateComments() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: communityQueryKeys.comments() }),
      invalidateCommunityTargets(queryClient),
    ]);
  }

  function goToPage(page: number) {
    const next = new URLSearchParams(searchParams);
    next.set(`${targetType}_comments_page`, String(page));
    setSearchParams(next);
  }

  function submitComment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!comment.trim()) return;
    createCommentMutation.mutate({
      target_type: targetType,
      target_id: targetId,
      parent_id: replyTarget?.id,
      content: comment,
      visibility: 'public',
      is_spoiler: commentSpoiler,
    });
  }

  function toggleCommentReaction(targetComment: CommunityCommentSummary) {
    const body = { target_type: 'comment' as const, target_id: targetComment.id, reaction_type: 'like' as const };
    if (targetComment.viewer_state?.has_liked) unreactMutation.mutate(body);
    else reactMutation.mutate(body);
  }

  function submitReport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!reportTarget) return;
    reportMutation.mutate({
      target_type: 'comment',
      target_id: reportTarget.id,
      reason: reportReason,
      description: reportDescription,
    });
  }

  function submitEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editTarget || !editTarget.content.trim()) return;
    updateCommentMutation.mutate({
      commentId: editTarget.id,
      body: {
        content: editTarget.content,
        is_spoiler: editTarget.is_spoiler,
      },
    });
  }

  function replyTargetName(target: CommunityCommentSummary) {
    if (target.is_hidden) return t('community.deletedComment');
    return target.author?.nickname || t('common.anonymous');
  }

  return (
    <section className="grid gap-3">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold tracking-tight text-neutral-950 dark:text-white">{t('community.comments')}</h2>
        <span className="text-sm text-neutral-500 dark:text-neutral-400">{commentsQuery.data?.count ?? 0}</span>
      </div>

      {locked ? <EmptyState title={t('community.postLockedTitle')} description={t('community.postLockedBody')} /> : null}
      {!locked && auth.isAuthenticated ? (
        <form className="grid gap-3 rounded-lg border border-neutral-200 bg-white p-3 dark:border-neutral-800 dark:bg-neutral-950" onSubmit={submitComment}>
          {replyTarget ? (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-neutral-50 px-3 py-2 text-sm text-neutral-500 dark:bg-neutral-900 dark:text-neutral-400">
              <span>{t('community.replyingTo')} <strong className="text-neutral-950 dark:text-white">{replyTargetName(replyTarget)}</strong></span>
              <button className="font-semibold text-[var(--color-accent-strong)]" type="button" onClick={() => setReplyTarget(null)}>
                {t('community.cancelReply')}
              </button>
            </div>
          ) : null}
          <textarea
            className="min-h-28 resize-y rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm leading-6 outline-none transition placeholder:text-neutral-400 focus:border-[var(--color-accent-border)] dark:border-neutral-800 dark:bg-neutral-900"
            value={comment}
            placeholder={replyTarget ? t('community.replyPlaceholder') : t('community.commentPlaceholder')}
            onChange={(event) => setComment(event.target.value)}
          />
          <div className="flex flex-wrap items-center justify-between gap-3">
            <label className="inline-flex items-center gap-2 text-sm text-neutral-500 dark:text-neutral-400">
              <input checked={commentSpoiler} className="size-4 accent-[var(--color-accent)]" type="checkbox" onChange={(event) => setCommentSpoiler(event.target.checked)} />
              {t('community.markSpoiler')}
            </label>
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
          action={<Button asChild size="sm" type="button" variant="secondary"><Link to={routes.login}>{t('auth.login')}</Link></Button>}
        />
      ) : null}

      {commentsQuery.isLoading ? <LoadingState title={t('community.loadingComments')} /> : null}
      {commentsQuery.isError ? <ErrorState title={t('community.commentsErrorTitle')} description={t('community.commentsErrorBody')} /> : null}
      {!commentsQuery.isLoading && !commentsQuery.isError && comments.length === 0 ? (
        <EmptyState title={t('community.noCommentsTitle')} description={t('community.noCommentsBody')} />
      ) : null}
      <div className="community-comment-list">
        {commentTree.map((item) => (
          <CommentThread
            key={item.id}
            node={item}
            canInteract={auth.isAuthenticated}
            canReply={auth.isAuthenticated && !locked}
            currentUserId={auth.profile?.user_id}
            pending={pending}
            onDelete={setDeleteTarget}
            onEdit={(targetComment) => setEditTarget({ id: targetComment.id, content: targetComment.content, is_spoiler: targetComment.is_spoiler })}
            onLike={toggleCommentReaction}
            onReport={(targetComment) => {
              setReportTarget({ id: targetComment.id, label: t('community.reportComment') });
              setReportReason('spam');
              setReportDescription('');
            }}
            onReply={setReplyTarget}
          />
        ))}
      </div>
      <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={goToPage} />

      <Dialog open={Boolean(deleteTarget)} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('community.deleteCommentTitle')}</DialogTitle>
            <DialogDescription>{t('community.deleteCommentBody')}</DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setDeleteTarget(null)}>{t('common.cancel')}</Button>
            <Button disabled={deleteCommentMutation.isPending} type="button" onClick={() => deleteTarget && deleteCommentMutation.mutate(deleteTarget.id)}>
              <Trash2 className="size-4" /> {t('common.delete')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(editTarget)} onOpenChange={(open) => !open && setEditTarget(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{t('community.editCommentTitle')}</DialogTitle>
            <DialogDescription>{t('community.editCommentDescription')}</DialogDescription>
          </DialogHeader>
          <form className="grid gap-4" onSubmit={submitEdit}>
            <textarea
              className="min-h-40 resize-y rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm leading-6 outline-none transition placeholder:text-neutral-400 focus:border-[var(--color-accent-border)] dark:border-neutral-800 dark:bg-neutral-900"
              value={editTarget?.content ?? ''}
              placeholder={t('community.commentPlaceholder')}
              onChange={(event) => setEditTarget((current) => current ? { ...current, content: event.target.value } : current)}
            />
            <label className="inline-flex items-center gap-2 text-sm text-neutral-500 dark:text-neutral-400">
              <input checked={Boolean(editTarget?.is_spoiler)} className="size-4 accent-[var(--color-accent)]" type="checkbox" onChange={(event) => setEditTarget((current) => current ? { ...current, is_spoiler: event.target.checked } : current)} />
              {t('community.markSpoiler')}
            </label>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setEditTarget(null)}>{t('common.cancel')}</Button>
              <Button disabled={updateCommentMutation.isPending || !editTarget?.content.trim()} type="submit">
                <PencilLine className="size-4" /> {t('common.save')}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(reportTarget)} onOpenChange={(open) => !open && setReportTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('community.reportTitle')}</DialogTitle>
            <DialogDescription>{reportTarget?.label || t('community.reportDescription')}</DialogDescription>
          </DialogHeader>
          <form className="grid gap-4" onSubmit={submitReport}>
            <div className="grid gap-2">
              <span className="text-sm font-semibold text-neutral-950 dark:text-white">{t('community.reportReason')}</span>
              <div className="flex flex-wrap gap-2">
                {reportReasons.map((reason) => (
                  <button
                    className={[
                      'rounded-full border px-3 py-1.5 text-sm font-semibold transition',
                      reportReason === reason
                        ? 'border-[var(--color-accent-border)] bg-[var(--color-accent-soft)] text-[var(--color-accent-strong)]'
                        : 'border-neutral-200 text-neutral-500 hover:border-neutral-300 dark:border-neutral-800 dark:text-neutral-400',
                    ].join(' ')}
                    key={reason}
                    type="button"
                    onClick={() => setReportReason(reason)}
                  >
                    {t(`community.reportReason.${reason}`)}
                  </button>
                ))}
              </div>
            </div>
            <textarea
              className="min-h-28 resize-y rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm leading-6 outline-none transition placeholder:text-neutral-400 focus:border-[var(--color-accent-border)] dark:border-neutral-800 dark:bg-neutral-900"
              value={reportDescription}
              placeholder={t('community.reportPlaceholder')}
              onChange={(event) => setReportDescription(event.target.value)}
            />
            <div className="flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setReportTarget(null)}>{t('common.cancel')}</Button>
              <Button disabled={reportMutation.isPending} type="submit"><Flag className="size-4" /> {t('community.submitReport')}</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </section>
  );
}
