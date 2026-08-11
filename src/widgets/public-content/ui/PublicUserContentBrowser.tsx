import { type SyntheticEvent, useEffect, useState } from 'react';
import { Link } from '@tanstack/react-router';
import { ArrowLeft, BookOpen, FileText, Library } from 'lucide-react';
import { UserSubjectListItem } from '@/entities/library';
import type { PrimarySubjectType, UserSubjectStatus } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import type { PublicCollectionsSearch, PublicReviewsSearch, PublicSubjectsSearch } from '@/shared/routing/route-search';
import { parseIntegerParam } from '@/shared/routing/search-params';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
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
import { ErrorState } from '@/shared/ui/FeedbackState';
import { FilterMenu } from '@/shared/ui/FilterMenu';
import { Page } from '@/shared/ui/Page';
import { Pagination } from '@/shared/ui/Pagination';
import { usePublicContentData } from '../model/use-public-content-data';
import { PublicCollectionPackCard, PublicReviewItem } from './PublicContentItems';
import { PublicSubjectStatusFilter } from './PublicSubjectStatusFilter';

export type PublicContentSearchKey = 'keyword' | 'ordering' | 'page' | 'status' | 'subject_type';

type CommonProps = {
  onResetSearch: () => void;
  onSearchChange: (key: PublicContentSearchKey, value: string, options?: { replace?: boolean }) => void;
  userIdParam: string;
};

type PublicUserContentBrowserProps = CommonProps &
  (
    | { mode: 'reviews'; search: PublicReviewsSearch }
    | { mode: 'subjects'; search: PublicSubjectsSearch }
    | { mode: 'collections'; search: PublicCollectionsSearch }
  );

type PublicUserContentMode = PublicUserContentBrowserProps['mode'];

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

function defaultOrderingOf(mode: PublicUserContentMode) {
  if (mode === 'subjects') return '-id';
  if (mode === 'reviews') return '-created_at';
  return '-id';
}

