import { formatDate } from '@/shared/lib/date';
import { type SyntheticEvent, useEffect, useMemo, useState } from 'react';
import { getRouteApi, Link, useLocation } from '@tanstack/react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { EyeOff, FileText, PencilLine, Trash2 } from 'lucide-react';
import { toast } from '@/shared/ui/toast';
import { libraryMutations, libraryQueries } from '@/entities/library';
import { useAuth } from '@/entities/session';
import { invalidateReviewViews, ReviewDeleteDialog } from '@/features/reviews';
import { useI18n } from '@/shared/i18n';
import type { Review } from '@/shared/api';
import { routes } from '@/shared/routing/paths';
import type { ReviewsSearch } from '@/shared/routing/route-search';
import type { RouteBackState } from '@/shared/routing/route-state';
import { routeBackState } from '@/shared/routing/route-state';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import {
  ContentRow,
  ContentRowActions,
  ContentRowExcerpt,
  ContentRowHeading,
  ContentRowMain,
  ContentRowMedia,
  ContentRowMeta,
  ContentRowReference,
  ContentRowTitle,
} from '@/shared/ui/ContentRow';
import {
  DataToolbar,
  DataToolbarPrimary,
  DataToolbarRow,
  ListSurface,
  ResultsMeta,
  ResultsState,
  SearchField,
  type ResultsStatus,
} from '@/shared/ui/DataView';
import { FilterMenu } from '@/shared/ui/FilterMenu';
import { Page } from '@/shared/ui/Page';
import { Pagination } from '@/shared/ui/Pagination';
import { SpoilerText } from '@/shared/ui/SpoilerText';

const pageSize = 12;
const reviewsRoute = getRouteApi('/reviews');
type ReviewOrdering = NonNullable<ReviewsSearch['ordering']>;

function reviewSubjectTitle(
  review: { subject?: { display_title?: string | null; title?: string | null; title_cn?: string | null } },
  fallback: string,
) {
  return review.subject?.display_title || review.subject?.title || review.subject?.title_cn || fallback;
}

function ReviewCard({
  review,
  isDeleting,
  onDelete,
  state,
}: {
  review: Review;
  isDeleting: boolean;
  onDelete: () => void;
  state: RouteBackState;
}) {
  const { t } = useI18n();
  const subjectTitle = reviewSubjectTitle(review, t('common.untitledSubject'));
  const cover = review.subject?.image_thumbnail || review.subject?.image;

  return (
    <ContentRow>
      <ContentRowMedia>
        {review.subject ? (
          <Link
            aria-label={subjectTitle}
            params={{ subjectId: review.subject.id }}
            state={state}
            to="/entities/$subjectId"
          >
            {cover ? (
              <img alt="" decoding="async" loading="lazy" referrerPolicy="no-referrer" src={cover} />
            ) : (
              <span>
                <FileText className="size-5" />
              </span>
            )}
          </Link>
        ) : (
          <Link
            aria-label={review.title}
            params={{ reviewId: String(review.id) }}
            state={state}
            to="/reviews/$reviewId"
          >
            <span>
              <FileText className="size-5" />
            </span>
          </Link>
        )}
      </ContentRowMedia>
      <ContentRowMain>
        <ContentRowMeta>
          <Badge variant={review.is_public ? 'accent' : 'secondary'}>
            {review.is_public ? t('common.public') : t('common.private')}
          </Badge>
          {review.is_spoiler ? (
            <Badge>
              <EyeOff className="size-3" />
              {t('common.spoiler')}
            </Badge>
          ) : null}
          <span>{formatDate(review.updated_at || review.created_at, t('common.noDate'))}</span>
        </ContentRowMeta>
        <ContentRowHeading>
          <ContentRowTitle>
            <Link params={{ reviewId: String(review.id) }} state={state} to="/reviews/$reviewId">
              {review.title}
            </Link>
          </ContentRowTitle>
          <ContentRowActions>
            <Button
              asChild
              aria-label={`${t('common.edit')} ${review.title}`}
              size="icon"
              tooltip={t('common.edit')}
              type="button"
              variant="ghost"
            >
              <Link params={{ reviewId: String(review.id) }} state={state} to="/reviews/$reviewId/edit">
                <PencilLine className="size-4" />
              </Link>
            </Button>
            <Button
              aria-label={`${t('common.delete')} ${review.title}`}
              disabled={isDeleting}
              size="icon"
              tooltip={t('common.delete')}
              type="button"
              variant="ghost"
              onClick={() => {
                onDelete();
              }}
            >
              <Trash2 className="size-4" />
            </Button>
          </ContentRowActions>
        </ContentRowHeading>
        {review.subject ? (
          <ContentRowReference>
            <Link params={{ subjectId: review.subject.id }} state={state} to="/entities/$subjectId">
              <span>{subjectTitle}</span>
              {review.subject.subject_type ? <small>{review.subject.subject_type}</small> : null}
            </Link>
          </ContentRowReference>
        ) : null}
        <ContentRowExcerpt>
          <SpoilerText isSpoiler={review.is_spoiler} revealLabel={t('common.revealSpoiler')}>
            {review.content || t('common.noContent')}
          </SpoilerText>
        </ContentRowExcerpt>
      </ContentRowMain>
    </ContentRow>
  );
}

