import { useEffect, useMemo } from 'react';
import { getRouteApi, useLocation } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { subjectQueries } from '@/entities/subject';
import { buildSubjectSearchQuery, SearchFilters, SearchResultsGrid } from '@/features/search';
import { useI18n } from '@/shared/i18n';
import { routes } from '@/shared/routing/paths';
import { validateSearchPageSearch, type SearchPageSearch } from '@/shared/routing/route-search';
import { routeBackState } from '@/shared/routing/route-state';
import { Seo } from '@/shared/seo/Seo';
import { ResultsMeta, ResultsState, type ResultsStatus } from '@/shared/ui/DataView';
import { Page } from '@/shared/ui/Page';
import { PageHeading } from '@/shared/ui/PageHeading';
import { Pagination } from '@/shared/ui/Pagination';

const pageSize = 30;
const searchRoute = getRouteApi('/search');

export function SearchPage() {
  const { t } = useI18n();
  const location = useLocation();
  const navigate = searchRoute.useNavigate();
  const search = searchRoute.useSearch();
  const currentPage = search.page ?? 1;
  const subjectQueryParams = useMemo(() => buildSubjectSearchQuery(search, pageSize), [search]);
  // The catalogue is the source for this page. It used to browse the season
  // calendar until a keyword was typed, which made a 79k catalogue look like a
  // 198-item list with seven pages.
  const subjectsQuery = useQuery(subjectQueries.list(subjectQueryParams));
  const resultCount = subjectsQuery.data?.count;
  const hasResolvedResults = subjectsQuery.data !== undefined;
  const totalPages = Math.max(1, Math.ceil((resultCount ?? 0) / pageSize));
  const { isError, isFetching, isLoading } = subjectsQuery;
  const isEmpty = (subjectsQuery.data?.results.length ?? 0) === 0;
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
    <Page hideHeader title={t('search.title')} seo={false}>
      <Seo
        title={t('nav.catalog')}
        description="Search anime and galgame entries by title, year, season, platform, episode count, content type, and source ID."
        path={routes.search}
      />
      <div className="grid gap-5 pb-8">
        <PageHeading description={t('search.pageBody')} eyebrow={t('nav.groupDiscover')} title={t('nav.catalog')} />
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
            <SearchResultsGrid state={subjectLinkState} subjects={subjectsQuery.data?.results ?? []} />

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
