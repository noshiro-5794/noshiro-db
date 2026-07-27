import { type FormEvent, useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from '@/shared/routing/navigation';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, BookOpen, FileText, Library, Search, SlidersHorizontal } from 'lucide-react';
import { useI18n } from '@/shared/i18n';
import { PublicCollectionPackCard, PublicReviewItem, PublicSubjectListItem } from '@/widgets/public-content';
import { publicUserQueries } from '@/entities/user';
import type { PrimarySubjectType, UserSubjectStatus } from '@/shared/api';
import { routes } from '@/shared/routing/paths';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { FilterMenu } from '@/shared/ui/FilterMenu';
import { Input } from '@/shared/ui/Input';
import { Page } from '@/shared/ui/Page';
import { Pagination } from '@/shared/ui/Pagination';

const pageSize = 12;

type PublicUserContentMode = 'reviews' | 'subjects' | 'collections';

type PublicUserContentPageProps = {
  mode: PublicUserContentMode;
};

function modeTitle(mode: PublicUserContentMode, t: ReturnType<typeof useI18n>['t']) {
  if (mode === 'reviews') return t('profile.allReviewsTitle');
  if (mode === 'subjects') return t('profile.allSubjectsTitle');
  return t('profile.allCollectionsTitle');
}

function modeEmptyTitle(mode: PublicUserContentMode, t: ReturnType<typeof useI18n>['t']) {
  if (mode === 'reviews') return t('profile.noReviewsTitle');
  if (mode === 'subjects') return t('profile.noSubjectsTitle');
  return t('profile.noCollectionsTitle');
}

function modeEmptyBody(mode: PublicUserContentMode, t: ReturnType<typeof useI18n>['t']) {
  if (mode === 'reviews') return t('profile.noReviewsBody');
  if (mode === 'subjects') return t('profile.noSubjectsBody');
  return t('profile.noCollectionsBody');
}

function modeIcon(mode: PublicUserContentMode) {
  if (mode === 'reviews') return <FileText className="size-4" />;
  if (mode === 'subjects') return <Library className="size-4" />;
  return <BookOpen className="size-4" />;
}

function modeCountLabel(mode: PublicUserContentMode, t: ReturnType<typeof useI18n>['t']) {
  if (mode === 'reviews') return t('common.reviews');
  if (mode === 'subjects') return t('common.subjects');
  return t('nav.collections');
}

function toolbarClass(mode: PublicUserContentMode) {
  if (mode === 'subjects') return 'content-toolbar-grid is-library';
  return 'content-toolbar-grid is-review';
}

function defaultOrderingOf(mode: PublicUserContentMode) {
  if (mode === 'subjects') return '-updated_at';
  if (mode === 'reviews') return '-created_at';
  return '-id';
}

