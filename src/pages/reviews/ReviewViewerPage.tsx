import { Link, useLocation, useNavigate, useParams } from '@/shared/routing/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, PencilLine, ShieldAlert, Trash2 } from 'lucide-react';
import { useAuth } from '@/entities/session';
import { CommunityCommentsSection } from '@/features/community';
import { CommunityTargetActions } from '@/features/community';
import { useI18n } from '@/shared/i18n';
import { libraryMutations, libraryQueries, libraryQueryKeys } from '@/entities/library';
import { MarkdownRenderer } from '@/features/reviews';
import { routes } from '@/shared/routing/paths';
import { backTargetFromState, routeBackState } from '@/shared/routing/route-state';
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
  const location = useLocation();
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
  const fallbackBackTarget = review?.subject ? routes.subject(review.subject.id) : routes.reviews;
  const backTarget = backTargetFromState(location, fallbackBackTarget);
  const isOwnReview = Boolean(
    myReviewQuery.data ||
    (review?.user?.id && auth.profile?.user_id && String(review.user.id) === String(auth.profile.user_id)),
  );
  const deleteReviewMutation = useMutation({
    ...libraryMutations.deleteReview(),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: libraryQueryKeys.reviews() }),
        queryClient.invalidateQueries({ queryKey: libraryQueryKeys.publicReviewDetail(reviewId ?? 0) }),
      ]);
      setDeleteOpen(false);
      void navigate(reviewId && backTarget === routes.review(reviewId) ? routes.reviews : backTarget);
    },
  });

  if (!reviewId) {
    return (
      <Page title={t('common.review')} eyebrow={t('reviewViewer.publicReview')}>
        <ErrorState title={t('reviewViewer.invalidTitle')} description={t('reviewViewer.invalidBody')} />
      </Page>
    );
  }

  if (reviewQuery.isLoading || (auth.isAuthenticated && myReviewQuery.isLoading)) {
    return (
      <Page title={t('common.review')} eyebrow={t('reviewViewer.publicReview')}>
        <LoadingState title={t('reviewViewer.loading')} />
      </Page>
    );
  }

  if ((reviewQuery.isError && myReviewQuery.isError) || !review) {
    return (
      <Page title={t('common.review')} eyebrow={t('reviewViewer.publicReview')}>
        <ErrorState title={t('reviewViewer.unavailableTitle')} description={t('reviewViewer.unavailableBody')} />
      </Page>
    );
  }

  return (
    <Page
      actions={
        <>
          <Button asChild variant="ghost">
            <Link to={backTarget}>
              <ArrowLeft className="size-4" /> {t('common.back')}
            </Link>
          </Button>
          {isOwnReview ? (
            <>
              <Button asChild>
                <Link state={routeBackState(location, t('common.review'))} to={routes.reviewEdit(review.id)}>
                  <PencilLine className="size-4" /> {t('common.edit')}
                </Link>
              </Button>
              <Button type="button" variant="secondary" onClick={() => setDeleteOpen(true)}>
                <Trash2 className="size-4" /> {t('common.delete')}
              </Button>
            </>
          ) : null}
        </>
      }
      description={review.subject?.display_title || review.subject?.title || t('reviewViewer.publicReview')}
      eyebrow={t('reviewViewer.publicReview')}
      title={review.title}
    >
      <article className="content-reader">
        <header className="content-reader-header">
          <div className="content-reader-author">
            <img alt="" src={review.user?.avatar || '/assets/placeholders/avatar.png'} />
            <div className="min-w-0">
              <p>{review.user?.nickname || t('common.anonymous')}</p>
              <span>{formatDate(review.updated_at || review.created_at)}</span>
            </div>
          </div>
          <div className="content-reader-badges">
            <Badge variant={review.is_public ? 'accent' : 'secondary'}>
              {review.is_public ? t('common.public') : t('common.private')}
            </Badge>
            {review.is_spoiler ? (
              <Badge>
                <ShieldAlert className="size-3" /> {t('common.spoiler')}
              </Badge>
            ) : null}
          </div>
        </header>
        <div className={review.is_spoiler ? 'content-reader-body is-spoiler' : 'content-reader-body'}>
          <MarkdownRenderer content={review.content} />
        </div>
        <footer className="content-reader-actions">
          <CommunityTargetActions
            presentation="inline"
            reactionCount={numberMeta(review.reaction_count)}
            reportLabel={t('community.reportReview')}
            targetId={review.id}
            targetType="review"
            viewerState={review.viewer_state}
          />
        </footer>
      </article>
      {review.is_public || isOwnReview ? (
        <section className="content-reader-section">
          <CommunityCommentsSection targetType="review" targetId={review.id} />
        </section>
      ) : null}
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('reviewViewer.deleteTitle')}</DialogTitle>
            <DialogDescription>{t('reviewViewer.deleteBody')}</DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setDeleteOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button
              disabled={deleteReviewMutation.isPending}
              type="button"
              onClick={() => deleteReviewMutation.mutate(review.id)}
            >
              <Trash2 className="size-4" /> {t('common.delete')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </Page>
  );
}
