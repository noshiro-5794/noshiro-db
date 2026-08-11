import { useEffect, useMemo } from 'react';
import { getRouteApi, useLocation } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { subjectQueries } from '@/entities/subject';
import {
  buildSubjectSearchQuery,
  filterCalendarItems,
  flattenCalendarGroups,
  SearchFilters,
  SearchResultsGrid,
  sortCalendarItems,
  usesSubjectDatabaseSearch,
} from '@/features/search';
import { useI18n } from '@/shared/i18n';
import { routes } from '@/shared/routing/paths';
import { validateSearchPageSearch, type SearchPageSearch } from '@/shared/routing/route-search';
import { routeBackState } from '@/shared/routing/route-state';
import { Seo } from '@/shared/seo/Seo';
import { ResultsMeta, ResultsState, type ResultsStatus } from '@/shared/ui/DataView';
import { Page } from '@/shared/ui/Page';
import { Pagination } from '@/shared/ui/Pagination';

const pageSize = 30;
const searchRoute = getRouteApi('/search');

export function SearchPage() {
  const { locale, t } = useI18n();
  const location = useLocation();
  const navigate = searchRoute.useNavigate();
  const search = searchRoute.useSearch();
  const currentPage = search.page ?? 1;
  const ordering = search.ordering ?? '-date';
  const safety = search.nsfw === false ? 'safe' : 'all';
  const shouldUseSubjectSearch = usesSubjectDatabaseSearch(search);
  const subjectQueryParams = useMemo(() => buildSubjectSearchQuery(search, pageSize), [search]);
  const subjectsQuery = useQuery({
    ...subjectQueries.list(subjectQueryParams),
    enabled: shouldUseSubjectSearch,
  });
  const calendarQuery = useQuery({ ...subjectQueries.calendar(), enabled: !shouldUseSubjectSearch });
  const calendarItems = useMemo(
    () =>
      sortCalendarItems(
        filterCalendarItems(flattenCalendarGroups(calendarQuery.data), {
          ordering,
          safety,
          subjectType: search.subject_type ?? '',
        }),
        ordering,
      ),
    [calendarQuery.data, ordering, safety, search.subject_type],
  );
  const resultCount = shouldUseSubjectSearch ? subjectsQuery.data?.count : calendarItems.length;
  const hasResolvedResults = shouldUseSubjectSearch
    ? subjectsQuery.data !== undefined
    : calendarQuery.data !== undefined;
  const totalPages = Math.max(1, Math.ceil((resultCount ?? 0) / pageSize));
  const visibleCalendarItems = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return calendarItems.slice(start, start + pageSize);
  }, [calendarItems, currentPage]);
  const isFetching = shouldUseSubjectSearch ? subjectsQuery.isFetching : calendarQuery.isFetching;
  const isLoading = shouldUseSubjectSearch ? subjectsQuery.isLoading : calendarQuery.isLoading;
  const isError = shouldUseSubjectSearch ? subjectsQuery.isError : calendarQuery.isError;
  const isEmpty = shouldUseSubjectSearch ? (subjectsQuery.data?.results.length ?? 0) === 0 : calendarItems.length === 0;
  const resultsStatus: ResultsStatus =
    !hasResolvedResults && isLoading
      ? 'loading'
      : !hasResolvedResults && isError
        ? 'error'
        : isEmpty
          ? 'empty'
          : 'ready';
  const subjectLinkState = useMemo(() => routeBackState(location, t('nav.search')), [location, t]);

  useEffect(() => {
    if (hasResolvedResults && currentPage > totalPages) {
      void navigate({ replace: true, search: (current) => ({ ...current, page: totalPages }) });
    }
  }, [currentPage, hasResolvedResults, navigate, totalPages]);

  function updateSearchParam(key: keyof SearchPageSearch, value: string) {
    void navigate({
      search: (current) => ({
        ...current,
        ...validateSearchPageSearch({
          ...current,
          [key]: value || undefined,
          page: key === 'page' ? value : undefined,
        }),
      }),
    });
  }

  return (
    <Page title={t('search.title')} eyebrow={t('nav.groupDiscover')} seo={false}>
      <Seo
        title={t('search.title')}
        description="Search anime and galgame entries by title, year, season, platform, episode count, content type, and source ID."
        path={routes.search}
      />
      <div className="grid gap-5 pb-8">
        <SearchFilters search={search} onChange={updateSearchParam} />

        <ResultsMeta
          count={hasResolvedResults ? resultCount : undefined}
          label={t('common.subjects')}
          pending={isFetching && !isLoading}
          pendingLabel={t('search.loading')}
        />

        <ResultsState
          emptyDescription={t('search.emptyBody')}
          emptyTitle={t('search.emptyTitle')}
          errorDescription={t('search.errorBody')}
          errorTitle={t('search.errorTitle')}
          loadingTitle={t('search.loading')}
          status={resultsStatus}
        >
          <>
            <SearchResultsGrid
              calendarItems={visibleCalendarItems}
              locale={locale}
              state={subjectLinkState}
              subjects={subjectsQuery.data?.results ?? []}
              useDatabaseResults={shouldUseSubjectSearch}
            />

            <Pagination
              currentPage={currentPage}
              totalPages={totalPages}
              onPageChange={(page) => {
                updateSearchParam('page', String(Math.min(Math.max(page, 1), totalPages)));
              }}
            />
          </>
        </ResultsState>
      </div>
    </Page>
  );
}
