import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from '@/shared/routing/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bookmark, Flag, Heart, MessageSquare, PencilLine, ShieldAlert, Trash2, UserPlus } from 'lucide-react';
import { useAuth } from '@/entities/session';
import { invalidateCommunityFollows, invalidateCommunityTargets } from '@/features/community';
import { communityMutations, communityQueries, communityQueryKeys } from '@/entities/community';
import { useI18n } from '@/shared/i18n';
import type {
  CommunityCommentSummary,
  CommunityPostSummary,
  CommunityReportReason,
  CommunityTargetType,
} from '@/shared/api';
import { routes } from '@/shared/routing/paths';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/shared/ui/Dialog';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';
import { Pagination } from '@/shared/ui/Pagination';

const commentsPageSize = 16;
const reportReasons = ['spam', 'harassment', 'spoiler', 'illegal', 'other'] as const satisfies CommunityReportReason[];
const emptyComments: CommunityCommentSummary[] = [];

type ReportTarget = {
  type: CommunityTargetType;
  id: number;
  label: string;
};

type DeleteTarget = {
  type: 'post' | 'comment';
  id: number;
};

type EditTarget =
  | {
      type: 'post';
      id: number;
      content: string;
      is_spoiler: boolean;
      is_nsfw: boolean;
    }
  | {
      type: 'comment';
      id: number;
      content: string;
      is_spoiler: boolean;
    };

type CommentNode = CommunityCommentSummary & {
  children: CommentNode[];
};

function formatDate(value?: string) {
  if (!value) return '';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

function subjectTitle(post: CommunityPostSummary) {
  return post.subject?.title || post.subject?.title_cn || '';
}

function useCommunityInvalidation(postId: number) {
  const queryClient = useQueryClient();

  return async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: communityQueryKeys.postDetail(postId) }),
      queryClient.invalidateQueries({ queryKey: communityQueryKeys.posts() }),
      queryClient.invalidateQueries({ queryKey: communityQueryKeys.comments() }),
      invalidateCommunityTargets(queryClient),
    ]);
  };
}

function PostSubjectCard({ post }: { post: CommunityPostSummary }) {
  if (!post.subject) return null;

  return (
    <Link
      className="mt-4 grid grid-cols-[56px_minmax(0,1fr)] gap-3 rounded-lg border border-neutral-200 p-3 transition hover:border-[var(--color-accent-border)] dark:border-neutral-800"
      to={routes.subject(post.subject.id)}
    >
      <img
        className="h-20 w-14 rounded-md bg-neutral-100 object-cover dark:bg-neutral-900"
        src={post.subject.image_thumbnail || '/assets/placeholders/subject-cover.png'}
        alt=""
      />
      <span className="min-w-0 self-center">
        <span className="block truncate text-sm font-semibold text-neutral-950 dark:text-white">
          {subjectTitle(post)}
        </span>
        <span className="mt-1 block text-xs text-neutral-500 dark:text-neutral-400">{post.subject.subject_type}</span>
        {post.subject.nsfw ? <Badge className="mt-2">NSFW</Badge> : null}
      </span>
    </Link>
  );
}

