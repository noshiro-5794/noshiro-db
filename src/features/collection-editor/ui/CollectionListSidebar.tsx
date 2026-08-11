import { type SyntheticEvent, useEffect, useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import type { Collection } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { cn } from '@/shared/lib/cn';
import { Button } from '@/shared/ui/Button';
import {
  DataToolbar,
  DataToolbarPrimary,
  DataToolbarRow,
  ResultsMeta,
  ResultsState,
  SearchField,
  type ResultsStatus,
} from '@/shared/ui/DataView';
import { FilterMenu } from '@/shared/ui/FilterMenu';
import { Pagination } from '@/shared/ui/Pagination';
import type { CollectionOrdering } from '../model/reorder';
import { CollectionPackCover } from './CollectionPackCover';
import { CollectionRatingStars } from './CollectionRatingStars';

type CollectionListSidebarProps = {
  collections: Collection[];
  currentPage: number;
  isError: boolean;
  isFetching: boolean;
  isLoading: boolean;
  keyword: string;
  ordering: CollectionOrdering;
  selectedCollectionId: number | null;
  totalCount: number;
  totalPages: number;
  onOrderingChange: (ordering: CollectionOrdering) => void;
  onPageChange: (page: number) => void;
  onSearch: (keyword: string) => void;
  onSelect: (collectionId: number) => void;
};

export function CollectionListSidebar({
  collections,
  currentPage,
  isError,
  isFetching,
  isLoading,
  keyword,
  ordering,
  selectedCollectionId,
  totalCount,
  totalPages,
  onOrderingChange,
  onPageChange,
  onSearch,
  onSelect,
}: CollectionListSidebarProps) {
  const { t } = useI18n();
  const [draftKeyword, setDraftKeyword] = useState(keyword);
  const orderingOptions: Array<{ label: string; value: CollectionOrdering }> = [
    { label: t('collections.sortNewest'), value: '-id' },
    { label: t('collections.sortOldest'), value: 'id' },
    { label: t('collections.sortNameAsc'), value: 'name' },
    { label: t('collections.sortNameDesc'), value: '-name' },
    { label: t('collections.sortMostItems'), value: '-item_count' },
    { label: t('collections.sortHighestRating'), value: '-simple_rating' },
  ];
  const resultsStatus: ResultsStatus = isLoading
    ? 'loading'
    : isError
      ? 'error'
      : collections.length === 0
        ? 'empty'
        : 'ready';

  useEffect(() => {
    setDraftKeyword(keyword);
  }, [keyword]);

  function submitSearch(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    onSearch(draftKeyword.trim());
  }

  return (
    <aside className="grid content-start gap-5">
      <DataToolbar onSubmit={submitSearch}>
        <DataToolbarRow>
          <DataToolbarPrimary>
            <SearchField
              aria-label={t('collections.searchPlaceholder')}
              maxLength={200}
              placeholder={t('collections.searchPlaceholder')}
              value={draftKeyword}
              onChange={(event) => {
                setDraftKeyword(event.target.value);
              }}
            />
          </DataToolbarPrimary>
          <FilterMenu
            label={t('common.sort')}
            options={orderingOptions}
            size="lg"
            value={ordering}
            onChange={onOrderingChange}
          />
          <Button size="lg" type="submit" variant="secondary">
            {t('common.search')}
          </Button>
        </DataToolbarRow>
      </DataToolbar>

      <ResultsMeta
        count={isLoading ? undefined : totalCount}
        label={t('nav.collections')}
        pending={isFetching && !isLoading}
        pendingLabel={t('common.loading')}
      />

      <ResultsState
        emptyDescription={t('collections.emptyBody')}
        emptyTitle={t('collections.emptyTitle')}
        errorDescription={t('search.errorBody')}
        errorTitle={t('collections.errorTitle')}
        loadingTitle={t('calendar.loading')}
        status={resultsStatus}
      >
        <>
          <div className="grid gap-2">
            {collections.map((collection) => {
              const isSelected = collection.id === selectedCollectionId;
              return (
                <Button
                  className={cn(
                    'group grid min-w-0 gap-3 rounded-md border border-border bg-surface p-3.5 text-left text-foreground transition-colors hover:border-[var(--ui-accent-border)] hover:bg-muted',
                    isSelected &&
                      'border-[var(--ui-accent-border)] bg-muted shadow-[inset_0_0_0_1px_color-mix(in_srgb,var(--ui-accent-border)_24%,transparent)]',
                  )}
                  data-slot="collection-selector-card"
                  key={collection.id}
                  type="button"
                  variant="unstyled"
                  onClick={() => {
                    onSelect(collection.id);
                  }}
                >
                  <CollectionPackCover collectionId={collection.id} hasItems={(collection.item_count ?? 0) > 0} />
                  <div className="flex items-start justify-between gap-3">
                    <h2 className="min-w-0 truncate text-sm font-semibold">{collection.name}</h2>
                    <span
                      className={cn(
                        'rounded-full px-2 py-0.5 text-xs font-semibold',
                        isSelected
                          ? 'bg-[var(--ui-bg-elevated)] text-[var(--ui-text-muted)]'
                          : 'bg-[var(--ui-bg-subtle)] text-[var(--ui-text-muted)]',
                      )}
                    >
                      {collection.item_count ?? 0}
                    </span>
                  </div>
                  {collection.note ? (
                    <p className="mt-2 line-clamp-2 text-xs leading-5 text-[var(--ui-text-muted)]">{collection.note}</p>
                  ) : null}
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <CollectionRatingStars label={t('common.unrated')} value={collection.simple_rating} />
                    {collection.is_public ? (
                      <Eye className="size-4 opacity-60" />
                    ) : (
                      <EyeOff className="size-4 opacity-60" />
                    )}
                  </div>
                </Button>
              );
            })}
          </div>

          <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={onPageChange} />
        </>
      </ResultsState>
    </aside>
  );
}
