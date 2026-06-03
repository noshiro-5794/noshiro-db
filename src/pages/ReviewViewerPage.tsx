import { Link, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, PencilLine, ShieldAlert, Trash2 } from 'lucide-react';
import { useAuth } from '@/features/auth/use-auth';
import { CommunityCommentsSection } from '@/features/community/components/CommunityCommentsSection';
import { CommunityTargetActions } from '@/features/community/components/CommunityTargetActions';
import { useI18n } from '@/features/i18n/use-i18n';
import { libraryMutations, libraryQueries, libraryQueryKeys } from '@/features/library/library-queries';
import { MarkdownRenderer } from '@/features/reviews/components/MarkdownRenderer';
import { routes } from '@/routes/paths';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/shared/ui/Dialog';
import { ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';
import { useState } from 'react';

function parseReviewId(value?: string) {
  const reviewId = Number(value);
  return Number.isInteger(reviewId) && reviewId > 0 ? reviewId : null;
}

function formatDate(value?: string) {
  if (!value) return '';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
}

function numberMeta(value: unknown) {
  return typeof value === 'number' ? value : undefined;
}

export function ReviewViewerPage() {
  const { t } = useI18n();
  const { reviewId: reviewIdParam } = useParams();
  const auth = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const reviewId = parseReviewId(reviewIdParam);
  const myReviewQuery = useQuery({
    ...libraryQueries.review(reviewId ?? 0),
    enabled: Boolean(reviewId) && auth.isAuthenticated,
    retry: false,
  });
  const reviewQuery = useQuery({
    ...libraryQueries.publicReview(reviewId ?? 0),
    enabled: Boolean(reviewId),
  });
  const review = myReviewQuery.data ?? reviewQuery.data;
  const isOwnReview = Boolean(myReviewQuery.data || (review?.user?.id && auth.profile?.user_id && String(review.user.id) === String(auth.profile.user_id)));
  const deleteReviewMutation = useMutation({
    ...libraryMutations.deleteReview(),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: libraryQueryKeys.reviews() }),
        queryClient.invalidateQueries({ queryKey: libraryQueryKeys.publicReviewDetail(reviewId ?? 0) }),
      ]);
      setDeleteOpen(false);
      navigate(routes.reviews);
    },
  });

  if (!reviewId) {
    return <Page title={t('common.review')}><ErrorState title={t('reviewViewer.invalidTitle')} description={t('reviewViewer.invalidBody')} /></Page>;
  }

  if (reviewQuery.isLoading || (auth.isAuthenticated && myReviewQuery.isLoading)) {
    return <Page title={t('common.review')}><LoadingState title={t('reviewViewer.loading')} /></Page>;
  }

  if ((reviewQuery.isError && myReviewQuery.isError) || !review) {
    return <Page title={t('common.review')}><ErrorState title={t('reviewViewer.unavailableTitle')} description={t('reviewViewer.unavailableBody')} /></Page>;
  }

  return (
    <Page
      actions={(
        <>
          <Button asChild variant="ghost">
            <Link to={review.subject ? routes.subject(review.subject.id) : routes.reviews}><ArrowLeft className="size-4" /> {t('common.back')}</Link>
          </Button>
          {isOwnReview ? (
            <>
              <Button asChild>
                <Link to={routes.reviewEdit(review.id)}><PencilLine className="size-4" /> {t('common.edit')}</Link>
              </Button>
              <Button type="button" variant="secondary" onClick={() => setDeleteOpen(true)}>
                <Trash2 className="size-4" /> {t('common.delete')}
              </Button>
            </>
          ) : null}
        </>
      )}
      description={review.subject?.display_title || review.subject?.title || t('reviewViewer.publicReview')}
      eyebrow={t('common.review')}
      title={review.title}
    >
      <article className="review-reader">
        <header className="review-reader-header">
          <div className="flex min-w-0 items-center gap-3">
            <img
              alt=""
              className="size-10 rounded-full bg-neutral-100 object-cover dark:bg-neutral-900"
              src={review.user?.avatar || '/assets/placeholders/avatar.png'}
            />
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-neutral-950 dark:text-white">{review.user?.nickname || t('common.anonymous')}</p>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">
                {formatDate(review.updated_at || review.created_at)}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            <Badge variant={review.is_public ? 'accent' : 'secondary'}>{review.is_public ? t('common.public') : t('common.private')}</Badge>
            {review.is_spoiler ? <Badge><ShieldAlert className="size-3" /> {t('common.spoiler')}</Badge> : null}
          </div>
        </header>
        <div className={review.is_spoiler ? 'review-reader-content is-spoiler' : 'review-reader-content'}>
          <MarkdownRenderer content={review.content} />
        </div>
      </article>
      <CommunityTargetActions
        className="rounded-lg border border-neutral-200 bg-white p-2 dark:border-neutral-800 dark:bg-neutral-950"
        reactionCount={numberMeta(review.reaction_count)}
        reportLabel={t('community.reportReview')}
        targetId={review.id}
        targetType="review"
        viewerState={review.viewer_state as { has_liked?: boolean; has_bookmarked?: boolean } | undefined}
      />
      {review.is_public || isOwnReview ? (
        <CommunityCommentsSection targetType="review" targetId={review.id} />
      ) : null}
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('reviewViewer.deleteTitle')}</DialogTitle>
            <DialogDescription>{t('reviewViewer.deleteBody')}</DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setDeleteOpen(false)}>{t('common.cancel')}</Button>
            <Button disabled={deleteReviewMutation.isPending} type="button" onClick={() => deleteReviewMutation.mutate(review.id)}>
              <Trash2 className="size-4" /> {t('common.delete')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </Page>
  );
}
