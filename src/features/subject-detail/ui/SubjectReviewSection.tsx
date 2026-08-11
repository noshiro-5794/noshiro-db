import { useId } from 'react';
import { Link } from '@tanstack/react-router';
import { PencilLine, Plus, ShieldAlert } from 'lucide-react';
import type { Review, UUID } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import type { RouteBackState } from '@/shared/routing/route-state';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { DetailSection } from '@/shared/ui/Detail';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';

export function SubjectReviewSection({
  canCreateReview,
  className,
  detailLinkState,
  isError,
  isLoading,
  onRetry,
  reviews,
  subjectId,
}: {
  canCreateReview: boolean;
  className?: string;
  detailLinkState: RouteBackState;
  isError: boolean;
  isLoading: boolean;
  onRetry: () => void;
  reviews: Review[];
  subjectId: UUID;
}) {
  const { t } = useI18n();
  const titleId = useId();
  const createAction = canCreateReview ? (
    <Button asChild size="sm" variant="secondary">
      <Link search={{ subjectId }} state={detailLinkState} to="/reviews/new">
        <Plus aria-hidden="true" />
        {t('subject.newReview')}
      </Link>
    </Button>
  ) : (
    <Button disabled size="sm" type="button" variant="secondary">
      <Plus aria-hidden="true" />
      {t('subject.newReview')}
    </Button>
  );

  return (
    <DetailSection
      actions={createAction}
      className={className}
      id="reviews"
      meta={`${reviews.length} ${t('common.items')}`}
      title={t('reviews.title')}
      titleId={titleId}
    >
      {isLoading ? <LoadingState title={t('reviews.loading')} /> : null}
      {isError ? (
        <ErrorState
          action={
            <Button size="sm" variant="secondary" onClick={onRetry}>
              {t('common.retry')}
            </Button>
          }
          description={t('common.requestFailed')}
          title={t('reviews.errorTitle')}
        />
      ) : null}
      {!isLoading && !isError && reviews.length ? (
        <ul className="m-0 list-none divide-y divide-border-subtle rounded-sm bg-[color-mix(in_srgb,var(--ui-bg-subtle)_48%,transparent)] px-3 py-0">
          {reviews.map((review) => (
            <li key={review.id}>
              <article className="grid min-w-0 gap-2 py-3" data-slot="subject-review-row">
                <div className="flex min-w-0 items-start justify-between gap-3">
                  <div className="min-w-0">
                    <Link
                      className="block truncate text-sm font-semibold text-foreground transition-colors hover:text-[var(--ui-accent-text)]"
                      params={{ reviewId: String(review.id) }}
                      state={detailLinkState}
                      to="/reviews/$reviewId"
                    >
                      {review.title}
                    </Link>
                    <p className="mt-1 line-clamp-2 text-sm leading-6 text-muted-foreground">{review.content}</p>
                  </div>
                  <Button
                    asChild
                    aria-label={`${t('common.edit')} ${review.title}`}
                    size="icon-sm"
                    tooltip={t('common.edit')}
                    variant="ghost"
                  >
                    <Link params={{ reviewId: String(review.id) }} state={detailLinkState} to="/reviews/$reviewId/edit">
                      <PencilLine aria-hidden="true" />
                    </Link>
                  </Button>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  <Badge>{review.is_public ? t('common.public') : t('common.private')}</Badge>
                  {review.is_spoiler ? (
                    <Badge variant="warning">
                      <ShieldAlert aria-hidden="true" />
                      {t('common.spoiler')}
                    </Badge>
                  ) : null}
                </div>
              </article>
            </li>
          ))}
        </ul>
      ) : null}
      {!isLoading && !isError && reviews.length === 0 ? <EmptyState title={t('common.none')} /> : null}
    </DetailSection>
  );
}
