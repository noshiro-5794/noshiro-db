import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Search, X } from 'lucide-react';
import { useAuth } from '@/features/auth/use-auth';
import { useI18n } from '@/features/i18n/use-i18n';
import { calendarImageOf, filterCalendarItems, flattenCalendarGroups, sortCalendarItems } from '@/features/search/calendar-search';
import {
  orderingOptions,
  episodeRangeOptions,
  platformOptions,
  safetyOptions,
  seasonOptions,
  subjectTypeOptions,
  type EpisodeRangeFilter,
  type PlatformFilter,
  type SeasonFilter,
  type SubjectTypeFilter,
} from '@/features/search/search-options';
import type { SubjectOrdering } from '@/features/subjects/api';
import { subjectQueries } from '@/features/subjects/subject-queries';
import type { CalendarSubjectItem, SubjectSummary } from '@/lib/api/types';
import { routes } from '@/routes/paths';
import { EmptyState, ErrorState } from '@/shared/ui/FeedbackState';
import { FilterCombobox } from '@/shared/ui/FilterCombobox';
import { FilterMenu } from '@/shared/ui/FilterMenu';
import { Button } from '@/shared/ui/Button';
import { Input } from '@/shared/ui/Input';
import type { RouteBackState } from '@/shared/navigation/route-state';
import { routeBackState } from '@/shared/navigation/route-state';
import { Seo } from '@/shared/seo/Seo';
import { Page } from '@/shared/ui/Page';
import { Pagination } from '@/shared/ui/Pagination';

const coverPlaceholder = '/assets/placeholders/subject-cover.png';
const pageSize = 30;

type SearchPosterProps = {
  badge?: string;
  poster: string;
  subtitle?: string;
  state?: RouteBackState;
  title: string;
  to: string;
};

type SearchFilterKey = 'type' | 'sourceId' | 'year' | 'season' | 'sort' | 'platform' | 'episodes' | 'safety';

function calendarTitleOf(item: CalendarSubjectItem, fallback: string) {
  return item.display_title || item.title || item.title_cn || fallback;
}

function subjectTitleOf(subject: SubjectSummary, fallback: string) {
  return subject.display_title || subject.title || subject.title_cn || fallback;
}

function subjectPosterOf(subject: SubjectSummary) {
  return subject.images?.poster || subject.images?.thumbnail || subject.image_thumbnail || subject.image || coverPlaceholder;
}

function SearchPoster({ badge, poster, state, subtitle, title, to }: SearchPosterProps) {
  return (
    <Link className="group grid min-w-0 gap-2" state={state} to={to}>
      <div className="relative aspect-[2/3] overflow-hidden rounded-xl bg-neutral-100 shadow-sm ring-1 ring-neutral-200 transition group-hover:-translate-y-1 group-hover:shadow-lg group-hover:ring-[var(--color-accent-border)] dark:bg-neutral-900 dark:ring-neutral-800">
        <img
          className="h-full w-full object-cover transition duration-300 group-hover:scale-[1.035]"
          src={poster}
          alt={title}
          loading="lazy"
        />
        {badge ? (
          <div className="absolute left-2 top-2 rounded-full bg-black/55 px-2 py-1 text-[11px] font-semibold text-white backdrop-blur">
            {badge}
          </div>
        ) : null}
      </div>
      <span className="min-w-0">
        <span className="line-clamp-2 text-sm font-semibold leading-5 text-neutral-950 dark:text-white">{title}</span>
        <span className="mt-1 line-clamp-1 text-xs text-neutral-500 dark:text-neutral-400">
          {subtitle}
        </span>
      </span>
    </Link>
  );
}

function getEpisodeRangeParams(range: EpisodeRangeFilter) {
  if (range === 'short') {
    return { min: 1, max: 12 };
  }
  if (range === 'standard') {
    return { min: 13, max: 24 };
  }
  if (range === 'long') {
    return { min: 25, max: undefined };
  }
  return { min: undefined, max: undefined };
}