export function PublicUserContentBrowser(props: PublicUserContentBrowserProps) {
  const { mode, onResetSearch, onSearchChange, search, userIdParam } = props;
  const { t } = useI18n();
  const userId = parseIntegerParam(userIdParam, { min: 1 }) ?? 0;
  const isValidUserId = userId > 0;
  const keyword = search.keyword ?? '';
  const status = mode === 'subjects' ? (search.status ?? '') : '';
  const subjectType = mode === 'subjects' ? (search.subject_type ?? '') : '';
  const ordering = search.ordering ?? defaultOrderingOf(mode);
  const currentPage = search.page ?? 1;
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
    { label: t('library.sortRecentlyAdded'), value: '-id' },
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
  const { activeQuery, collectionsQuery, reviewsQuery, subjectsQuery, totalCount, totalPages } = usePublicContentData({
    enabled: isValidUserId,
    keyword,
    selection: props,
    userId,
  });
  const hasFilters = Boolean(
    keyword || (mode === 'subjects' && (status || subjectType)) || ordering !== defaultOrderingOf(mode),
  );
  const resultsStatus: ResultsStatus =
    activeQuery.data === undefined && activeQuery.isLoading
      ? 'loading'
      : activeQuery.data === undefined && activeQuery.isError
        ? 'error'
        : totalCount === 0
          ? 'empty'
          : 'ready';

  useEffect(() => {
    setDraftKeyword(keyword);
  }, [keyword]);

  useEffect(() => {
    if (activeQuery.data && currentPage > totalPages) {
      onSearchChange('page', String(totalPages), { replace: true });
    }
  }, [activeQuery.data, currentPage, onSearchChange, totalPages]);

  function submitSearch(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    onSearchChange('keyword', draftKeyword.trim());
  }

  function statusLabel(statusValue: string) {
    return statusOptions.find((option) => option.value === statusValue)?.label ?? statusValue.replaceAll('_', ' ');
  }

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
          <Link params={{ userId: String(userId) }} to="/users/$userId">
            <ArrowLeft className="size-4" /> {t('profile.backToProfile')}
          </Link>
        </Button>
      }
    >
      <div className={mode === 'subjects' ? 'grid gap-5 lg:grid-cols-[260px_minmax(0,1fr)]' : 'grid gap-5'}>
        {mode === 'subjects' ? (
          <PublicSubjectStatusFilter
            status={status}
            onChange={(value) => {
              onSearchChange('status', value);
            }}
          />
        ) : null}

        <div className="grid min-w-0 content-start gap-5">
          <DataToolbar onSubmit={submitSearch}>
            <DataToolbarRow
              className={
                mode === 'subjects'
                  ? 'xl:grid-cols-[minmax(0,1fr)_150px_190px_auto]'
                  : 'lg:grid-cols-[minmax(0,1fr)_190px_auto]'
              }
            >
              <DataToolbarPrimary>
                <SearchField
                  aria-label={t('profile.contentSearchPlaceholder')}
                  maxLength={200}
                  placeholder={t('profile.contentSearchPlaceholder')}
                  value={draftKeyword}
                  onChange={(event) => {
                    setDraftKeyword(event.target.value);
                  }}
                />
              </DataToolbarPrimary>
              {mode === 'subjects' ? (
                <FilterMenu
                  label={t('search.type')}
                  options={typeOptions}
                  size="lg"
                  value={subjectType}
                  onChange={(value) => {
                    onSearchChange('subject_type', value);
                  }}
                />
              ) : null}
              <FilterMenu
                label={t('common.sort')}
                options={orderingOptions}
                size="lg"
                value={ordering}
                onChange={(value) => {
                  onSearchChange('ordering', value);
                }}
              />
              <Button size="lg" type="submit" variant="secondary">
                {t('common.search')}
              </Button>
            </DataToolbarRow>
          </DataToolbar>

          <ResultsMeta
            actions={
              hasFilters ? (
                <Button
                  className="h-7 px-2 font-semibold text-[var(--ui-accent-text)]"
                  size="sm"
                  type="button"
                  variant="ghost"
                  onClick={onResetSearch}
                >
                  {t('common.reset')}
                </Button>
              ) : null
            }
            count={activeQuery.data === undefined ? undefined : totalCount}
            label={
              <span className="inline-flex items-center gap-1.5">
                {modeIcon(mode)} {modeCountLabel(mode, t)}
              </span>
            }
            pending={activeQuery.isFetching && !activeQuery.isLoading}
            pendingLabel={t('common.loading')}
          >
            {mode === 'subjects' && status ? <Badge variant="secondary">{statusLabel(status)}</Badge> : null}
            {mode === 'subjects' && subjectType ? <Badge variant="secondary">{subjectType}</Badge> : null}
            {keyword ? <Badge variant="secondary">{keyword}</Badge> : null}
          </ResultsMeta>

          <ResultsState
            emptyDescription={modeEmptyBody(mode, t)}
            emptyTitle={modeEmptyTitle(mode, t)}
            errorDescription={t('profile.contentErrorBody')}
            errorTitle={t('profile.contentErrorTitle')}
            loadingTitle={t('profile.loadingContent')}
            status={resultsStatus}
          >
            <>
              {mode === 'reviews' ? (
                <ListSurface>
                  {(reviewsQuery.data?.results ?? []).map((review) => (
                    <PublicReviewItem key={review.id} review={review} />
                  ))}
                </ListSurface>
              ) : null}
              {mode === 'subjects' ? (
                <ListSurface>
                  {(subjectsQuery.data?.results ?? []).map((item) => (
                    <UserSubjectListItem key={item.id} item={item} />
                  ))}
                </ListSurface>
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
                onPageChange={(page) => {
                  onSearchChange('page', String(page));
                }}
              />
            </>
          </ResultsState>
        </div>
      </div>
    </Page>
  );
}
