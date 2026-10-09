import { type SyntheticEvent, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, PencilLine, Trash2, UserPlus } from 'lucide-react';
import { getRouteApi, Link } from '@tanstack/react-router';
import { communityMutations, communityQueries, communityQueryKeys } from '@/entities/community';
import { useAuth } from '@/entities/session';
import {
  CommunityCommentsSection,
  CommunityTargetActions,
  invalidateCommunityTargets,
  useFollowUserMutation,
} from '@/features/community';
import { useI18n } from '@/shared/i18n';
import { routes } from '@/shared/routing/paths';
import { parseIntegerParam } from '@/shared/routing/search-params';
import { Button } from '@/shared/ui/Button';
import { CheckboxField } from '@/shared/ui/Checkbox';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { DetailFooter } from '@/shared/ui/Detail';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/shared/ui/Dialog';
import { ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';
import { Textarea } from '@/shared/ui/Textarea';
import { Toggle } from '@/shared/ui/Toggle';
import { toast } from '@/shared/ui/toast';
import { PostContent } from './PostContent';

type PostEditDraft = {
  content: string;
  isNsfw: boolean;
  isSpoiler: boolean;
};

const communityPostRoute = getRouteApi('/community/posts/$postId');

export function CommunityPostPage() {
  const { t } = useI18n();
  const auth = useAuth();
  const queryClient = useQueryClient();
  const navigate = communityPostRoute.useNavigate();
  const params = communityPostRoute.useParams();
  const { post_comments_page: commentsPage = 1 } = communityPostRoute.useSearch();
  const postId = parseIntegerParam(params.postId, { min: 1 }) ?? 0;
  const isValidPostId = postId > 0;
  const [editDraft, setEditDraft] = useState<PostEditDraft | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const postQuery = useQuery({ ...communityQueries.post(postId), enabled: isValidPostId });
  const post = postQuery.data;
  const isOwnPost = Boolean(post?.author?.id && auth.profile?.user_id && post.author.id === auth.profile.user_id);

  async function invalidatePost() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: communityQueryKeys.postDetail(postId) }),
      invalidateCommunityTargets(queryClient),
    ]);
  }

  const showMutationError = () => toast.error(t('common.requestFailed'));
  const followMutation = useFollowUserMutation();
  const updatePostMutation = useMutation({
    ...communityMutations.updatePost(),
    onError: showMutationError,
    onSuccess: async () => {
      setEditDraft(null);
      await invalidatePost();
    },
  });
  const deletePostMutation = useMutation({
    ...communityMutations.deletePost(),
    onError: showMutationError,
    onSuccess: async () => {
      setDeleteOpen(false);
      await invalidateCommunityTargets(queryClient);
      queryClient.removeQueries({ exact: true, queryKey: communityQueryKeys.postDetail(postId) });
      await navigate({ replace: true, to: '/community/posts' });
    },
  });
  const isOwnerActionPending = followMutation.isPending || updatePostMutation.isPending || deletePostMutation.isPending;

  function toggleFollowAuthor() {
    if (!post?.author?.id || followMutation.isPending) return;
    followMutation.mutate(
      {
        targetUserId: post.author.id,
        shouldFollow: !post.viewer_state?.is_following_author,
      },
      {
        onSettled: () => {
          void invalidatePost();
        },
      },
    );
  }

  function submitEdit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (!post || !editDraft?.content.trim()) return;
    updatePostMutation.mutate({
      postId: post.id,
      body: {
        content: editDraft.content,
        is_nsfw: editDraft.isNsfw,
        is_spoiler: editDraft.isSpoiler,
      },
    });
  }

  if (!isValidPostId) {
    return (
      <Page title={t('community.postDetailTitle')} eyebrow={t('nav.groupCommunity')}>
        <ErrorState title={t('community.invalidPostTitle')} description={t('community.invalidPostBody')} />
      </Page>
    );
  }

  if (postQuery.isLoading) {
    return (
      <Page title={t('community.postDetailTitle')} eyebrow={t('nav.groupCommunity')}>
        <LoadingState title={t('community.loadingPost')} />
      </Page>
    );
  }

  if (postQuery.isError || !post) {
    return (
      <Page title={t('community.postDetailTitle')} eyebrow={t('nav.groupCommunity')}>
        <ErrorState title={t('community.postErrorTitle')} description={t('community.postErrorBody')} />
      </Page>
    );
  }

  const postTitleId = `post-title-${post.id}`;

  return (
    <Page
      title={t('community.postDetailTitle')}
      eyebrow={t('nav.groupCommunity')}
      headerMode="context"
      leading={
        <Button
          asChild
          aria-label={t('community.backToPosts')}
          size="icon-sm"
          tooltip={t('community.backToPosts')}
          variant="ghost"
        >
          <Link to={routes.communityPosts}>
            <ArrowLeft className="size-4" />
          </Link>
        </Button>
      }
      seoDescription={post.content.slice(0, 160)}
      width="reader"
    >
      <article aria-labelledby={postTitleId} className="mx-auto grid w-full max-w-3xl min-w-0 gap-6">
        <PostContent post={post} title={t('community.postDetailTitle')} titleId={postTitleId} />
        <DetailFooter>
          <CommunityTargetActions
            additionalActions={
              <>
                {auth.isAuthenticated && post.author?.id && !isOwnPost ? (
                  <Toggle
                    className="community-action-button"
                    disabled={isOwnerActionPending}
                    pressed={Boolean(post.viewer_state?.is_following_author)}
                    variant="bare"
                    onPressedChange={toggleFollowAuthor}
                  >
                    <UserPlus className="size-4" />{' '}
                    {post.viewer_state?.is_following_author ? t('community.following') : t('community.followAuthor')}
                  </Toggle>
                ) : null}
                {isOwnPost ? (
                  <Button
                    className="community-action-button"
                    disabled={isOwnerActionPending}
                    type="button"
                    variant="unstyled"
                    onClick={() => {
                      setEditDraft({
                        content: post.content,
                        isNsfw: post.is_nsfw,
                        isSpoiler: post.is_spoiler,
                      });
                    }}
                  >
                    <PencilLine className="size-4" /> {t('common.edit')}
                  </Button>
                ) : null}
                {isOwnPost ? (
                  <Button
                    className="community-action-button"
                    disabled={isOwnerActionPending}
                    type="button"
                    variant="unstyled"
                    onClick={() => {
                      setDeleteOpen(true);
                    }}
                  >
                    <Trash2 className="size-4" /> {t('common.delete')}
                  </Button>
                ) : null}
              </>
            }
            reactionCount={post.reaction_count}
            reportLabel={t('community.reportPost')}
            targetId={post.id}
            targetType="post"
            viewerState={post.viewer_state}
          />
        </DetailFooter>
      </article>
      <div className="mx-auto mt-6 w-full max-w-3xl border-t border-border-subtle pt-6" data-slot="detail-comments">
        <CommunityCommentsSection
          currentPage={commentsPage}
          locked={Boolean(post.is_locked)}
          targetId={post.id}
          targetType="post"
          onPageChange={(page) => void navigate({ search: (current) => ({ ...current, post_comments_page: page }) })}
        />
      </div>

      <ConfirmDialog
        confirmIcon={<Trash2 className="size-4" />}
        confirmLabel={t('common.delete')}
        description={t('community.deletePostBody')}
        isPending={deletePostMutation.isPending}
        open={deleteOpen}
        title={t('community.deletePostTitle')}
        onConfirm={() => {
          deletePostMutation.mutate(post.id);
        }}
        onOpenChange={setDeleteOpen}
      />

      <Dialog
        open={Boolean(editDraft)}
        onOpenChange={(open) => {
          if (!open) setEditDraft(null);
        }}
      >
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{t('community.editPostTitle')}</DialogTitle>
            <DialogDescription>{t('community.editPostDescription')}</DialogDescription>
          </DialogHeader>
          <form className="grid gap-4" onSubmit={submitEdit}>
            <Textarea
              aria-label={t('community.postPlaceholder')}
              className="min-h-40"
              maxLength={10_000}
              value={editDraft?.content ?? ''}
              placeholder={t('community.postPlaceholder')}
              onChange={(event) => {
                setEditDraft((current) => (current ? { ...current, content: event.target.value } : current));
              }}
            />
            <div className="flex flex-wrap gap-3 text-sm text-[var(--ui-text-muted)]">
              <CheckboxField
                checked={Boolean(editDraft?.isSpoiler)}
                onCheckedChange={(checked) => {
                  setEditDraft((current) => (current ? { ...current, isSpoiler: checked } : current));
                }}
              >
                {t('community.markSpoiler')}
              </CheckboxField>
              <CheckboxField
                checked={Boolean(editDraft?.isNsfw)}
                onCheckedChange={(checked) => {
                  setEditDraft((current) => (current ? { ...current, isNsfw: checked } : current));
                }}
              >
                NSFW
              </CheckboxField>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setEditDraft(null);
                }}
              >
                {t('common.cancel')}
              </Button>
              <Button disabled={updatePostMutation.isPending || !editDraft?.content.trim()} type="submit">
                <PencilLine className="size-4" /> {t('common.save')}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </Page>
  );
}