export function SearchPage() {
  const { locale, t } = useI18n();
  const { role } = useAuth();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const keyword = searchParams.get('keyword') ?? '';
  const subjectType = (searchParams.get('subject_type') ?? '') as SubjectTypeFilter;
  const sourceId = searchParams.get('source_id') ?? '';
  const ordering = (searchParams.get('ordering') ?? '-date') as SubjectOrdering;
  const safety = searchParams.get('nsfw') === 'false' ? 'safe' : 'all';
  const year = searchParams.get('year') ?? '';
  const season = (searchParams.get('season') ?? '') as SeasonFilter;
  const platform = (searchParams.get('platform') ?? '') as PlatformFilter;
  const episodeRange = (searchParams.get('episodes') ?? '') as EpisodeRangeFilter;
  const currentPage = Math.max(1, Number(searchParams.get('page') ?? '1') || 1);
  const [draftKeyword, setDraftKeyword] = useState(keyword);
  const hasDatabaseOnlyFilters = Boolean(sourceId || year || season || platform || episodeRange);
  const shouldUseSubjectSearch = Boolean(keyword.trim()) || hasDatabaseOnlyFilters;
  const [activeFilters, setActiveFilters] = useState<SearchFilterKey[]>(() => {
    const initialFilters: SearchFilterKey[] = ['type', 'year', 'season', 'sort'];
    if (sourceId) initialFilters.splice(1, 0, 'sourceId');
    if (platform) initialFilters.push('platform');
    if (episodeRange) initialFilters.push('episodes');
    if (searchParams.has('nsfw')) initialFilters.push('safety');
    return initialFilters;
  });
  const episodeRangeParams = getEpisodeRangeParams(episodeRange);

  const subjectQueryParams = useMemo(
    () => ({
      keyword: keyword || undefined,
      source_id: sourceId || undefined,
      subject_type: subjectType || undefined,
      ordering,
      nsfw: safety === 'safe' ? false : undefined,
      year: year ? Number(year) : undefined,
      season: season || undefined,
      platform: platform || undefined,
      episodes_min: episodeRangeParams.min,
      episodes_max: episodeRangeParams.max,
      page: currentPage,
      page_size: pageSize,
    }),
    [currentPage, episodeRangeParams.max, episodeRangeParams.min, keyword, ordering, platform, safety, season, sourceId, subjectType, year],
  );

  const subjectsQuery = useQuery({
    ...subjectQueries.list(subjectQueryParams),
    enabled: shouldUseSubjectSearch,
  });
  const calendarQuery = useQuery(subjectQueries.calendar());

  const calendarItems = useMemo(() => {
    const items = flattenCalendarGroups(calendarQuery.data);
    return sortCalendarItems(
      filterCalendarItems(items, {
        ordering,
        safety,
        subjectType,
      }),
      ordering,
    );
  }, [calendarQuery.data, ordering, safety, subjectType]);

  const resultCount = shouldUseSubjectSearch ? subjectsQuery.data?.count : calendarItems.length;
  const hasResolvedResults = shouldUseSubjectSearch ? subjectsQuery.data !== undefined : calendarQuery.data !== undefined;
  const totalPages = Math.max(1, Math.ceil((resultCount ?? 0) / pageSize));
  const visibleCalendarItems = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return calendarItems.slice(start, start + pageSize);
  }, [calendarItems, currentPage]);
  const isFetching = shouldUseSubjectSearch ? subjectsQuery.isFetching : calendarQuery.isFetching;
  const isError = shouldUseSubjectSearch ? subjectsQuery.isError : calendarQuery.isError;
  const isEmpty = shouldUseSubjectSearch ? (subjectsQuery.data?.results.length ?? 0) === 0 : calendarItems.length === 0;

  useEffect(() => {
    setDraftKeyword(keyword);
  }, [keyword]);

  useEffect(() => {
    if (hasResolvedResults && currentPage > totalPages) {
      setSearchParams((currentParams) => {
        const nextParams = new URLSearchParams(currentParams);
        nextParams.set('page', String(totalPages));
        return nextParams;
      });
    }
  }, [currentPage, hasResolvedResults, setSearchParams, totalPages]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    updateSearchParam('keyword', draftKeyword.trim());
  }

  function handleKeywordChange(nextKeyword: string) {
    setDraftKeyword(nextKeyword);
    if (!nextKeyword.trim()) {
      updateSearchParam('keyword', '');
    }
  }

  function updateSearchParam(key: string, value: string) {
    setSearchParams((currentParams) => {
      const nextParams = new URLSearchParams(currentParams);

      if (value) {
        nextParams.set(key, value);
      } else {
        nextParams.delete(key);
      }

      if (key !== 'page') {
        nextParams.delete('page');
      }

      return nextParams;
    });
  }

  function goToPage(nextPage: number) {
    updateSearchParam('page', String(Math.min(Math.max(nextPage, 1), totalPages)));
  }

  function addFilter(filter: SearchFilterKey | '') {
    if (!filter || activeFilters.includes(filter)) {
      return;
    }
    setActiveFilters((currentFilters) => [...currentFilters, filter]);
  }

  function removeFilter(filter: SearchFilterKey) {
    setActiveFilters((currentFilters) => currentFilters.filter((item) => item !== filter));
    if (filter === 'type') {
      updateSearchParam('subject_type', '');
    }
    if (filter === 'sourceId') {
      updateSearchParam('source_id', '');
    }
    if (filter === 'year') {
      updateSearchParam('year', '');
    }
    if (filter === 'season') {
      updateSearchParam('season', '');
    }
    if (filter === 'sort') {
      updateSearchParam('ordering', '');
    }
    if (filter === 'platform') {
      updateSearchParam('platform', '');
    }
    if (filter === 'episodes') {
      updateSearchParam('episodes', '');
    }
    if (filter === 'safety') {
      updateSearchParam('nsfw', '');
    }
  }

  const filterLabels: Record<SearchFilterKey, string> = {
    type: t('search.type'),
    sourceId: t('search.sourceId'),
    year: t('search.year'),
    season: t('search.season'),
    sort: t('search.sort'),
    platform: t('search.platform'),
    episodes: t('search.episodes'),
    safety: t('search.safety'),
  };
  const allFilters: SearchFilterKey[] = ['type', 'sourceId', 'year', 'season', 'sort', 'platform', 'episodes', 'safety'];
  const availableFilters = allFilters.filter(
    (filter) => !activeFilters.includes(filter),
  );
  const subjectLinkState = useMemo(() => routeBackState(location, t('nav.search')), [location, t]);
  const yearOptions = useMemo(() => {
    const currentYear = new Date().getFullYear();
    return [
      { label: t('search.all'), value: '' },
      ...Array.from({ length: currentYear - 1999 }, (_, index) => {
        const optionYear = String(currentYear - index);
        return { label: optionYear, value: optionYear };
      }),
    ];
  }, [t]);

  return (
    <Page
      title={t('search.title')}
      eyebrow={t('nav.groupDiscover')}
      hideHeader={role === 'guest'}
    >
      <Seo
        title={t('search.title')}
        description="Search anime and galgame entries by title, year, season, platform, episode count, content type, and source ID."
        path={routes.search}
      />
      <div className="grid gap-6 pb-8">
        <form
          className={`content-toolbar ${role === 'guest' ? 'is-public' : ''}`}
          onSubmit={handleSubmit}
        >
            <div className="content-toolbar-grid is-search">
              <label className="content-toolbar-search">
                <span className="sr-only">{t('search.keyword')}</span>
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-neutral-400" />
                <Input
                  className="pl-9"
                  value={draftKeyword}
                  placeholder={t('public.searchPlaceholder')}
                  onChange={(event) => handleKeywordChange(event.target.value)}
                />
              </label>
              <Button type="submit" variant="secondary">
                {t('search.title')}
              </Button>
            </div>

            <div className="content-toolbar-filter-row">
              {activeFilters.map((filter) => (
                <div className="content-toolbar-filter-item" key={filter}>
                  {filter === 'type' ? (
                    <FilterMenu
                      label={filterLabels.type}
                      options={subjectTypeOptions.map((option) => ({ label: t(option.labelKey), value: option.value }))}
                      value={subjectType}
                      onChange={(value) => updateSearchParam('subject_type', value)}
                    />
                  ) : null}
                  {filter === 'sourceId' ? (
                    <label className="flex h-10 min-w-0 items-center gap-1.5 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-3 text-sm font-semibold text-[var(--color-text)] shadow-sm transition focus-within:ring-4 focus-within:ring-[var(--color-focus-ring)] hover:border-[var(--color-accent-border)] hover:bg-[var(--color-surface-muted)]">
                      <span className="shrink-0 text-neutral-400 dark:text-neutral-500">{filterLabels.sourceId}</span>
                      <Input
                        className="h-auto min-w-0 flex-1 rounded-none bg-transparent p-0 text-sm font-semibold shadow-none ring-0 placeholder:text-neutral-400 focus:ring-0"
                        inputMode="numeric"
                        pattern="[0-9]*"
                        placeholder={t('search.sourceIdPlaceholder')}
                        value={sourceId}
                        onChange={(event) => updateSearchParam('source_id', event.target.value.replace(/\D/gu, ''))}
                      />
                    </label>
                  ) : null}
                  {filter === 'year' ? (
                    <FilterCombobox
                      allowCustomValue={(value) => /^\d{4}$/u.test(value) && Number(value) >= 1900 && Number(value) <= 2100}
                      label={filterLabels.year}
                      options={yearOptions}
                      placeholder={t('search.year')}
                      value={year}
                      onChange={(value) => updateSearchParam('year', value)}
                    />
                  ) : null}
                  {filter === 'season' ? (
                    <FilterMenu
                      label={filterLabels.season}
                      options={seasonOptions.map((option) => ({ label: t(option.labelKey), value: option.value }))}
                      value={season}
                      onChange={(value) => updateSearchParam('season', value)}
                    />
                  ) : null}
                  {filter === 'sort' ? (
                    <FilterMenu
                      label={filterLabels.sort}
                      options={orderingOptions.map((option) => ({ label: t(option.labelKey), value: option.value }))}
                      value={ordering}
                      onChange={(value) => updateSearchParam('ordering', value === '-date' ? '' : value)}
                    />
                  ) : null}
                  {filter === 'platform' ? (
                    <FilterMenu
                      label={filterLabels.platform}
                      options={platformOptions.map((option) => ({
                        label: option.value ? option.label : t('search.all'),
                        value: option.value,
                      }))}
                      value={platform}
                      onChange={(value) => updateSearchParam('platform', value)}
                    />
                  ) : null}
                  {filter === 'episodes' ? (
                    <FilterMenu
                      label={filterLabels.episodes}
                      options={episodeRangeOptions.map((option) => ({ label: t(option.labelKey), value: option.value }))}
                      value={episodeRange}
                      onChange={(value) => updateSearchParam('episodes', value)}
                    />
                  ) : null}
                  {filter === 'safety' ? (
                    <FilterMenu
                      label={filterLabels.safety}
                      options={safetyOptions.map((option) => ({ label: t(option.labelKey), value: option.value }))}
                      value={safety}
                      onChange={(value) => updateSearchParam('nsfw', value === 'safe' ? 'false' : '')}
                    />
                  ) : null}
                  <Button
                    className="self-end text-neutral-400 hover:text-neutral-950 dark:hover:text-white"
                    size="icon"
                    type="button"
                    variant="secondary"
                    aria-label={`Remove ${filterLabels[filter]}`}
                    onClick={() => removeFilter(filter)}
                  >
                    <X className="size-4" />
                  </Button>
                </div>
              ))}

              {availableFilters.length > 0 ? (
                <div className="min-w-44">
                  <FilterMenu
                    label={t('search.addFilter')}
                    options={[
                      { label: t('search.addFilter'), value: '' },
                      ...availableFilters.map((filter) => ({ label: filterLabels[filter], value: filter })),
                    ]}
                    value=""
                    onChange={addFilter}
                  />
                </div>
              ) : null}
            </div>
          </form>

          <div className="flex justify-end gap-3 text-sm text-neutral-500 dark:text-neutral-400">
            {isFetching ? <span>{t('search.loading')}</span> : null}
          </div>

        {isError ? <ErrorState title={t('search.errorTitle')} description={t('search.errorBody')} /> : null}

        {!isError && !isFetching && isEmpty ? (
          <EmptyState title={t('search.emptyTitle')} description={t('search.emptyBody')} />
        ) : null}

        <div className="grid grid-cols-2 gap-x-4 gap-y-7 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
          {shouldUseSubjectSearch
            ? (subjectsQuery.data?.results ?? []).map((subject) => (
                <SearchPoster
                  key={subject.id}
                  poster={subjectPosterOf(subject)}
                  state={subjectLinkState}
                  subtitle={subject.display_subtitle || subject.subject_type}
                  title={subjectTitleOf(subject, t('common.untitledSubject'))}
                  to={routes.subject(subject.id)}
                />
              ))
            : visibleCalendarItems.map((item) => (
                <SearchPoster
                  badge={new Intl.NumberFormat(locale, { notation: item.doing >= 10000 ? 'compact' : 'standard' }).format(item.doing)}
                  key={item.subject_id}
                  poster={calendarImageOf(item) || coverPlaceholder}
                  state={subjectLinkState}
                  subtitle={item.display_subtitle || item.subject_type}
                  title={calendarTitleOf(item, t('common.untitledSubject'))}
                  to={routes.subject(item.subject_id)}
                />
              ))}
        </div>

        <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={goToPage} />
      </div>
    </Page>
  );
}
