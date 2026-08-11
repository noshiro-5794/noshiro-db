import { useId, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ShieldAlert } from 'lucide-react';
import { libraryQueries } from '@/entities/library';
import { useAuth } from '@/entities/session';
import type { Review, UUID } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { Link, useLocation } from '@tanstack/react-router';
import { routes } from '@/shared/routing/paths';
import { routeBackState } from '@/shared/routing/route-state';
import type { RouteBackState } from '@/shared/routing/route-state';
import { formatDate } from '@/shared/lib/date';
import { Avatar } from '@/shared/ui/Avatar';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { DetailSection } from '@/shared/ui/Detail';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Pagination } from '@/shared/ui/Pagination';
import { SpoilerText } from '@/shared/ui/SpoilerText';

const pageSize = 8;

export function PublicReviewsSection({
  className,
  subjectId,
  subjectTitle,
}: {
  className?: string;
  subjectId: UUID;
  subjectTitle: string;
}) {
  const { t } = useI18n();
  const auth = useAuth();
  const location = useLocation();
  const sectionTitleId = useId();
  const [page, setPage] = useState(1);
  const query = useQuery(
    libraryQueries.publicSubjectReviews(subjectId, { page, page_size: pageSize, ordering: '-created_at' }),
  );
  const reviews = query.data?.results ?? [];
  const totalPages = Math.max(1, Math.ceil((query.data?.count ?? 0) / pageSize));
  const detailLinkState = routeBackState(location, subjectTitle);

  return (
    <DetailSection
      className={className}
      id="public-reviews"
      meta={query.data ? `${query.data.count} ${t('common.items')}` : undefined}
      title={t('subject.publicReviews')}
      titleId={sectionTitleId}
    >
      {query.isLoading ? <LoadingState title={t('subject.publicReviews')} /> : null}
      {query.isError ? (
        <ErrorState
          action={
            <Button size="sm" variant="secondary" onClick={() => void query.refetch()}>
              {t('common.retry')}
            </Button>
          }
          description={t('common.requestFailed')}
          title={t('subject.publicReviews')}
        />
      ) : null}
      {!query.isLoading && !query.isError && reviews.length > 0 ? (
        <ul className="m-0 list-none divide-y divide-border-subtle p-0">
          {reviews.map((review) => (
            <li key={review.id}>
              <PublicReviewItem
                detailLinkState={detailLinkState}
                isOwnReview={Boolean(
                  review.user?.id && auth.profile?.user_id && review.user.id === auth.profile.user_id,
                )}
                review={review}
              />
            </li>
          ))}
        </ul>
      ) : null}
      {!query.isLoading && !query.isError && reviews.length === 0 ? <EmptyState title={t('common.none')} /> : null}
      {!query.isLoading && !query.isError && reviews.length > 0 ? (
        <Pagination currentPage={page} totalPages={totalPages} onPageChange={setPage} />
      ) : null}
    </DetailSection>
  );
}

function PublicReviewItem({
  detailLinkState,
  isOwnReview,
  review,
}: {
  detailLinkState: RouteBackState;
  isOwnReview: boolean;
  review: Review;
}) {
  const { t } = useI18n();
  const reviewDate = review.updated_at || review.created_at;
  return (
    <article className="py-4 first:pt-0 last:pb-0">
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 items-center gap-3">
          {review.user?.id ? (
            <Link className="group shrink-0 rounded-full" to={routes.userProfile(review.user.id)}>
              <Avatar
                alt={review.user.nickname || t('common.anonymous')}
                className="size-9 transition-shadow group-hover:ring-2 group-hover:ring-[var(--ui-accent-border)]"
                src={review.user.avatar}
              />
            </Link>
          ) : (
            <Avatar className="size-9" />
          )}
          <div className="min-w-0">
            {review.user?.id ? (
              <Link
                className="block truncate text-sm font-semibold text-foreground transition-colors hover:text-[var(--ui-accent-text)]"
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
        </div>
        <div className="flex flex-shrink-0 flex-wrap justify-end gap-2">
          {review.is_spoiler ? (
            <Badge>
              <ShieldAlert aria-hidden="true" className="size-3" /> {t('common.spoiler')}
            </Badge>
          ) : null}
          {isOwnReview ? (
            <Button asChild size="sm" variant="ghost">
              <Link state={detailLinkState} to={routes.reviewEdit(review.id)}>
                {t('common.edit')}
              </Link>
            </Button>
          ) : null}
        </div>
      </div>
      <div className="mt-4">
        <Link className="group/title block w-fit max-w-full" state={detailLinkState} to={routes.review(review.id)}>
          <h3 className="m-0 truncate text-sm font-semibold text-foreground transition-colors group-hover/title:text-[var(--ui-accent-text)]">
            {review.title}
          </h3>
        </Link>
        <div className="mt-2">
          <SpoilerText
            className="line-clamp-3 text-sm leading-6 text-muted-foreground"
            isSpoiler={review.is_spoiler}
            revealLabel={t('common.revealSpoiler')}
          >
            {review.content}
          </SpoilerText>
        </div>
      </div>
    </article>
  );
}
