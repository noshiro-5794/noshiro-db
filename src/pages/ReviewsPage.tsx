import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { EyeOff, PencilLine, Search, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { CommunityContentCard } from '@/features/community/components/CommunityContentCard';
import { libraryMutations, libraryQueries, libraryQueryKeys } from '@/features/library/library-queries';
import { useI18n } from '@/features/i18n/use-i18n';
import { routes } from '@/routes/paths';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { FilterMenu } from '@/shared/ui/FilterMenu';
import { Input } from '@/shared/ui/Input';
import { Page } from '@/shared/ui/Page';
import { Pagination } from '@/shared/ui/Pagination';

const pageSize = 12;
const coverPlaceholder = '/assets/placeholders/subject-cover.png';

function formatDate(value: string | undefined, fallback: string) {
  if (!value) return fallback;
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
}

function reviewSubjectTitle(review: { subject?: { display_title?: string | null; title?: string | null; title_cn?: string | null } }, fallback: string) {
  return review.subject?.display_title || review.subject?.title || review.subject?.title_cn || fallback;
}

export function ReviewsPage() {
  const { t } = useI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const keyword = searchParams.get('keyword') ?? '';
  const ordering = searchParams.get('ordering') ?? '-created_at';
  const currentPage = Math.max(1, Number(searchParams.get('page') ?? '1') || 1);
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
    if (currentPage > totalPages) {
      setSearchParams((currentParams) => {
        const nextParams = new URLSearchParams(currentParams);
        nextParams.set('page', String(totalPages));
        return nextParams;
      });
    }
  }, [currentPage, setSearchParams, totalPages]);

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
    <Page title={t('reviews.title')} eyebrow={t('nav.groupMarked')} description={t('reviews.description')}>
      <form className="reviews-toolbar" onSubmit={handleSubmit}>
        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_190px_auto]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-neutral-400" />
            <Input className="pl-9" value={draftKeyword} placeholder={t('reviews.searchPlaceholder')} onChange={(event) => setDraftKeyword(event.target.value)} />
          </div>
          <FilterMenu label={t('common.sort')} options={orderingOptions} value={ordering} onChange={(value) => updateSearchParam('ordering', value)} />
          <Button type="submit">{t('common.search')}</Button>
        </div>
      </form>

      <div className="grid gap-4">
        <div className="flex items-center justify-between gap-3 text-sm text-neutral-500 dark:text-neutral-400">
          <span>{totalCount} {t('common.reviews')}</span>
          {reviewsQuery.isFetching ? <span>{t('common.loading')}</span> : null}
        </div>

        {reviewsQuery.isLoading ? <LoadingState title={t('reviews.loading')} /> : null}
        {reviewsQuery.isError ? <ErrorState title={t('reviews.errorTitle')} description={t('search.errorBody')} /> : null}
        {!reviewsQuery.isLoading && !reviewsQuery.isError && reviewsQuery.data?.results.length === 0 ? (
          <EmptyState
            title={t('reviews.emptyTitle')}
            description={t('reviews.emptyBody')}
            action={(
              <Button asChild size="sm" type="button" variant="secondary">
                <Link to={routes.search}>{t('nav.search')}</Link>
              </Button>
            )}
          />
        ) : null}

        <div className="review-list">
          {(reviewsQuery.data?.results ?? []).map((review) => (
            <CommunityContentCard
            actions={(
              <>
                <Button asChild aria-label={`${t('common.edit')} ${review.title}`} size="icon" type="button" variant="ghost">
                  <Link to={routes.reviewEdit(review.id)}>
                    <PencilLine className="size-4" />
                  </Link>
                </Button>
                <Button
                  aria-label={`${t('common.delete')} ${review.title}`}
                  disabled={deleteReviewMutation.isPending}
                  size="icon"
                  type="button"
                  variant="ghost"
                  onClick={() => deleteReviewMutation.mutate(review.id)}
                >
                  <Trash2 className="size-4" />
                </Button>
              </>
            )}
            badges={(
              <>
                <Badge variant={review.is_public ? 'accent' : 'secondary'}>{review.is_public ? t('common.public') : t('common.private')}</Badge>
                {review.is_spoiler ? (
                  <Badge>
                    <EyeOff className="size-3" />
                    {t('common.spoiler')}
                  </Badge>
                ) : null}
              </>
            )}
            body={review.content || t('common.noContent')}
            cover={review.subject?.image_thumbnail || review.subject?.image || coverPlaceholder}
            date={formatDate(review.updated_at || review.created_at, t('common.noDate'))}
            href={routes.review(review.id)}
            isSpoiler={review.is_spoiler}
            key={review.id}
            subject={review.subject ? {
              href: routes.subject(review.subject.id),
              title: reviewSubjectTitle(review, t('common.untitledSubject')),
            } : undefined}
            title={review.title}
            typeLabel={t('community.targetType.review')}
            />
          ))}
        </div>

        <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={goToPage} />
      </div>
    </Page>
  );
}
