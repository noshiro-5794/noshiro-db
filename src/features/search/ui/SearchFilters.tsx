import { type SyntheticEvent, useEffect, useMemo, useState } from 'react';
import { X } from 'lucide-react';
import type { SearchPageSearch } from '@/shared/routing/route-search';
import { useI18n } from '@/shared/i18n';
import { Button } from '@/shared/ui/Button';
import { DataToolbar, DataToolbarFilters, DataToolbarPrimary, DataToolbarRow, SearchField } from '@/shared/ui/DataView';
import { FilterCombobox } from '@/shared/ui/FilterCombobox';
import { FilterMenu } from '@/shared/ui/FilterMenu';
import { InputGroup, InputGroupAddon, InputGroupInput } from '@/shared/ui/InputGroup';
import {
  episodeRangeOptions,
  orderingOptions,
  platformOptions,
  safetyOptions,
  seasonOptions,
  subjectTypeOptions,
} from '../model/search-options';

type SearchFilterKey = 'type' | 'sourceId' | 'year' | 'season' | 'sort' | 'platform' | 'episodes' | 'safety';

const defaultSearchFilters: SearchFilterKey[] = ['type', 'year', 'season', 'sort'];
const allFilters: SearchFilterKey[] = ['type', 'sourceId', 'year', 'season', 'sort', 'platform', 'episodes', 'safety'];
const searchParamByFilter: Record<SearchFilterKey, keyof SearchPageSearch> = {
  type: 'subject_type',
  sourceId: 'source_id',
  year: 'year',
  season: 'season',
  sort: 'ordering',
  platform: 'platform',
  episodes: 'episodes',
  safety: 'nsfw',
};

function routeFiltersOf(search: SearchPageSearch): SearchFilterKey[] {
  const filters: SearchFilterKey[] = [];
  if (search.source_id) filters.push('sourceId');
  if (search.platform) filters.push('platform');
  if (search.episodes) filters.push('episodes');
  if (search.nsfw !== undefined) filters.push('safety');
  return filters;
}

