import { useEffect, useMemo } from 'react';
import { getRouteApi } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import { libraryQueries } from '@/entities/library';
import { useAuth } from '@/entities/session';
import {
  CollectionDetailPanel,
  CollectionListSidebar,
  CreateCollectionDialog,
  parseCollectionOrdering,
} from '@/features/collection-editor';
import { ApiError, type Collection } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { cn } from '@/shared/lib/cn';
import { useMediaQuery } from '@/shared/lib/use-media-query';
import { Button } from '@/shared/ui/Button';
import { Page } from '@/shared/ui/Page';

const pageSize = 4;
const emptyCollections: Collection[] = [];
const collectionsRoute = getRouteApi('/collections');

export function CollectionsPage() {
  const { t } = useI18n();
  const { profile } = useAuth();
  const isDesktop = useMediaQuery('(min-width: 1280px)');
  const navigate = collectionsRoute.useNavigate();
  const search = collectionsRoute.useSearch();
  const keyword = search.keyword ?? '';
  const ordering = parseCollectionOrdering(search.ordering ?? null);
  const currentPage = search.page ?? 1;
  const selectedCollectionId = search.collection ?? null;
  const collectionQuery = useMemo(
    () => ({
      ...(keyword ? { keyword } : {}),
      ordering,
      page: currentPage,
      page_size: pageSize,
    }),
    [currentPage, keyword, ordering],
  );
  const collectionsQuery = useQuery(libraryQueries.collections(collectionQuery));
  const collections = collectionsQuery.data?.results ?? emptyCollections;
  const selectedCollectionFromList = collections.find(({ id }) => id === selectedCollectionId) ?? null;
  const selectedCollectionQuery = useQuery({
    ...libraryQueries.collection(selectedCollectionId ?? 0),
    enabled: selectedCollectionId !== null,
  });
  const selectedCollection = selectedCollectionQuery.data ?? selectedCollectionFromList;
  const totalCount = collectionsQuery.data?.count ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const publicProfileUserId = profile?.user_id ?? 0;

  useEffect(() => {
    const firstCollection = collections[0];
    if (isDesktop && selectedCollectionId === null && firstCollection) {
      void navigate({ search: (current) => ({ ...current, collection: firstCollection.id }) });
    }
  }, [collections, isDesktop, navigate, selectedCollectionId]);

  useEffect(() => {
    if (collectionsQuery.data && currentPage > totalPages) {
      void navigate({ replace: true, search: (current) => ({ ...current, page: totalPages }) });
    }
  }, [collectionsQuery.data, currentPage, navigate, totalPages]);

  useEffect(() => {
    if (!(selectedCollectionQuery.error instanceof ApiError) || selectedCollectionQuery.error.status !== 404) return;

    void navigate({
      replace: true,
      search: (current) => ({
        ...current,
        collection: collections.find(({ id }) => id !== selectedCollectionId)?.id,
      }),
    });
  }, [collections, navigate, selectedCollectionId, selectedCollectionQuery.error]);

  return (
    <Page
      actions={
        <CreateCollectionDialog
          publicProfileUserId={publicProfileUserId}
          onCreated={(collectionId) => {
            void navigate({ search: (current) => ({ ...current, collection: collectionId, page: undefined }) });
          }}
        />
      }
      eyebrow={t('nav.groupLibrary')}
      title={t('collections.title')}
    >
      <div className="grid min-w-0 gap-5 xl:grid-cols-[340px_minmax(0,1fr)]">
        <div className={cn(selectedCollectionId !== null && 'max-xl:hidden')}>
          <CollectionListSidebar
            collections={collections}
            currentPage={currentPage}
            isError={collectionsQuery.isError}
            isFetching={collectionsQuery.isFetching}
            isLoading={collectionsQuery.isLoading}
            keyword={keyword}
            ordering={ordering}
            selectedCollectionId={selectedCollectionId}
            totalCount={totalCount}
            totalPages={totalPages}
            onOrderingChange={(nextOrdering) => {
              void navigate({
                search: (current) => ({
                  ...current,
                  collection: undefined,
                  ordering: nextOrdering,
                  page: undefined,
                }),
              });
            }}
            onPageChange={(page) => {
              void navigate({
                search: (current) => ({
                  ...current,
                  collection: undefined,
                  page: Math.min(Math.max(page, 1), totalPages),
                }),
              });
            }}
            onSearch={(nextKeyword) => {
              void navigate({
                search: (current) => ({
                  ...current,
                  collection: undefined,
                  keyword: nextKeyword || undefined,
                  page: undefined,
                }),
              });
            }}
            onSelect={(collectionId) => {
              void navigate({ search: (current) => ({ ...current, collection: collectionId }) });
            }}
          />
        </div>

        <section className={cn('min-w-0', selectedCollectionId === null && 'max-xl:hidden')}>
          <Button
            className="mb-3 xl:hidden"
            size="sm"
            type="button"
            variant="ghost"
            onClick={() => {
              void navigate({ search: (current) => ({ ...current, collection: undefined }) });
            }}
          >
            <ArrowLeft className="size-4" />
            {t('nav.collections')}
          </Button>
          <CollectionDetailPanel
            collection={selectedCollection}
            collectionId={selectedCollectionId}
            isError={selectedCollectionQuery.isError}
            isLoading={selectedCollectionQuery.isLoading}
            publicProfileUserId={publicProfileUserId}
            onDeleted={() => {
              void navigate({ search: (current) => ({ ...current, collection: undefined }) });
            }}
          />
        </section>
      </div>
    </Page>
  );
}