export function ReviewsPage() {
  const { t } = useI18n();
  const auth = useAuth();
  const location = useLocation();
  const navigate = reviewsRoute.useNavigate();
  const search = reviewsRoute.useSearch();
  const keyword = search.keyword ?? '';
  const ordering = search.ordering ?? '-created_at';
  const currentPage = search.page ?? 1;
  const routeState = routeBackState(location, t('nav.reviews'));
  const [draftKeyword, setDraftKeyword] = useState(keyword);
  const [deleteTarget, setDeleteTarget] = useState<Review | null>(null);
  const queryClient = useQueryClient();
  const orderingOptions: Array<{ label: string; value: ReviewOrdering }> = [
    { label: t('reviews.sortNewest'), value: '-created_at' },
    { label: t('reviews.sortOldest'), value: 'created_at' },
    { label: t('reviews.sortRecentlyCreated'), value: '-id' },
    { label: t('reviews.sortEarliestCreated'), value: 'id' },
  ];

  const query = useMemo(
    () => ({
      ...(keyword ? { keyword } : {}),
      ordering,
      page: currentPage,
      page_size: pageSize,
    }),
    [currentPage, keyword, ordering],
  );
  const reviewsQuery = useQuery(libraryQueries.reviews(query));
  const deleteReviewMutation = useMutation({
    ...libraryMutations.deleteReview(),
    onError: () => toast.error(t('common.requestFailed')),
    onSuccess: async () => {
      setDeleteTarget(null);
      await invalidateReviewViews(queryClient, {
        includeComments: true,
        userId: auth.profile?.user_id,
      });
      toast.success(t('reviews.deleted'));
    },
  });
  const reviews = reviewsQuery.data?.results ?? [];
  const totalCount = reviewsQuery.data?.count ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const resultsStatus: ResultsStatus =
    reviewsQuery.data === undefined && reviewsQuery.isLoading
      ? 'loading'
      : reviewsQuery.data === undefined && reviewsQuery.isError
        ? 'error'
        : reviews.length === 0
          ? 'empty'
          : 'ready';

  useEffect(() => {
    setDraftKeyword(keyword);
  }, [keyword]);

  useEffect(() => {
    if (reviewsQuery.data && currentPage > totalPages) {
      void navigate({ replace: true, search: (current) => ({ ...current, page: totalPages }) });
    }
  }, [currentPage, navigate, reviewsQuery.data, totalPages]);

  function updateOrdering(value: ReviewOrdering) {
    void navigate({ search: (current) => ({ ...current, ordering: value, page: undefined }) });
  }

  function handleSubmit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    void navigate({
      search: (current) => ({ ...current, keyword: draftKeyword.trim() || undefined, page: undefined }),
    });
  }

  function goToPage(page: number) {
    void navigate({ search: (current) => ({ ...current, page: Math.min(Math.max(page, 1), totalPages) }) });
  }

  return (
    <Page title={t('reviews.title')} eyebrow={t('nav.groupLibrary')}>
      <div className="grid gap-5">
        <DataToolbar onSubmit={handleSubmit}>
          <DataToolbarRow className="lg:grid-cols-[minmax(0,1fr)_190px_auto]">
            <DataToolbarPrimary>
              <SearchField
                aria-label={t('reviews.searchPlaceholder')}
                maxLength={200}
                value={draftKeyword}
                placeholder={t('reviews.searchPlaceholder')}
                onChange={(event) => {
                  setDraftKeyword(event.target.value);
                }}
              />
            </DataToolbarPrimary>
            <FilterMenu
              label={t('common.sort')}
              options={orderingOptions}
              size="lg"
              value={ordering}
              onChange={updateOrdering}
            />
            <Button size="lg" type="submit" variant="secondary">
              {t('common.search')}
            </Button>
          </DataToolbarRow>
        </DataToolbar>

        <ResultsMeta
          count={reviewsQuery.data?.count}
          label={t('common.reviews')}
          pending={reviewsQuery.isFetching && !reviewsQuery.isLoading}
          pendingLabel={t('common.loading')}
        />

        <ResultsState
          emptyAction={
            <Button asChild size="sm" type="button" variant="secondary">
              <Link to={routes.search}>{t('nav.search')}</Link>
            </Button>
          }
          emptyDescription={t('reviews.emptyBody')}
          emptyTitle={t('reviews.emptyTitle')}
          errorDescription={t('search.errorBody')}
          errorTitle={t('reviews.errorTitle')}
          loadingTitle={t('reviews.loading')}
          status={resultsStatus}
        >
          <>
            <ListSurface>
              {reviews.map((review) => (
                <ReviewCard
                  key={review.id}
                  review={review}
                  isDeleting={deleteReviewMutation.isPending && deleteReviewMutation.variables === review.id}
                  state={routeState}
                  onDelete={() => {
                    setDeleteTarget(review);
                  }}
                />
              ))}
            </ListSurface>
            <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={goToPage} />
          </>
        </ResultsState>

        <ReviewDeleteDialog
          isPending={deleteReviewMutation.isPending}
          open={deleteTarget !== null}
          reviewTitle={deleteTarget?.title}
          onConfirm={() => {
            if (deleteTarget && !deleteReviewMutation.isPending) deleteReviewMutation.mutate(deleteTarget.id);
          }}
          onOpenChange={(open) => {
            if (!open) setDeleteTarget(null);
          }}
        />
      </div>
    </Page>
  );
}
