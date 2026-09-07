import { formatDate } from '@/shared/lib/date';
import { getRouteApi, Link, useLocation } from '@tanstack/react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, PencilLine, ShieldAlert, Trash2 } from 'lucide-react';
import { useAuth } from '@/entities/session';
import { CommunityCommentsSection, CommunityTargetActions } from '@/features/community';
import { useI18n } from '@/shared/i18n';
import { libraryMutations, libraryQueries, libraryQueryKeys } from '@/entities/library';
import { invalidateReviewViews, MarkdownRenderer, ReviewDeleteDialog } from '@/features/reviews';
import type { ApiPage, Review } from '@/shared/api';
import { routes } from '@/shared/routing/paths';
import { resolvedRouteHref } from '@/shared/routing/resolved-href';
import { parseIntegerParam } from '@/shared/routing/search-params';
import { backTargetFromState, routeBackState } from '@/shared/routing/route-state';
import { Badge } from '@/shared/ui/Badge';
import { Avatar } from '@/shared/ui/Avatar';
import { Button } from '@/shared/ui/Button';
import { DetailBody, DetailFooter, DetailHeader } from '@/shared/ui/Detail';
import { ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';
import { SensitiveContent } from '@/shared/ui/SensitiveContent';
import { toast } from '@/shared/ui/toast';
import { useState } from 'react';

const reviewRoute = getRouteApi('/reviews/$reviewId');

function parseReviewId(value?: string) {
  return parseIntegerParam(value, { min: 1 });
}

function numberMeta(value: unknown) {
  return typeof value === 'number' ? value : undefined;
}

export function ReviewViewerPage() {
  const { t } = useI18n();
  const { reviewId: reviewIdParam } = reviewRoute.useParams();
  const auth = useAuth();
  const location = useLocation();
  const navigate = reviewRoute.useNavigate();
  const { review_comments_page: commentsPage = 1 } = reviewRoute.useSearch();
  const queryClient = useQueryClient();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const reviewId = parseReviewId(reviewIdParam);
  const cachedOwnReview = reviewId
    ? queryClient
        .getQueriesData<ApiPage<Review>>({ queryKey: libraryQueryKeys.reviewLists() })
        .flatMap(([, page]) => page?.results ?? [])
        .find((candidate) => candidate.id === reviewId)
    : undefined;
  const preferOwnReview = cachedOwnReview?.is_public === false;
  const reviewQuery = useQuery({
    ...libraryQueries.publicReview(reviewId ?? 0),
    enabled: Boolean(reviewId) && !preferOwnReview,
    retry: false,
  });
  const publicReview = preferOwnReview ? undefined : reviewQuery.data;
  const publicReviewUnavailable = reviewQuery.isError && !reviewQuery.isFetching;
  const shouldLoadOwnReview = Boolean(reviewId && auth.isAuthenticated && (preferOwnReview || publicReviewUnavailable));
  const myReviewQuery = useQuery({
    ...libraryQueries.review(reviewId ?? 0),
    enabled: shouldLoadOwnReview,
    retry: false,
  });
  const review = myReviewQuery.data ?? publicReview;
  const fallbackBackTarget = review?.subject ? routes.entity(review.subject.id) : routes.reviews;
  const backTarget = backTargetFromState(location, fallbackBackTarget);
  const isOwnReview = Boolean(
    myReviewQuery.data || (review?.user.id && auth.profile?.user_id && review.user.id === auth.profile.user_id),
  );
  const deleteReviewMutation = useMutation({
    ...libraryMutations.deleteReview(),
    onError: () => toast.error(t('common.requestFailed')),
    onSuccess: async () => {
      await invalidateReviewViews(queryClient, {
        includeComments: true,
        userId: auth.profile?.user_id,
      });
      setDeleteOpen(false);
      void navigate({ href: reviewId && backTarget === routes.review(reviewId) ? routes.reviews : backTarget });
    },
  });

  if (!reviewId) {
    return (
      <Page title={t('common.review')} eyebrow={t('reviewViewer.publicReview')}>
        <ErrorState title={t('reviewViewer.invalidTitle')} description={t('reviewViewer.invalidBody')} />
      </Page>
    );
  }

  const isResolvingReview =
    (reviewQuery.isFetching && !publicReview) ||
    myReviewQuery.isLoading ||
    ((preferOwnReview || publicReviewUnavailable) && auth.status === 'checking');

  if (isResolvingReview) {
    return (
      <Page title={t('common.review')} eyebrow={t('reviewViewer.publicReview')}>
        <LoadingState title={t('reviewViewer.loading')} />
      </Page>
    );
  }

  if (!review) {
    return (
      <Page title={t('common.review')} eyebrow={t('reviewViewer.publicReview')}>
        <ErrorState title={t('reviewViewer.unavailableTitle')} description={t('reviewViewer.unavailableBody')} />
      </Page>
    );
  }

  const reviewTitleId = `review-title-${review.id}`;
  const reviewDate = review.updated_at || review.created_at;

  return (
    <Page
      actions={
        isOwnReview ? (
          <>
            <Button asChild>
              <Link
                params={{ reviewId: String(review.id) }}
                state={routeBackState(location, t('common.review'))}
                to="/reviews/$reviewId/edit"
              >
                <PencilLine className="size-4" /> {t('common.edit')}
              </Link>
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setDeleteOpen(true);
              }}
            >
              <Trash2 className="size-4" /> {t('common.delete')}
            </Button>
          </>
        ) : undefined
      }
      description={review.subject?.display_title || review.subject?.title || t('reviewViewer.publicReview')}
      eyebrow={t('reviewViewer.publicReview')}
      headerMode="context"
      leading={
        <Button asChild aria-label={t('common.back')} size="icon-sm" tooltip={t('common.back')} variant="ghost">
          <Link {...resolvedRouteHref(backTarget)}>
            <ArrowLeft className="size-4" />
          </Link>
        </Button>
      }
      title={review.title}
      width="reader"
    >
      <article aria-labelledby={reviewTitleId} className="mx-auto grid w-full max-w-3xl min-w-0 gap-6">
        <DetailHeader
          badges={
            <>
              <Badge variant={review.is_public ? 'accent' : 'secondary'}>
                {review.is_public ? t('common.public') : t('common.private')}
              </Badge>
              {review.is_spoiler ? (
                <Badge>
                  <ShieldAlert className="size-3" /> {t('common.spoiler')}
                </Badge>
              ) : null}
            </>
          }
          description={
            review.subject ? (
              <Link
                className="font-medium text-[var(--ui-accent-text)] hover:underline"
                to={routes.entity(review.subject.id)}
              >
                {review.subject.display_title || review.subject.title}
              </Link>
            ) : (
              t('reviewViewer.publicReview')
            )
          }
          meta={
            <>
              {review.user.id ? (
                <Link to={routes.userProfile(review.user.id)}>
                  <Avatar alt={review.user.nickname || t('common.anonymous')} src={review.user.avatar} />
                </Link>
              ) : (
                <Avatar />
              )}
              <div className="min-w-0">
                {review.user.id ? (
                  <Link
                    className="block truncate text-sm font-semibold text-foreground hover:text-[var(--ui-accent-text)]"
                    to={routes.userProfile(review.user.id)}
                  >
                    {review.user.nickname || t('common.anonymous')}
                  </Link>
                ) : (
                  <p className="truncate text-sm font-semibold text-foreground">{t('common.anonymous')}</p>
                )}
                <time className="block text-xs text-muted-foreground" dateTime={reviewDate}>
                  {formatDate(reviewDate)}
                </time>
              </div>
            </>
          }
          title={review.title}
          titleId={reviewTitleId}
        />
        <SensitiveContent
          contentLabel={t('common.spoiler')}
          isSensitive={review.is_spoiler}
          revealLabel={t('common.revealSpoiler')}
        >
          <DetailBody>
            <MarkdownRenderer content={review.content} />
          </DetailBody>
        </SensitiveContent>
        <DetailFooter>
          <CommunityTargetActions
            presentation="inline"
            reactionCount={numberMeta(review.reaction_count)}
            reportLabel={t('community.reportReview')}
            targetId={review.id}
            targetType="review"
            viewerState={review.viewer_state}
          />
        </DetailFooter>
      </article>
      {publicReview ? (
        <div className="mx-auto mt-6 w-full max-w-3xl border-t border-border-subtle pt-6" data-slot="detail-comments">
          <CommunityCommentsSection
            currentPage={commentsPage}
            targetType="review"
            targetId={review.id}
            onPageChange={(page) =>
              void navigate({ search: (current) => ({ ...current, review_comments_page: page }) })
            }
          />
        </div>
      ) : null}
      <ReviewDeleteDialog
        isPending={deleteReviewMutation.isPending}
        open={deleteOpen}
        reviewTitle={review.title}
        onConfirm={() => {
          if (!deleteReviewMutation.isPending) deleteReviewMutation.mutate(review.id);
        }}
        onOpenChange={setDeleteOpen}
      />
    </Page>
  );
}
