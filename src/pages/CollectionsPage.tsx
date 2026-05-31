import { useQuery } from '@tanstack/react-query';
import { libraryQueries } from '@/features/library/library-queries';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';

export function CollectionsPage() {
  const collectionsQuery = useQuery(libraryQueries.collections({ page_size: 24, ordering: '-id' }));

  return (
    <Page title="Collections" eyebrow="Marked" description="Curated groups of subjects with notes, ordering, and relations.">
      {collectionsQuery.isLoading ? <LoadingState title="Loading collections" /> : null}
      {collectionsQuery.isError ? <ErrorState title="Unable to load collections." description="Please try again later." /> : null}
      {!collectionsQuery.isLoading && !collectionsQuery.isError && collectionsQuery.data?.results.length === 0 ? (
        <EmptyState title="No collections yet." description="Collections will help you group works by theme, memory, or recommendation." />
      ) : null}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {(collectionsQuery.data?.results ?? []).map((collection) => (
          <article className="rounded-xl border border-neutral-200 bg-white p-5 shadow-sm dark:border-neutral-800 dark:bg-neutral-950" key={collection.id}>
            <div className="flex items-start justify-between gap-4">
              <h2 className="min-w-0 truncate text-lg font-semibold tracking-tight text-neutral-950 dark:text-white">{collection.name}</h2>
              <span className="rounded-full bg-neutral-100 px-2 py-1 text-xs font-semibold text-neutral-500 dark:bg-neutral-900 dark:text-neutral-400">
                {collection.item_count ?? 0}
              </span>
            </div>
            {collection.note ? <p className="mt-3 line-clamp-3 text-sm leading-6 text-neutral-500 dark:text-neutral-400">{collection.note}</p> : null}
          </article>
        ))}
      </div>
    </Page>
  );
}
