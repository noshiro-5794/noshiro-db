import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useSearchParams } from '@/shared/routing/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { EyeOff, FileText, PencilLine, Search, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { libraryMutations, libraryQueries, libraryQueryKeys } from '@/entities/library';
import { useI18n } from '@/shared/i18n';
import type { Review } from '@/shared/api';
import { routes } from '@/shared/routing/paths';
import type { RouteBackState } from '@/shared/routing/route-state';
import { routeBackState } from '@/shared/routing/route-state';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { FilterMenu } from '@/shared/ui/FilterMenu';
import { Input } from '@/shared/ui/Input';
import { Page } from '@/shared/ui/Page';
import { Pagination } from '@/shared/ui/Pagination';

const pageSize = 12;

function formatDate(value: string | undefined, fallback: string) {
  if (!value) return fallback;
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
}

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
  onDelete: (reviewId: number) => void;
  state: RouteBackState;
}) {
  const { t } = useI18n();
  const subjectTitle = reviewSubjectTitle(review, t('common.untitledSubject'));
  const cover = review.subject?.image_thumbnail || review.subject?.image;

  return (
    <article className="review-showcase-card">
      <Link
        className="review-showcase-cover"
        state={state}
        to={review.subject ? routes.subject(review.subject.id) : routes.review(review.id)}
      >
        {cover ? (
          <img src={cover} alt="" loading="lazy" />
        ) : (
          <span>
            <FileText className="size-5" />
          </span>
        )}
      </Link>
      <div className="review-showcase-main">
        <div className="review-showcase-meta">
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
        </div>
        <div className="review-showcase-heading">
          <Link className="review-showcase-title" state={state} to={routes.review(review.id)}>
            {review.title}
          </Link>
          <div className="review-showcase-actions">
            <Button
              asChild
              aria-label={`${t('common.edit')} ${review.title}`}
              size="icon"
              type="button"
              variant="ghost"
            >
              <Link state={state} to={routes.reviewEdit(review.id)}>
                <PencilLine className="size-4" />
              </Link>
            </Button>
            <Button
              aria-label={`${t('common.delete')} ${review.title}`}
              disabled={isDeleting}
              size="icon"
              type="button"
              variant="ghost"
              onClick={() => onDelete(review.id)}
            >
              <Trash2 className="size-4" />
            </Button>
          </div>
        </div>
        {review.subject ? (
          <Link className="review-showcase-subject" state={state} to={routes.subject(review.subject.id)}>
            <span>{subjectTitle}</span>
            {review.subject.subject_type ? <small>{review.subject.subject_type}</small> : null}
          </Link>
        ) : null}
        <p className={`review-showcase-body ${review.is_spoiler ? 'is-spoiler' : ''}`}>
          {review.content || t('common.noContent')}
        </p>
      </div>
    </article>
  );
}

export function ReviewsPage() {
  const { t } = useI18n();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const keyword = searchParams.get('keyword') ?? '';
  const ordering = searchParams.get('ordering') ?? '-created_at';
  const currentPage = Math.max(1, Number(searchParams.get('page') ?? '1') || 1);
  const routeState = routeBackState(location, t('nav.reviews'));
  const [draftKeyword, setDraftKeyword] = useState(keyword);
  const queryClient = useQueryClient();
  const orderingOptions = [
    { label: t('reviews.sortNewest'), value: '-created_at' },
    { label: t('reviews.sortOldest'), value: 'created_at' },
    { label: t('reviews.sortRecentlyCreated'), value: '-id' },
    { label: t('reviews.sortEarliestCreated'), value: 'id' },
  ];

  const query = useMemo(
    () => ({
      keyword: keyword || undefined,
      ordering: ordering as 'created_at' | '-created_at' | 'id' | '-id',
      page: currentPage,
      page_size: pageSize,
    }),
    [currentPage, keyword, ordering],
  );
  const reviewsQuery = useQuery(libraryQueries.reviews(query));
  const deleteReviewMutation = useMutation({
    ...libraryMutations.deleteReview(),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: libraryQueryKeys.reviews() });
      toast.success(t('reviews.deleted'));
    },
  });
  const totalCount = reviewsQuery.data?.count ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  useEffect(() => {
    setDraftKeyword(keyword);
  }, [keyword]);

  useEffect(() => {
    if (reviewsQuery.data && currentPage > totalPages) {
      setSearchParams((currentParams) => {
        const nextParams = new URLSearchParams(currentParams);
        nextParams.set('page', String(totalPages));
        return nextParams;
      });
    }
  }, [currentPage, reviewsQuery.data, setSearchParams, totalPages]);

  function updateSearchParam(key: string, value: string) {
    setSearchParams((currentParams) => {
      const nextParams = new URLSearchParams(currentParams);
      if (value) nextParams.set(key, value);
      else nextParams.delete(key);
      if (key !== 'page') nextParams.delete('page');
      return nextParams;
    });
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    updateSearchParam('keyword', draftKeyword.trim());
  }

  function goToPage(page: number) {
    updateSearchParam('page', String(Math.min(Math.max(page, 1), totalPages)));
  }

  return (
    <Page title={t('reviews.title')} eyebrow={t('nav.groupLibrary')}>
      <div className="grid gap-5">
        <form className="content-toolbar" onSubmit={handleSubmit}>
          <div className="content-toolbar-grid is-review">
            <div className="content-toolbar-search">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-neutral-400" />
              <Input
                className="pl-9"
                value={draftKeyword}
                placeholder={t('reviews.searchPlaceholder')}
                onChange={(event) => setDraftKeyword(event.target.value)}
              />
            </div>
            <FilterMenu
              label={t('common.sort')}
              options={orderingOptions}
              value={ordering}
              onChange={(value) => updateSearchParam('ordering', value)}
            />
            <Button type="submit" variant="secondary">
              {t('common.search')}
            </Button>
          </div>
        </form>

        <div className="content-summary-bar">
          <div className="content-summary-count">
            <span className="content-summary-number">{totalCount}</span>
            <span>{t('common.reviews')}</span>
          </div>
          <div className="content-summary-side">
            {reviewsQuery.isFetching ? <span>{t('common.loading')}</span> : null}
            <span className="content-summary-page">
              {t('common.page')} {currentPage} / {totalPages}
            </span>
          </div>
        </div>

        {reviewsQuery.isLoading ? <LoadingState title={t('reviews.loading')} /> : null}
        {reviewsQuery.isError ? (
          <ErrorState title={t('reviews.errorTitle')} description={t('search.errorBody')} />
        ) : null}
        {!reviewsQuery.isLoading && !reviewsQuery.isError && reviewsQuery.data?.results.length === 0 ? (
          <EmptyState
            title={t('reviews.emptyTitle')}
            description={t('reviews.emptyBody')}
            action={
              <Button asChild size="sm" type="button" variant="secondary">
                <Link to={routes.search}>{t('nav.search')}</Link>
              </Button>
            }
          />
        ) : null}

        <div className="review-list">
          {(reviewsQuery.data?.results ?? []).map((review) => (
            <ReviewCard
              key={review.id}
              review={review}
              isDeleting={deleteReviewMutation.isPending}
              state={routeState}
              onDelete={(reviewId) => deleteReviewMutation.mutate(reviewId)}
            />
          ))}
        </div>

        <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={goToPage} />
      </div>
    </Page>
  );
}