function PostBody({ post }: { post: CommunityPostSummary }) {
  const { t } = useI18n();

  return (
    <article className="community-post-reader">
      <div className="flex min-w-0 items-start gap-3">
        {post.author?.id ? (
          <Link to={routes.userProfile(post.author.id)}>
            <img
              className="size-11 rounded-full bg-neutral-100 object-cover transition hover:ring-2 hover:ring-[var(--color-accent-border)] dark:bg-neutral-900"
              src={post.author.avatar || '/assets/placeholders/avatar.png'}
              alt=""
            />
          </Link>
        ) : (
          <img
            className="size-11 rounded-full bg-neutral-100 object-cover dark:bg-neutral-900"
            src="/assets/placeholders/avatar.png"
            alt=""
          />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            {post.author?.id ? (
              <Link
                className="font-semibold text-neutral-950 transition hover:text-[var(--color-accent-strong)] dark:text-white"
                to={routes.userProfile(post.author.id)}
              >
                {post.author.nickname || t('common.anonymous')}
              </Link>
            ) : (
              <span className="font-semibold text-neutral-950 dark:text-white">{t('common.anonymous')}</span>
            )}
            <span className="text-neutral-400">{formatDate(post.created_at)}</span>
            {post.is_pinned ? <Badge variant="accent">{t('community.pinned')}</Badge> : null}
            {post.is_locked ? <Badge>{t('community.locked')}</Badge> : null}
          </div>
          <p
            className={`mt-3 whitespace-pre-wrap text-[0.95rem] leading-7 text-neutral-700 dark:text-neutral-300 ${post.is_spoiler ? 'blur-sm transition hover:blur-none' : ''}`}
          >
            {post.content}
          </p>
          <PostSubjectCard post={post} />
          <div className="mt-4 flex flex-wrap gap-2">
            <Badge variant="secondary">
              <Heart className="mr-1 size-3" /> {post.reaction_count ?? 0}
            </Badge>
            <Badge variant="secondary">
              <MessageSquare className="mr-1 size-3" /> {post.reply_count ?? 0}
            </Badge>
            {post.is_nsfw ? <Badge>NSFW</Badge> : null}
            {post.is_spoiler ? (
              <Badge>
                <ShieldAlert className="mr-1 size-3" /> {t('common.spoiler')}
              </Badge>
            ) : null}
          </div>
        </div>
      </div>
    </article>
  );
}

function buildCommentTree(comments: CommunityCommentSummary[]) {
  const nodeMap = new Map<number, CommentNode>();
  const roots: CommentNode[] = [];

  comments.forEach((comment) => {
    nodeMap.set(comment.id, { ...comment, children: [] });
  });

  nodeMap.forEach((node) => {
    const parentId = node.parent_id;
    const parent = parentId ? nodeMap.get(parentId) : null;
    if (parent) {
      parent.children.push(node);
    } else {
      roots.push(node);
    }
  });

  return roots;
}

function CommentItem({
  comment,
  onLike,
  onReport,
  onDelete,
  onEdit,
  onReply,
  pending,
  canDelete,
  canEdit,
  canReply,
}: {
  comment: CommunityCommentSummary;
  onLike: (comment: CommunityCommentSummary) => void;
  onReport: (comment: CommunityCommentSummary) => void;
  onDelete: (comment: CommunityCommentSummary) => void;
  onEdit: (comment: CommunityCommentSummary) => void;
  onReply: (comment: CommunityCommentSummary) => void;
  pending: boolean;
  canDelete: boolean;
  canEdit: boolean;
  canReply: boolean;
}) {
  const { t } = useI18n();
  const isDeleted = Boolean(comment.is_hidden);

  return (
    <article className="community-comment-item scroll-mt-24" id={`comment-${comment.id}`}>
      {comment.author?.id && !isDeleted ? (
        <Link to={routes.userProfile(comment.author.id)}>
          <img
            className="size-9 rounded-full bg-neutral-100 object-cover transition hover:ring-2 hover:ring-[var(--color-accent-border)] dark:bg-neutral-900"
            src={comment.author.avatar || '/assets/placeholders/avatar.png'}
            alt=""
          />
        </Link>
      ) : (
        <img
          className="size-9 rounded-full bg-neutral-100 object-cover dark:bg-neutral-900"
          src="/assets/placeholders/avatar.png"
          alt=""
        />
      )}
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          {comment.author?.id && !isDeleted ? (
            <Link
              className="font-semibold text-neutral-950 transition hover:text-[var(--color-accent-strong)] dark:text-white"
              to={routes.userProfile(comment.author.id)}
            >
              {comment.author.nickname || t('common.anonymous')}
            </Link>
          ) : (
            <span className="font-semibold text-neutral-950 dark:text-white">
              {isDeleted ? t('community.deletedComment') : t('common.anonymous')}
            </span>
          )}
          <span className="text-neutral-400">{formatDate(comment.created_at)}</span>
          {comment.is_locked ? <Badge>{t('community.locked')}</Badge> : null}
          {comment.is_spoiler ? (
            <Badge>
              <ShieldAlert className="mr-1 size-3" /> {t('common.spoiler')}
            </Badge>
          ) : null}
        </div>
        <p
          className={`mt-2 whitespace-pre-wrap text-sm leading-6 ${isDeleted ? 'text-neutral-400 dark:text-neutral-500' : 'text-neutral-700 dark:text-neutral-300'} ${comment.is_spoiler && !isDeleted ? 'blur-sm transition hover:blur-none' : ''}`}
        >
          {isDeleted ? t('community.deletedCommentBody') : comment.content}
        </p>
        {!isDeleted ? (
          <div className="community-action-bar mt-3">
            <Button
              className={`community-action-button ${comment.viewer_state?.has_liked ? 'is-active' : ''}`}
              disabled={pending}
              size="sm"
              type="button"
              variant="ghost"
              onClick={() => onLike(comment)}
            >
              <Heart className="size-4" /> {comment.reaction_count ?? 0}
            </Button>
            {canReply ? (
              <Button
                className="community-action-button"
                disabled={pending}
                size="sm"
                type="button"
                variant="ghost"
                onClick={() => onReply(comment)}
              >
                <MessageSquare className="size-4" /> {t('community.reply')}
              </Button>
            ) : null}
            <Button
              className="community-action-button"
              size="sm"
              type="button"
              variant="ghost"
              onClick={() => onReport(comment)}
            >
              <Flag className="size-4" /> {t('community.report')}
            </Button>
            {canEdit ? (
              <Button
                className="community-action-button"
                disabled={pending}
                size="sm"
                type="button"
                variant="ghost"
                onClick={() => onEdit(comment)}
              >
                <PencilLine className="size-4" /> {t('common.edit')}
              </Button>
            ) : null}
            {canDelete ? (
              <Button
                className="community-action-button"
                disabled={pending}
                size="sm"
                type="button"
                variant="ghost"
                onClick={() => onDelete(comment)}
              >
                <Trash2 className="size-4" /> {t('common.delete')}
              </Button>
            ) : null}
          </div>
        ) : null}
      </div>
    </article>
  );
}

function CommentThread({
  node,
  pending,
  canReply,
  currentUserId,
  onLike,
  onReport,
  onDelete,
  onEdit,
  onReply,
}: {
  node: CommentNode;
  pending: boolean;
  canReply: boolean;
  currentUserId?: string | number;
  onLike: (comment: CommunityCommentSummary) => void;
  onReport: (comment: CommunityCommentSummary) => void;
  onDelete: (comment: CommunityCommentSummary) => void;
  onEdit: (comment: CommunityCommentSummary) => void;
  onReply: (comment: CommunityCommentSummary) => void;
}) {
  const isOwnComment = Boolean(node.author?.id && currentUserId && String(node.author.id) === String(currentUserId));

  return (
    <div className="border-b border-neutral-200 last:border-b-0 dark:border-neutral-800">
      <CommentItem
        comment={node}
        canDelete={isOwnComment}
        canEdit={isOwnComment && !node.is_hidden && !node.is_locked}
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

export function CommunityPostPage() {
  const { t } = useI18n();
  const auth = useAuth();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const params = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const postId = Number(params.postId);
  const currentPage = Math.max(1, Number(searchParams.get('comments_page') ?? '1') || 1);
  const [comment, setComment] = useState('');
  const [commentSpoiler, setCommentSpoiler] = useState(false);
  const [replyTarget, setReplyTarget] = useState<CommunityCommentSummary | null>(null);
  const [reportTarget, setReportTarget] = useState<ReportTarget | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget | null>(null);
  const [editTarget, setEditTarget] = useState<EditTarget | null>(null);
  const [reportReason, setReportReason] = useState<CommunityReportReason>('spam');
  const [reportDescription, setReportDescription] = useState('');
  const invalidateCommunity = useCommunityInvalidation(postId);

  const postQuery = useQuery({ ...communityQueries.post(postId), enabled: Number.isFinite(postId) && postId > 0 });
  const commentsQuery = useQuery({
    ...communityQueries.postComments(postId, { page: currentPage, page_size: commentsPageSize }),
    enabled: Number.isFinite(postId) && postId > 0,
  });

  const post = postQuery.data;
  const comments = commentsQuery.data?.results ?? emptyComments;
  const commentTree = useMemo(() => buildCommentTree(comments), [comments]);
  const totalPages = Math.max(1, Math.ceil((commentsQuery.data?.count ?? 0) / commentsPageSize));
  const isOwnPost = Boolean(
    post?.author?.id && auth.profile?.user_id && String(post.author.id) === String(auth.profile.user_id),
  );

  const reactMutation = useMutation({ ...communityMutations.react(), onSuccess: invalidateCommunity });
  const unreactMutation = useMutation({ ...communityMutations.unreact(), onSuccess: invalidateCommunity });
  const bookmarkMutation = useMutation({ ...communityMutations.bookmark(), onSuccess: invalidateCommunity });
  const unbookmarkMutation = useMutation({ ...communityMutations.unbookmark(), onSuccess: invalidateCommunity });
  const followMutation = useMutation({
    ...communityMutations.follow(),
    onSuccess: async () => {
      await invalidateCommunityFollows(queryClient, post?.author?.id);
      await invalidateCommunity();
    },
  });
  const unfollowMutation = useMutation({
    ...communityMutations.unfollow(),
    onSuccess: async () => {
      await invalidateCommunityFollows(queryClient, post?.author?.id);
      await invalidateCommunity();
    },
  });
  const commentMutation = useMutation({
    ...communityMutations.createPostComment(),
    onSuccess: async () => {
      setComment('');
      setCommentSpoiler(false);
      setReplyTarget(null);
      await invalidateCommunity();
    },
  });
  const reportMutation = useMutation({
    ...communityMutations.createReport(),
    onSuccess: async () => {
      setReportTarget(null);
      setReportReason('spam');
      setReportDescription('');
      await invalidateCommunity();
    },
  });
  const deletePostMutation = useMutation({
    ...communityMutations.deletePost(),
    onSuccess: async () => {
      setDeleteTarget(null);
      await invalidateCommunity();
      void navigate(routes.communityPosts);
    },
  });
  const deleteCommentMutation = useMutation({
    ...communityMutations.deleteComment(),
    onSuccess: async () => {
      setDeleteTarget(null);
      await invalidateCommunity();
    },
  });
  const updatePostMutation = useMutation({
    ...communityMutations.updatePost(),
    onSuccess: async () => {
      setEditTarget(null);
      await invalidateCommunity();
    },
  });
  const updateCommentMutation = useMutation({
    ...communityMutations.updateComment(),
    onSuccess: async () => {
      setEditTarget(null);
      await invalidateCommunity();
    },
  });

  const isActionPending = useMemo(
    () =>
      reactMutation.isPending ||
      unreactMutation.isPending ||
      bookmarkMutation.isPending ||
      unbookmarkMutation.isPending ||
      followMutation.isPending ||
      unfollowMutation.isPending ||
      deletePostMutation.isPending ||
      deleteCommentMutation.isPending ||
      updatePostMutation.isPending ||
      updateCommentMutation.isPending,
    [
      bookmarkMutation.isPending,
      deleteCommentMutation.isPending,
      deletePostMutation.isPending,
      followMutation.isPending,
      reactMutation.isPending,
      unbookmarkMutation.isPending,
      unfollowMutation.isPending,
      unreactMutation.isPending,
      updateCommentMutation.isPending,
      updatePostMutation.isPending,
    ],
  );

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

  function goToCommentsPage(page: number) {
    const next = new URLSearchParams(searchParams);
    next.set('comments_page', String(page));
    setSearchParams(next);
  }

  function togglePostReaction() {
    if (!post) return;
    const body = { target_type: 'post' as const, target_id: post.id, reaction_type: 'like' as const };
    if (post.viewer_state?.has_liked) {
      unreactMutation.mutate(body);
    } else {
      reactMutation.mutate(body);
    }
  }

  function toggleCommentReaction(targetComment: CommunityCommentSummary) {
    const body = { target_type: 'comment' as const, target_id: targetComment.id, reaction_type: 'like' as const };
    if (targetComment.viewer_state?.has_liked) {
      unreactMutation.mutate(body);
    } else {
      reactMutation.mutate(body);
    }
  }

  function togglePostBookmark() {
    if (!post) return;
    const body = { target_type: 'post' as const, target_id: post.id };
    if (post.viewer_state?.has_bookmarked) {
      unbookmarkMutation.mutate(body);
    } else {
      bookmarkMutation.mutate(body);
    }
  }

  function toggleFollowAuthor() {
    if (!post?.author?.id) return;
    if (post.viewer_state?.is_following_author) {
      unfollowMutation.mutate(post.author.id);
    } else {
      followMutation.mutate(post.author.id);
    }
  }

  function submitComment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!comment.trim()) return;
    commentMutation.mutate({
      postId,
      body: {
        parent_id: replyTarget?.id,
        content: comment,
        visibility: 'public',
        is_spoiler: commentSpoiler,
      },
    });
  }

  function openReport(target: ReportTarget) {
    setReportTarget(target);
    setReportReason('spam');
    setReportDescription('');
  }

  function submitReport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!reportTarget) return;
    reportMutation.mutate({
      target_type: reportTarget.type,
      target_id: reportTarget.id,
      reason: reportReason,
      description: reportDescription,
    });
  }

  function submitDelete() {
    if (!deleteTarget) return;
    if (deleteTarget.type === 'post') {
      deletePostMutation.mutate(deleteTarget.id);
    } else {
      deleteCommentMutation.mutate(deleteTarget.id);
    }
  }

  function submitEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editTarget || !editTarget.content.trim()) return;

    if (editTarget.type === 'post') {
      updatePostMutation.mutate({
        postId: editTarget.id,
        body: {
          content: editTarget.content,
          is_spoiler: editTarget.is_spoiler,
          is_nsfw: editTarget.is_nsfw,
        },
      });
      return;
    }

    updateCommentMutation.mutate({
      commentId: editTarget.id,
      body: {
        content: editTarget.content,
        is_spoiler: editTarget.is_spoiler,
      },
    });
  }

  function updateEditContent(content: string) {
    setEditTarget((current) => (current ? { ...current, content } : current));
  }

  function updateEditSpoiler(isSpoiler: boolean) {
    setEditTarget((current) => (current ? { ...current, is_spoiler: isSpoiler } : current));
  }

  function updateEditNsfw(isNsfw: boolean) {
    setEditTarget((current) => (current && current.type === 'post' ? { ...current, is_nsfw: isNsfw } : current));
  }

  function replyTargetName(target: CommunityCommentSummary) {
    if (target.is_hidden) return t('community.deletedComment');
    return target.author?.nickname || t('common.anonymous');
  }

  if (!Number.isFinite(postId) || postId <= 0) {
    return (
      <Page title={t('community.postDetailTitle')} eyebrow={t('nav.groupCommunity')}>
        <ErrorState title={t('community.invalidPostTitle')} description={t('community.invalidPostBody')} />
      </Page>
    );
  }

  return (
    <Page
      title={t('community.postDetailTitle')}
      eyebrow={t('nav.groupCommunity')}
      actions={
        <Button asChild type="button" variant="secondary">
          <Link to={routes.communityPosts}>{t('community.backToPosts')}</Link>
        </Button>
      }
    >
      {postQuery.isLoading ? <LoadingState title={t('community.loadingPost')} /> : null}
      {postQuery.isError ? (
        <ErrorState title={t('community.postErrorTitle')} description={t('community.postErrorBody')} />
      ) : null}
      {post ? (
        <div className="grid gap-4">
          <PostBody post={post} />
          <div className="community-action-bar">
            <Button
              className={`community-action-button ${post.viewer_state?.has_liked ? 'is-active' : ''}`}
              disabled={isActionPending}
              type="button"
              variant="ghost"
              onClick={togglePostReaction}
            >
              <Heart className="size-4" /> {post.viewer_state?.has_liked ? t('community.liked') : t('community.like')}
            </Button>
            <Button
              className={`community-action-button ${post.viewer_state?.has_bookmarked ? 'is-active' : ''}`}
              disabled={isActionPending}
              type="button"
              variant="ghost"
              onClick={togglePostBookmark}
            >
              <Bookmark className="size-4" />{' '}
              {post.viewer_state?.has_bookmarked ? t('community.bookmarked') : t('community.bookmark')}
            </Button>
            {post.author?.id && !isOwnPost ? (
              <Button
                className={`community-action-button ${post.viewer_state?.is_following_author ? 'is-active' : ''}`}
                disabled={isActionPending}
                type="button"
                variant="ghost"
                onClick={toggleFollowAuthor}
              >
                <UserPlus className="size-4" />{' '}
                {post.viewer_state?.is_following_author ? t('community.following') : t('community.followAuthor')}
              </Button>
            ) : null}
            <Button
              className="community-action-button"
              type="button"
              variant="ghost"
              onClick={() => openReport({ type: 'post', id: post.id, label: t('community.reportPost') })}
            >
              <Flag className="size-4" /> {t('community.report')}
            </Button>
            {isOwnPost ? (
              <Button
                className="community-action-button"
                disabled={isActionPending}
                type="button"
                variant="ghost"
                onClick={() =>
                  setEditTarget({
                    type: 'post',
                    id: post.id,
                    content: post.content,
                    is_spoiler: post.is_spoiler,
                    is_nsfw: post.is_nsfw,
                  })
                }
              >
                <PencilLine className="size-4" /> {t('common.edit')}
              </Button>
            ) : null}
            {isOwnPost ? (
              <Button
                className="community-action-button"
                disabled={isActionPending}
                type="button"
                variant="ghost"
                onClick={() => setDeleteTarget({ type: 'post', id: post.id })}
              >
                <Trash2 className="size-4" /> {t('common.delete')}
              </Button>
            ) : null}
          </div>

          <section className="grid gap-3">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-base font-semibold tracking-tight text-neutral-950 dark:text-white">
                {t('community.comments')}
              </h2>
              <span className="text-sm text-neutral-500 dark:text-neutral-400">{commentsQuery.data?.count ?? 0}</span>
            </div>
            {post.is_locked ? (
              <EmptyState title={t('community.postLockedTitle')} description={t('community.postLockedBody')} />
            ) : (
              <form
                className="grid gap-3 rounded-lg border border-neutral-200 bg-white p-3 dark:border-neutral-800 dark:bg-neutral-950"
                onSubmit={submitComment}
              >
                {replyTarget ? (
                  <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-neutral-50 px-3 py-2 text-sm text-neutral-500 dark:bg-neutral-900 dark:text-neutral-400">
                    <span>
                      {t('community.replyingTo')}{' '}
                      <strong className="text-neutral-950 dark:text-white">{replyTargetName(replyTarget)}</strong>
                    </span>
                    <button
                      className="font-semibold text-[var(--color-accent-strong)]"
                      type="button"
                      onClick={() => setReplyTarget(null)}
                    >
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
                    <input
                      checked={commentSpoiler}
                      className="size-4 accent-[var(--color-accent)]"
                      type="checkbox"
                      onChange={(event) => setCommentSpoiler(event.target.checked)}
                    />
                    {t('community.markSpoiler')}
                  </label>
                  <Button disabled={commentMutation.isPending || !comment.trim()} type="submit">
                    <MessageSquare className="size-4" /> {t('community.sendComment')}
                  </Button>
                </div>
              </form>
            )}

            {commentsQuery.isLoading ? <LoadingState title={t('community.loadingComments')} /> : null}
            {commentsQuery.isError ? (
              <ErrorState title={t('community.commentsErrorTitle')} description={t('community.commentsErrorBody')} />
            ) : null}
            {!commentsQuery.isLoading && !commentsQuery.isError && comments.length === 0 ? (
              <EmptyState title={t('community.noCommentsTitle')} description={t('community.noCommentsBody')} />
            ) : null}
            <div className="community-comment-list">
              {commentTree.map((item) => (
                <CommentThread
                  key={item.id}
                  node={item}
                  canReply={!post.is_locked}
                  currentUserId={auth.profile?.user_id}
                  pending={isActionPending}
                  onDelete={(targetComment) => setDeleteTarget({ type: 'comment', id: targetComment.id })}
                  onEdit={(targetComment) =>
                    setEditTarget({
                      type: 'comment',
                      id: targetComment.id,
                      content: targetComment.content,
                      is_spoiler: targetComment.is_spoiler,
                    })
                  }
                  onLike={toggleCommentReaction}
                  onReport={(targetComment) =>
                    openReport({ type: 'comment', id: targetComment.id, label: t('community.reportComment') })
                  }
                  onReply={setReplyTarget}
                />
              ))}
            </div>
            <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={goToCommentsPage} />
          </section>
        </div>
      ) : null}

      <Dialog open={Boolean(reportTarget)} onOpenChange={(open) => !open && setReportTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('community.reportTitle')}</DialogTitle>
            <DialogDescription>{reportTarget?.label || t('community.reportDescription')}</DialogDescription>
          </DialogHeader>
          <form className="grid gap-4" onSubmit={submitReport}>
            <div className="grid gap-2">
              <span className="text-sm font-semibold text-neutral-950 dark:text-white">
                {t('community.reportReason')}
              </span>
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
              <Button type="button" variant="secondary" onClick={() => setReportTarget(null)}>
                {t('common.cancel')}
              </Button>
              <Button disabled={reportMutation.isPending} type="submit">
                <Flag className="size-4" /> {t('community.submitReport')}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(deleteTarget)} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {deleteTarget?.type === 'post' ? t('community.deletePostTitle') : t('community.deleteCommentTitle')}
            </DialogTitle>
            <DialogDescription>
              {deleteTarget?.type === 'post' ? t('community.deletePostBody') : t('community.deleteCommentBody')}
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setDeleteTarget(null)}>
              {t('common.cancel')}
            </Button>
            <Button
              disabled={deletePostMutation.isPending || deleteCommentMutation.isPending}
              type="button"
              onClick={submitDelete}
            >
              <Trash2 className="size-4" /> {t('common.delete')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(editTarget)} onOpenChange={(open) => !open && setEditTarget(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {editTarget?.type === 'post' ? t('community.editPostTitle') : t('community.editCommentTitle')}
            </DialogTitle>
            <DialogDescription>
              {editTarget?.type === 'post' ? t('community.editPostDescription') : t('community.editCommentDescription')}
            </DialogDescription>
          </DialogHeader>
          <form className="grid gap-4" onSubmit={submitEdit}>
            <textarea
              className="min-h-40 resize-y rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm leading-6 outline-none transition placeholder:text-neutral-400 focus:border-[var(--color-accent-border)] dark:border-neutral-800 dark:bg-neutral-900"
              value={editTarget?.content ?? ''}
              placeholder={t('community.postPlaceholder')}
              onChange={(event) => updateEditContent(event.target.value)}
            />
            <div className="flex flex-wrap gap-3 text-sm text-neutral-500 dark:text-neutral-400">
              <label className="inline-flex items-center gap-2">
                <input
                  checked={Boolean(editTarget?.is_spoiler)}
                  className="size-4 accent-[var(--color-accent)]"
                  type="checkbox"
                  onChange={(event) => updateEditSpoiler(event.target.checked)}
                />
                {t('community.markSpoiler')}
              </label>
              {editTarget?.type === 'post' ? (
                <label className="inline-flex items-center gap-2">
                  <input
                    checked={editTarget.is_nsfw}
                    className="size-4 accent-[var(--color-accent)]"
                    type="checkbox"
                    onChange={(event) => updateEditNsfw(event.target.checked)}
                  />
                  NSFW
                </label>
              ) : null}
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setEditTarget(null)}>
                {t('common.cancel')}
              </Button>
              <Button
                disabled={
                  updatePostMutation.isPending || updateCommentMutation.isPending || !editTarget?.content.trim()
                }
                type="submit"
              >
                <PencilLine className="size-4" /> {t('common.save')}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </Page>
  );
}