export function SearchFilters({
  search,
  onChange,
}: {
  search: SearchPageSearch;
  onChange: (key: keyof SearchPageSearch, value: string) => void;
}) {
  const { t } = useI18n();
  const keyword = search.keyword ?? '';
  const [draftKeyword, setDraftKeyword] = useState(keyword);
  const [activeFilters, setActiveFilters] = useState<SearchFilterKey[]>(() => [
    ...defaultSearchFilters,
    ...routeFiltersOf(search),
  ]);
  const currentYear = new Date().getFullYear();
  const maximumYear = currentYear + 5;
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
  const availableFilters = allFilters.filter((filter) => !activeFilters.includes(filter));
  const yearOptions = useMemo(
    () => [
      { label: t('search.all'), value: '' },
      ...Array.from({ length: currentYear - 1999 }, (_, index) => {
        const optionYear = String(currentYear - index);
        return { label: optionYear, value: optionYear };
      }),
    ],
    [currentYear, t],
  );

  useEffect(() => {
    setDraftKeyword(keyword);
  }, [keyword]);

  useEffect(() => {
    const routeFilters = routeFiltersOf(search);
    setActiveFilters((current) => {
      const missingFilters = routeFilters.filter((filter) => !current.includes(filter));
      return missingFilters.length > 0 ? [...current, ...missingFilters] : current;
    });
  }, [search]);

  function submit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    onChange('keyword', draftKeyword.trim());
  }

  function removeFilter(filter: SearchFilterKey) {
    setActiveFilters((current) => current.filter((item) => item !== filter));
    onChange(searchParamByFilter[filter], '');
  }

  return (
    <DataToolbar onSubmit={submit}>
      <DataToolbarRow className="lg:grid-cols-[minmax(0,1fr)_auto]">
        <DataToolbarPrimary>
          <SearchField
            aria-label={t('search.keyword')}
            maxLength={200}
            placeholder={t('public.searchPlaceholder')}
            value={draftKeyword}
            onChange={(event) => {
              const value = event.target.value;
              setDraftKeyword(value);
              if (!value.trim()) onChange('keyword', '');
            }}
          />
        </DataToolbarPrimary>
        <Button className="w-full lg:w-auto" size="lg" type="submit" variant="secondary">
          {t('search.title')}
        </Button>
      </DataToolbarRow>

      <DataToolbarFilters>
        {activeFilters.map((filter) => (
          <div
            className={
              defaultSearchFilters.includes(filter)
                ? 'w-full min-w-0 sm:w-44'
                : 'grid w-full min-w-0 grid-cols-[minmax(0,1fr)_32px] gap-1 sm:w-[calc(11rem+2.25rem)]'
            }
            key={filter}
          >
            {filter === 'type' ? (
              <FilterMenu
                label={filterLabels.type}
                options={subjectTypeOptions.map((option) => ({ label: t(option.labelKey), value: option.value }))}
                value={search.subject_type ?? ''}
                onChange={(value) => {
                  onChange('subject_type', value);
                }}
              />
            ) : null}
            {filter === 'sourceId' ? (
              <InputGroup className="h-[var(--ui-control-height)]">
                <InputGroupAddon className="pr-0 text-xs">{filterLabels.sourceId}</InputGroupAddon>
                <InputGroupInput
                  aria-label={filterLabels.sourceId}
                  className="font-medium"
                  inputMode="numeric"
                  maxLength={64}
                  pattern="[0-9]*"
                  placeholder={t('search.sourceIdPlaceholder')}
                  value={search.source_id ?? ''}
                  onChange={(event) => {
                    onChange('source_id', event.target.value.replace(/\D/gu, ''));
                  }}
                />
              </InputGroup>
            ) : null}
            {filter === 'year' ? (
              <FilterCombobox
                createValue={(value) =>
                  /^\d{4}$/u.test(value) && Number(value) >= 1900 && Number(value) <= maximumYear ? value : null
                }
                label={filterLabels.year}
                options={yearOptions}
                placeholder={t('search.year')}
                value={search.year ? String(search.year) : ''}
                onChange={(value) => {
                  onChange('year', value);
                }}
              />
            ) : null}
            {filter === 'season' ? (
              <FilterMenu
                label={filterLabels.season}
                options={seasonOptions.map((option) => ({ label: t(option.labelKey), value: option.value }))}
                value={search.season ?? ''}
                onChange={(value) => {
                  onChange('season', value);
                }}
              />
            ) : null}
            {filter === 'sort' ? (
              <FilterMenu
                label={filterLabels.sort}
                options={orderingOptions.map((option) => ({ label: t(option.labelKey), value: option.value }))}
                value={search.ordering ?? '-date'}
                onChange={(value) => {
                  onChange('ordering', value === '-date' ? '' : value);
                }}
              />
            ) : null}
            {filter === 'platform' ? (
              <FilterMenu
                label={filterLabels.platform}
                options={platformOptions.map((option) => ({
                  label: option.value ? option.label : t('search.all'),
                  value: option.value,
                }))}
                value={search.platform ?? ''}
                onChange={(value) => {
                  onChange('platform', value);
                }}
              />
            ) : null}
            {filter === 'episodes' ? (
              <FilterMenu
                label={filterLabels.episodes}
                options={episodeRangeOptions.map((option) => ({ label: t(option.labelKey), value: option.value }))}
                value={search.episodes ?? ''}
                onChange={(value) => {
                  onChange('episodes', value);
                }}
              />
            ) : null}
            {filter === 'safety' ? (
              <FilterMenu
                label={filterLabels.safety}
                options={safetyOptions.map((option) => ({ label: t(option.labelKey), value: option.value }))}
                value={search.nsfw === false ? 'safe' : 'all'}
                onChange={(value) => {
                  onChange('nsfw', value === 'safe' ? 'false' : '');
                }}
              />
            ) : null}
            {!defaultSearchFilters.includes(filter) ? (
              <Button
                aria-label={`${t('common.clear')} ${filterLabels[filter]}`}
                className="self-end text-[var(--ui-text-subtle)] hover:text-[var(--ui-text)]"
                size="icon"
                tooltip={`${t('common.clear')} ${filterLabels[filter]}`}
                type="button"
                variant="ghost"
                onClick={() => {
                  removeFilter(filter);
                }}
              >
                <X className="size-4" />
              </Button>
            ) : null}
          </div>
        ))}

        {availableFilters.length > 0 ? (
          <div className="w-full min-w-0 sm:w-44">
            <FilterMenu
              label={t('search.addFilter')}
              options={[
                { label: t('search.addFilter'), value: '' },
                ...availableFilters.map((filter) => ({ label: filterLabels[filter], value: filter })),
              ]}
              value=""
              onChange={(filter) => {
                if (filter && !activeFilters.includes(filter)) {
                  setActiveFilters((current) => [...current, filter]);
                }
              }}
            />
          </div>
        ) : null}
      </DataToolbarFilters>
    </DataToolbar>
  );
}