export function PublicUserContentPage({ mode }: PublicUserContentPageProps) {
  const { t } = useI18n();
  const params = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const userId = Number(params.userId);
  const isValidUserId = Number.isFinite(userId) && userId > 0;
  const keyword = searchParams.get('keyword') ?? '';
  const status = searchParams.get('status') ?? '';
  const subjectType = (searchParams.get('subject_type') ?? '') as PrimarySubjectType | '';
  const ordering = searchParams.get('ordering') ?? defaultOrderingOf(mode);
  const currentPage = Math.max(1, Number(searchParams.get('page') ?? '1') || 1);
  const [draftKeyword, setDraftKeyword] = useState(keyword);

  const reviewOrderingOptions = [
    { label: t('reviews.sortNewest'), value: '-created_at' },
    { label: t('reviews.sortOldest'), value: 'created_at' },
    { label: t('reviews.sortRecentlyCreated'), value: '-id' },
    { label: t('reviews.sortEarliestCreated'), value: 'id' },
  ];
  const statusOptions: Array<{ label: string; value: UserSubjectStatus | '' }> = [
    { label: t('status.all'), value: '' },
    { label: t('status.wish'), value: 'wish' },
    { label: t('status.doing'), value: 'doing' },
    { label: t('status.done'), value: 'done' },
    { label: t('status.onHold'), value: 'on_hold' },
    { label: t('status.drop'), value: 'drop' },
  ];
  const typeOptions: Array<{ label: string; value: PrimarySubjectType | '' }> = [
    { label: t('search.all'), value: '' },
    { label: t('search.anime'), value: 'anime' },
    { label: t('search.galgame'), value: 'galgame' },
  ];
  const subjectOrderingOptions = [
    { label: t('library.sortRecentlyUpdated'), value: '-updated_at' },
    { label: t('library.sortRecentlyAdded'), value: '-created_at' },
    { label: t('library.sortRatingHigh'), value: '-rating' },
    { label: t('library.sortRatingLow'), value: 'rating' },
    { label: t('library.sortSimpleRatingHigh'), value: '-simple_rating' },
    { label: t('library.sortRecentlyFinished'), value: '-watch_end_date' },
    { label: t('library.sortStartedRecently'), value: '-watch_start_date' },
  ];
  const collectionOrderingOptions = [
    { label: t('collections.sortNewest'), value: '-id' },
    { label: t('collections.sortOldest'), value: 'id' },
    { label: t('collections.sortNameAsc'), value: 'name' },
    { label: t('collections.sortNameDesc'), value: '-name' },
    { label: t('collections.sortMostItems'), value: '-item_count' },
    { label: t('collections.sortHighestRating'), value: '-simple_rating' },
  ];
  const orderingOptions =
    mode === 'reviews'
      ? reviewOrderingOptions
      : mode === 'subjects'
        ? subjectOrderingOptions
        : collectionOrderingOptions;

  const profileQuery = useQuery({ ...publicUserQueries.publicProfile(userId), enabled: isValidUserId });
  const reviewsQuery = useQuery({
    ...publicUserQueries.publicReviews(userId, {
      keyword: keyword || undefined,
      ordering: ordering as 'created_at' | '-created_at' | 'id' | '-id',
      page: currentPage,
      page_size: pageSize,
    }),
    enabled: isValidUserId && mode === 'reviews',
  });
  const subjectsQuery = useQuery({
    ...publicUserQueries.publicSubjects(userId, {
      keyword: keyword || undefined,
      status: status || undefined,
      subject_type: subjectType || undefined,
      ordering,
      page: currentPage,
      page_size: pageSize,
    }),
    enabled: isValidUserId && mode === 'subjects',
  });
  const collectionsQuery = useQuery({
    ...publicUserQueries.publicCollections(userId, {
      keyword: keyword || undefined,
      ordering: ordering as
        'id' | '-id' | 'name' | '-name' | 'simple_rating' | '-simple_rating' | 'item_count' | '-item_count',
      page: currentPage,
      page_size: pageSize,
    }),
    enabled: isValidUserId && mode === 'collections',
  });

  const activeQuery = mode === 'reviews' ? reviewsQuery : mode === 'subjects' ? subjectsQuery : collectionsQuery;
  const totalCount = activeQuery.data?.count ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  useEffect(() => {
    setDraftKeyword(keyword);
  }, [keyword]);

  useEffect(() => {
    if (activeQuery.data && currentPage > totalPages) {
      setSearchParams((currentParams) => {
        const nextParams = new URLSearchParams(currentParams);
        nextParams.set('page', String(totalPages));
        return nextParams;
      });
    }
  }, [activeQuery.data, currentPage, setSearchParams, totalPages]);

  function updateSearchParam(key: string, value: string) {
    setSearchParams((currentParams) => {
      const nextParams = new URLSearchParams(currentParams);
      if (value) nextParams.set(key, value);
      else nextParams.delete(key);
      if (key !== 'page') nextParams.delete('page');
      return nextParams;
    });
  }

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    updateSearchParam('keyword', draftKeyword.trim());
  }

  function resetFilters() {
    setSearchParams(new URLSearchParams());
  }

  function statusLabel(statusValue: string) {
    return statusOptions.find((option) => option.value === statusValue)?.label ?? statusValue.replaceAll('_', ' ');
  }

  const hasFilters = Boolean(
    keyword || (mode === 'subjects' && (status || subjectType)) || ordering !== defaultOrderingOf(mode),
  );

  if (!isValidUserId) {
    return (
      <Page title={modeTitle(mode, t)} eyebrow={t('profile.title')}>
        <ErrorState title={t('profile.invalidTitle')} description={t('profile.invalidBody')} />
      </Page>
    );
  }

  return (
    <Page
      title={modeTitle(mode, t)}
      eyebrow={t('profile.title')}
      actions={
        <Button asChild type="button" variant="secondary">
          <Link to={routes.userProfile(userId)}>
            <ArrowLeft className="size-4" /> {t('profile.backToProfile')}
          </Link>
        </Button>
      }
    >
      <div className={mode === 'subjects' ? 'grid gap-5 lg:grid-cols-[260px_minmax(0,1fr)]' : 'grid gap-5'}>
        {mode === 'subjects' ? (
          <aside className="grid content-start gap-4">
            <section className="content-filter-panel">
              <div className="content-panel-title">
                <SlidersHorizontal className="size-4 text-neutral-400" />
                <h2>{t('library.status')}</h2>
              </div>
              <div className="grid gap-1">
                {statusOptions.map((option) => (
                  <button
                    className={`content-filter-choice ${status === option.value ? 'is-active' : ''}`}
                    key={option.value || 'all'}
                    type="button"
                    onClick={() => updateSearchParam('status', option.value)}
                  >
                    <span>{option.label}</span>
                  </button>
                ))}
              </div>
            </section>
          </aside>
        ) : null}

        <main className="grid min-w-0 content-start gap-5">
          <form className="content-toolbar" onSubmit={handleSearch}>
            <div className={toolbarClass(mode)}>
              <div className="content-toolbar-search">
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-neutral-400" />
                <Input
                  className="pl-9"
                  value={draftKeyword}
                  placeholder={t('profile.contentSearchPlaceholder')}
                  onChange={(event) => setDraftKeyword(event.target.value)}
                />
              </div>
              {mode === 'subjects' ? (
                <FilterMenu
                  label={t('search.type')}
                  options={typeOptions}
                  value={subjectType}
                  onChange={(value) => updateSearchParam('subject_type', value)}
                />
              ) : null}
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
              <span className="inline-flex items-center gap-2">
                {modeIcon(mode)} {modeCountLabel(mode, t)}
              </span>
              {mode === 'subjects' && status ? <Badge variant="secondary">{statusLabel(status)}</Badge> : null}
              {mode === 'subjects' && subjectType ? <Badge variant="secondary">{subjectType}</Badge> : null}
              {keyword ? <Badge variant="secondary">{keyword}</Badge> : null}
            </div>
            <div className="content-summary-side">
              {activeQuery.isFetching ? <span>{t('common.loading')}</span> : null}
              <span className="content-summary-page">
                {t('common.page')} {currentPage} / {totalPages}
              </span>
              {hasFilters ? (
                <button
                  className="font-semibold text-[var(--color-accent-strong)]"
                  type="button"
                  onClick={resetFilters}
                >
                  {t('common.reset')}
                </button>
              ) : null}
            </div>
          </div>

          {profileQuery.isLoading || activeQuery.isLoading ? (
            <LoadingState title={t('profile.loadingContent')} />
          ) : null}
          {profileQuery.isError || activeQuery.isError ? (
            <ErrorState title={t('profile.contentErrorTitle')} description={t('profile.contentErrorBody')} />
          ) : null}
          {!activeQuery.isLoading && !activeQuery.isError && totalCount === 0 ? (
            <EmptyState title={modeEmptyTitle(mode, t)} description={modeEmptyBody(mode, t)} />
          ) : null}

          {mode === 'reviews' ? (
            <div className="review-list">
              {(reviewsQuery.data?.results ?? []).map((review) => (
                <PublicReviewItem key={review.id} review={review} />
              ))}
            </div>
          ) : null}

          {mode === 'subjects' ? (
            <div className="content-list-panel">
              {(subjectsQuery.data?.results ?? []).map((item) => (
                <PublicSubjectListItem key={item.id} item={item} />
              ))}
            </div>
          ) : null}

          {mode === 'collections' ? (
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
              {(collectionsQuery.data?.results ?? []).map((collection) => (
                <PublicCollectionPackCard key={collection.id} collection={collection} userId={userId} />
              ))}
            </div>
          ) : null}

          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={(page) => updateSearchParam('page', String(page))}
          />
        </main>
      </div>
    </Page>
  );
}
