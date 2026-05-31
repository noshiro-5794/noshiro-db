import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { X } from 'lucide-react';
import { useI18n } from '@/features/i18n/use-i18n';
import { filterCalendarItems, flattenCalendarGroups, sortCalendarItems } from '@/features/search/calendar-search';
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

const coverPlaceholder = '/assets/placeholders/subject-cover.png';
const pageSize = 30;

type SearchPosterProps = {
  badge?: string;
  poster: string;
  subtitle?: string;
  title: string;
  to: string;
};

type SearchFilterKey = 'type' | 'year' | 'season' | 'sort' | 'platform' | 'episodes' | 'safety';
type PaginationItem = number | 'ellipsis';

function calendarTitleOf(item: CalendarSubjectItem) {
  return item.display_title || item.title || item.title_cn || 'Untitled';
}

function subjectTitleOf(subject: SubjectSummary) {
  return subject.display_title || subject.title || subject.title_cn || 'Untitled';
}

function subjectPosterOf(subject: SubjectSummary) {
  return subject.images?.poster || subject.images?.thumbnail || subject.image_thumbnail || subject.image || coverPlaceholder;
}

function SearchPoster({ badge, poster, subtitle, title, to }: SearchPosterProps) {
  return (
    <Link className="group grid min-w-0 gap-2" to={to}>
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

function buildPaginationItems(currentPage: number, totalPages: number): PaginationItem[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  const pages = new Set([1, totalPages, currentPage, currentPage - 1, currentPage + 1]);

  if (currentPage <= 4) {
    [2, 3, 4, 5].forEach((page) => pages.add(page));
  }

  if (currentPage >= totalPages - 3) {
    [totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1].forEach((page) => pages.add(page));
  }

  const sortedPages = [...pages]
    .filter((page) => page >= 1 && page <= totalPages)
    .sort((a, b) => a - b);

  return sortedPages.flatMap((page, index) => {
    const previousPage = sortedPages[index - 1];
    if (!previousPage) {
      return [page];
    }
    if (page - previousPage === 2) {
      return [previousPage + 1, page];
    }
    if (page - previousPage > 2) {
      return ['ellipsis' as const, page];
    }
    return [page];
  });
}

export function SearchPage() {
  const { locale, t } = useI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const keyword = searchParams.get('keyword') ?? '';
  const subjectType = (searchParams.get('subject_type') ?? '') as SubjectTypeFilter;
  const ordering = (searchParams.get('ordering') ?? '-date') as SubjectOrdering;
  const safety = searchParams.get('nsfw') === 'false' ? 'safe' : 'all';
  const year = searchParams.get('year') ?? '';
  const season = (searchParams.get('season') ?? '') as SeasonFilter;
  const platform = (searchParams.get('platform') ?? '') as PlatformFilter;
  const episodeRange = (searchParams.get('episodes') ?? '') as EpisodeRangeFilter;
  const currentPage = Math.max(1, Number(searchParams.get('page') ?? '1') || 1);
  const [draftKeyword, setDraftKeyword] = useState(keyword);
  const [jumpPage, setJumpPage] = useState('');
  const hasDatabaseOnlyFilters = Boolean(year || season || platform || episodeRange);
  const shouldUseSubjectSearch = Boolean(keyword.trim()) || hasDatabaseOnlyFilters;
  const [activeFilters, setActiveFilters] = useState<SearchFilterKey[]>(() => {
    const initialFilters: SearchFilterKey[] = ['type', 'year', 'season', 'sort'];
    if (platform) initialFilters.push('platform');
    if (episodeRange) initialFilters.push('episodes');
    if (searchParams.has('nsfw')) initialFilters.push('safety');
    return initialFilters;
  });
  const episodeRangeParams = getEpisodeRangeParams(episodeRange);

  const subjectQueryParams = useMemo(
    () => ({
      keyword: keyword || undefined,
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
    [currentPage, episodeRangeParams.max, episodeRangeParams.min, keyword, ordering, platform, safety, season, subjectType, year],
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
  const totalPages = Math.max(1, Math.ceil((resultCount ?? 0) / pageSize));
  const paginationItems = useMemo(() => buildPaginationItems(currentPage, totalPages), [currentPage, totalPages]);
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
    if (currentPage > totalPages) {
      setSearchParams((currentParams) => {
        const nextParams = new URLSearchParams(currentParams);
        nextParams.set('page', String(totalPages));
        return nextParams;
      });
    }
  }, [currentPage, setSearchParams, totalPages]);

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

  function handleJumpSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextPage = Number(jumpPage);
    if (Number.isFinite(nextPage)) {
      goToPage(nextPage);
      setJumpPage('');
    }
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
    year: t('search.year'),
    season: t('search.season'),
    sort: t('search.sort'),
    platform: t('search.platform'),
    episodes: t('search.episodes'),
    safety: t('search.safety'),
  };
  const availableFilters = (['type', 'year', 'season', 'sort', 'platform', 'episodes', 'safety'] as const).filter(
    (filter) => !activeFilters.includes(filter),
  );
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
    <div className="bg-neutral-50 pb-14 dark:bg-neutral-950">
      <section className="border-b border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-950">
        <div className="mx-auto grid max-w-6xl gap-5 px-5 py-8">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-normal text-[var(--color-accent-strong)]">
              {shouldUseSubjectSearch ? t('search.results') : t('search.catalog')}
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-neutral-950 dark:text-white sm:text-4xl">
              {t('search.title')}
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-500 dark:text-neutral-400">
              {t('public.searchBody')}
            </p>
          </div>

          <form
            className="grid gap-3 rounded-2xl bg-neutral-100 p-3 dark:bg-neutral-900/80"
            onSubmit={handleSubmit}
          >
            <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto]">
              <label className="grid gap-1.5">
                <span className="sr-only">{t('search.keyword')}</span>
                <Input
                  value={draftKeyword}
                  placeholder={t('public.searchPlaceholder')}
                  onChange={(event) => handleKeywordChange(event.target.value)}
                />
              </label>
              <Button className="self-end" size="lg" type="submit">
                {t('search.title')}
              </Button>
            </div>

            <div className="flex flex-wrap gap-2">
              {activeFilters.map((filter) => (
                <div className="grid min-w-44 grid-cols-[minmax(0,1fr)_40px] gap-1" key={filter}>
                  {filter === 'type' ? (
                    <FilterMenu
                      label={filterLabels.type}
                      options={subjectTypeOptions.map((option) => ({ label: t(option.labelKey), value: option.value }))}
                      value={subjectType}
                      onChange={(value) => updateSearchParam('subject_type', value)}
                    />
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

          <div className="flex justify-between gap-3 text-sm text-neutral-500 dark:text-neutral-400">
            <span>{typeof resultCount === 'number' ? `${resultCount} ${t('search.results')}` : t('search.ready')}</span>
            {isFetching ? <span>{t('search.loading')}</span> : null}
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-6 px-5 py-8">
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
                  subtitle={subject.display_subtitle || subject.subject_type}
                  title={subjectTitleOf(subject)}
                  to={routes.subject(subject.id)}
                />
              ))
            : visibleCalendarItems.map((item) => (
                <SearchPoster
                  badge={new Intl.NumberFormat(locale, { notation: item.doing >= 10000 ? 'compact' : 'standard' }).format(item.doing)}
                  key={item.subject_id}
                  poster={item.image_thumbnail || coverPlaceholder}
                  subtitle={item.display_subtitle || item.subject_type}
                  title={calendarTitleOf(item)}
                  to={routes.subject(item.subject_id)}
                />
              ))}
        </div>

        {totalPages > 1 ? (
          <div className="flex flex-col gap-4 border-t border-neutral-200 pt-5 text-sm text-neutral-500 dark:border-neutral-800 dark:text-neutral-400 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex flex-wrap items-center gap-2">
              <Button
                disabled={currentPage <= 1}
                type="button"
                variant="secondary"
                onClick={() => goToPage(currentPage - 1)}
              >
                {t('search.previous')}
              </Button>
              <div className="flex flex-wrap items-center gap-1">
                {paginationItems.map((item, index) =>
                  item === 'ellipsis' ? (
                    <span className="px-2 text-neutral-400" key={`ellipsis-${index}`}>
                      ...
                    </span>
                  ) : (
                    <Button
                      className="min-w-10 px-3"
                      key={item}
                      size="sm"
                      type="button"
                      variant={item === currentPage ? 'default' : 'secondary'}
                      onClick={() => goToPage(item)}
                    >
                      {item}
                    </Button>
                  ),
                )}
              </div>
              <Button
                disabled={currentPage >= totalPages}
                type="button"
                variant="secondary"
                onClick={() => goToPage(currentPage + 1)}
              >
                {t('search.next')}
              </Button>
            </div>

            <form className="flex items-center gap-2" onSubmit={handleJumpSubmit}>
              <span className="whitespace-nowrap">{t('search.page')}</span>
              <Input
                className="h-10 w-20 px-3"
                inputMode="numeric"
                min={1}
                max={totalPages}
                type="number"
                value={jumpPage}
                placeholder={String(currentPage)}
                onChange={(event) => setJumpPage(event.target.value)}
              />
              <Button size="sm" type="submit" variant="secondary">
                {t('search.go')}
              </Button>
            </form>
          </div>
        ) : null}
      </section>
    </div>
  );
}
