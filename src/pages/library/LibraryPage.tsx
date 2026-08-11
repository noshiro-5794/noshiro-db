import { type SyntheticEvent, useEffect, useMemo, useState } from 'react';
import { getRouteApi, useLocation } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { SlidersHorizontal } from 'lucide-react';
import { libraryQueries, UserSubjectListItem } from '@/entities/library';
import { TagManagerPanel } from '@/features/tag-manager';
import { useI18n } from '@/shared/i18n';
import type { PrimarySubjectType, UserSubjectStatus } from '@/shared/api';
import { validateLibrarySearch, type LibrarySearch } from '@/shared/routing/route-search';
import { routeBackState } from '@/shared/routing/route-state';
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
import { FilterMenu } from '@/shared/ui/FilterMenu';
import { FilterPanel, FilterPanelChoice, FilterPanelHeader } from '@/shared/ui/FilterPanel';
import { Page } from '@/shared/ui/Page';
import { Pagination } from '@/shared/ui/Pagination';
import { ToggleGroup } from '@/shared/ui/Toggle';

const pageSize = 12;
const libraryRoute = getRouteApi('/library');
type LibraryOrdering = NonNullable<LibrarySearch['ordering']>;

export function LibraryPage() {
  const { t } = useI18n();
  const location = useLocation();
  const navigate = libraryRoute.useNavigate();
  const search = libraryRoute.useSearch();
  const keyword = search.keyword ?? '';
  const status = search.status ?? '';
  const subjectType = search.subject_type ?? '';
  const tagId = search.tag_id ?? null;
  const ordering = search.ordering ?? '-updated_at';
  const currentPage = search.page ?? 1;
  const [draftKeyword, setDraftKeyword] = useState(keyword);
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
  const orderingOptions: Array<{ label: string; value: LibraryOrdering }> = [
    { label: t('library.sortRecentlyUpdated'), value: '-updated_at' },
    { label: t('library.sortRecentlyAdded'), value: '-created_at' },
    { label: t('library.sortRatingHigh'), value: '-rating' },
    { label: t('library.sortRatingLow'), value: 'rating' },
    { label: t('library.sortSimpleRatingHigh'), value: '-simple_rating' },
    { label: t('library.sortRecentlyFinished'), value: '-watch_end_date' },
    { label: t('library.sortStartedRecently'), value: '-watch_start_date' },
  ];

  const query = useMemo(
    () => ({
      ...(keyword ? { keyword } : {}),
      ...(status ? { status } : {}),
      ...(subjectType ? { subject_type: subjectType } : {}),
      ...(tagId === null ? {} : { tag_id: tagId }),
      ordering,
      page: currentPage,
      page_size: pageSize,
    }),
    [currentPage, keyword, ordering, status, subjectType, tagId],
  );
  const libraryQuery = useQuery(libraryQueries.userSubjects(query));
  const tagsQuery = useQuery(libraryQueries.tags());
  const totalCount = libraryQuery.data?.count ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const libraryItems = libraryQuery.data?.results ?? [];
  const resultsStatus: ResultsStatus =
    libraryQuery.data === undefined && libraryQuery.isLoading
      ? 'loading'
      : libraryQuery.data === undefined && libraryQuery.isError
        ? 'error'
        : libraryItems.length === 0
          ? 'empty'
          : 'ready';
  const selectedTag = (tagsQuery.data?.results ?? []).find((tag) => tag.id === tagId);
  const subjectLinkState = useMemo(() => routeBackState(location, t('nav.library')), [location, t]);

  useEffect(() => {
    setDraftKeyword(keyword);
  }, [keyword]);

  useEffect(() => {
    if (libraryQuery.data && currentPage > totalPages) {
      void navigate({ replace: true, search: (current) => ({ ...current, page: totalPages }) });
    }
  }, [currentPage, libraryQuery.data, navigate, totalPages]);

  function updateSearchParam(key: keyof LibrarySearch, value: string) {
    void navigate({
      search: (current) => ({
        ...current,
        ...validateLibrarySearch({ ...current, [key]: value || undefined, page: key === 'page' ? value : undefined }),
      }),
    });
  }

  function handleSubmit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    updateSearchParam('keyword', draftKeyword.trim());
  }

  function resetFilters() {
    void navigate({ search: {} });
  }

  function statusLabel(statusValue: string) {
    return statusOptions.find((option) => option.value === statusValue)?.label ?? statusValue.replaceAll('_', ' ');
  }

  function goToPage(page: number) {
    updateSearchParam('page', String(Math.min(Math.max(page, 1), totalPages)));
  }

  return (
    <Page title={t('library.title')} eyebrow={t('nav.groupLibrary')}>
      <div className="grid gap-4 lg:grid-cols-[220px_minmax(0,1fr)] lg:gap-x-6">
        <div className="grid content-start gap-4 lg:col-start-2 lg:row-start-1">
          <DataToolbar onSubmit={handleSubmit}>
            <DataToolbarRow className="xl:grid-cols-[minmax(0,1fr)_150px_190px_auto]">
              <DataToolbarPrimary>
                <SearchField
                  aria-label={t('library.searchPlaceholder')}
                  maxLength={200}
                  value={draftKeyword}
                  placeholder={t('library.searchPlaceholder')}
                  onChange={(event) => {
                    setDraftKeyword(event.target.value);
                  }}
                />
              </DataToolbarPrimary>
              <FilterMenu
                label={t('search.type')}
                options={typeOptions}
                size="lg"
                value={subjectType}
                onChange={(value) => {
                  updateSearchParam('subject_type', value);
                }}
              />
              <FilterMenu
                label={t('common.sort')}
                options={orderingOptions}
                size="lg"
                value={ordering}
                onChange={(value) => {
                  updateSearchParam('ordering', value);
                }}
              />
              <Button size="lg" type="submit" variant="secondary">
                {t('common.search')}
              </Button>
            </DataToolbarRow>
          </DataToolbar>

          <ResultsMeta
            actions={
              status || subjectType || tagId !== null || keyword || ordering !== '-updated_at' ? (
                <Button
                  className="h-7 px-2 font-semibold text-[var(--ui-accent-text)]"
                  size="sm"
                  type="button"
                  variant="ghost"
                  onClick={resetFilters}
                >
                  {t('common.reset')}
                </Button>
              ) : null
            }
            count={libraryQuery.data?.count}
            label={t('common.subjects')}
            pending={libraryQuery.isFetching && !libraryQuery.isLoading}
            pendingLabel={t('common.loading')}
          >
            {status ? <Badge variant="secondary">{statusLabel(status)}</Badge> : null}
            {subjectType ? <Badge variant="secondary">{subjectType}</Badge> : null}
            {selectedTag ? <Badge variant="secondary">{selectedTag.name}</Badge> : null}
            {keyword ? <Badge variant="secondary">{keyword}</Badge> : null}
          </ResultsMeta>
        </div>

        <aside className="grid content-start gap-4 lg:col-start-1 lg:row-span-2 lg:row-start-1">
          <FilterPanel>
            <FilterPanelHeader>
              <SlidersHorizontal className="size-4 text-[var(--ui-text-subtle)]" />
              <h2>{t('library.status')}</h2>
            </FilterPanelHeader>
            <ToggleGroup
              aria-label={t('library.status')}
              className="grid gap-1 border-0 bg-transparent p-0"
              orientation="vertical"
              value={[status || 'all']}
              onValueChange={(values) => {
                const nextStatus = values[0];
                if (nextStatus) updateSearchParam('status', nextStatus === 'all' ? '' : nextStatus);
              }}
            >
              {statusOptions.map((option) => (
                <FilterPanelChoice key={option.value || 'all'} value={option.value || 'all'}>
                  <span>{option.label}</span>
                </FilterPanelChoice>
              ))}
            </ToggleGroup>
          </FilterPanel>

          <TagManagerPanel
            isError={tagsQuery.isError}
            isLoading={tagsQuery.isLoading}
            selectedTagId={tagId}
            tags={tagsQuery.data?.results ?? []}
            onSelectTag={(nextTagId) => {
              updateSearchParam('tag_id', nextTagId === null ? '' : String(nextTagId));
            }}
          />
        </aside>

        <div className="grid content-start gap-4 lg:col-start-2 lg:row-start-2">
          <ResultsState
            emptyDescription={t('library.emptyBody')}
            emptyTitle={t('library.emptyTitle')}
            errorDescription={t('search.errorBody')}
            errorTitle={t('library.errorTitle')}
            loadingTitle={t('library.loading')}
            status={resultsStatus}
          >
            <>
              <ListSurface>
                {libraryItems.map((item) => (
                  <UserSubjectListItem detailLinkState={subjectLinkState} item={item} key={item.id} showWatchDates />
                ))}
              </ListSurface>
              <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={goToPage} />
            </>
          </ResultsState>
        </div>
      </div>
    </Page>
  );
}
