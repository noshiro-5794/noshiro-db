import { type SyntheticEvent, useMemo, useState } from 'react';
import { Link, useLocation } from '@tanstack/react-router';
import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ExternalLink, Layers3, Pencil, Trash2 } from 'lucide-react';
import { libraryMutations, libraryQueries } from '@/entities/library';
import type { Collection } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { routeBackState } from '@/shared/routing/route-state';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/shared/ui/Dialog';
import { ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { toast } from '@/shared/ui/toast';
import { collectionDraftOf, emptyCollectionDraft, type CollectionDraft } from '../model/draft';
import { invalidateCollectionViews } from '../model/cache';
import { collectionRatingLabel, collectionTitle } from '../model/presentation';
import { AddCollectionItemDialog } from './AddCollectionItemDialog';
import { CollectionForm } from './CollectionForm';
import { CollectionItemRail } from './CollectionItemRail';
import { CollectionRatingStars } from './CollectionRatingStars';

const itemPageSize = 64;

type CollectionDetailPanelProps = {
  collection: Collection | null;
  collectionId: number | null;
  isError: boolean;
  isLoading: boolean;
  publicProfileUserId: number;
  onDeleted: () => void;
};

export function CollectionDetailPanel({
  collection,
  collectionId,
  isError,
  isLoading,
  publicProfileUserId,
  onDeleted,
}: CollectionDetailPanelProps) {
  const { t } = useI18n();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [editDraft, setEditDraft] = useState<CollectionDraft>(emptyCollectionDraft);
  const itemsQuery = useInfiniteQuery({
    ...libraryQueries.collectionItemsInfinite(collectionId ?? 0, itemPageSize),
    enabled: collectionId !== null,
  });
  const loadedItems = useMemo(() => itemsQuery.data?.pages.flatMap((page) => page.results) ?? [], [itemsQuery.data]);
  const itemCount = itemsQuery.data?.pages[0]?.count ?? collection?.item_count ?? 0;
  const invalidateCollection = (includeComments = false) =>
    invalidateCollectionViews(queryClient, {
      includeComments,
      userId: publicProfileUserId || undefined,
    });
  const showMutationError = () => toast.error(t('common.requestFailed'));

  const updateCollectionMutation = useMutation({
    ...libraryMutations.updateCollection(),
    onError: showMutationError,
    onSuccess: async () => {
      setEditOpen(false);
      await invalidateCollection();
      toast.success(t('collections.updated'));
    },
  });
  const deleteCollectionMutation = useMutation({
    ...libraryMutations.deleteCollection(),
    onError: showMutationError,
    onSuccess: async () => {
      setDeleteOpen(false);
      await invalidateCollection(true);
      onDeleted();
      toast.success(t('collections.deleted'));
    },
  });
  const updateItemsMutation = useMutation({
    ...libraryMutations.updateCollectionItems(),
    onError: showMutationError,
    onSuccess: async () => {
      await invalidateCollection();
      toast.success(t('collections.orderSaved'));
    },
  });
  const deleteItemMutation = useMutation({
    ...libraryMutations.deleteCollectionItem(),
    onError: showMutationError,
    onSuccess: async () => {
      await invalidateCollection();
    },
  });

  function submitUpdate(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (!collection || updateCollectionMutation.isPending) return;
    const name = editDraft.name.trim();
    if (!name) return;

    updateCollectionMutation.mutate({
      collectionId: collection.id,
      body: {
        name,
        note: editDraft.note.trim(),
        ...(editDraft.rating === null ? {} : { simple_rating: editDraft.rating }),
        is_public: editDraft.isPublic,
      },
    });
  }

  if (collectionId !== null && isLoading && !collection) {
    return <LoadingState title={t('calendar.loading')} />;
  }
  if (isError && !collection) {
    return <ErrorState title={t('collections.errorTitle')} description={t('search.errorBody')} />;
  }
  if (!collection) {
    return (
      <div className="collection-empty-state">
        <div className="max-w-sm">
          <div className="collection-empty-icon">
            <Layers3 className="size-5" />
          </div>
          <h2 className="mt-4 text-lg font-semibold tracking-normal text-[var(--ui-text)]">
            {t('collections.chooseTitle')}
          </h2>
        </div>
      </div>
    );
  }

  return (
    <div className="grid min-w-0 gap-5">
      <div className="collection-editor-surface min-w-0 p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={collection.is_public ? 'accent' : 'secondary'}>
                {collection.is_public ? t('common.public') : t('common.private')}
              </Badge>
              <Badge>
                {itemCount} {t('common.items')}
              </Badge>
            </div>
            <h2 className="mt-3 text-2xl font-semibold tracking-normal text-[var(--ui-text)]">
              {collectionTitle(collection, t('collections.chooseTitle'))}
            </h2>
            {collection.note ? (
              <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--ui-text-muted)]">{collection.note}</p>
            ) : (
              <p className="mt-2 text-sm text-[var(--ui-text-subtle)]">{t('common.noNote')}</p>
            )}
            <div className="mt-4 flex items-center gap-3">
              <CollectionRatingStars label={t('common.unrated')} value={collection.simple_rating} />
              <span className="text-sm text-[var(--ui-text-muted)]">
                {collectionRatingLabel(collection.simple_rating, t('common.unrated'))}
              </span>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {collection.is_public && Number.isFinite(publicProfileUserId) && publicProfileUserId > 0 ? (
              <Button asChild type="button" variant="secondary">
                <Link
                  params={{ collectionId: String(collection.id), userId: String(publicProfileUserId) }}
                  state={routeBackState(location, t('collections.title'))}
                  to="/users/$userId/collections/$collectionId"
                >
                  <ExternalLink className="size-4" />
                  {t('collections.viewPublic')}
                </Link>
              </Button>
            ) : null}

            <AddCollectionItemDialog
              collectionId={collection.id}
              itemCount={itemCount}
              publicProfileUserId={publicProfileUserId}
            />

            <Dialog
              open={editOpen}
              onOpenChange={(open) => {
                if (open) setEditDraft(collectionDraftOf(collection));
                setEditOpen(open);
              }}
            >
              <DialogTrigger render={<Button type="button" variant="secondary" />}>
                <Pencil className="size-4" />
                {t('common.edit')}
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>{t('collections.editTitle')}</DialogTitle>
                  <DialogDescription>{t('collections.editDescription')}</DialogDescription>
                </DialogHeader>
                <CollectionForm
                  draft={editDraft}
                  isPending={updateCollectionMutation.isPending}
                  submitLabel={t('common.save')}
                  onCancel={() => {
                    setEditOpen(false);
                  }}
                  onChange={setEditDraft}
                  onSubmit={submitUpdate}
                />
              </DialogContent>
            </Dialog>

            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setDeleteOpen(true);
              }}
            >
              <Trash2 className="size-4" />
              {t('common.delete')}
            </Button>
            <ConfirmDialog
              confirmIcon={<Trash2 className="size-4" />}
              confirmLabel={t('common.delete')}
              description={t('collections.deleteDescription')}
              details={
                <div className="rounded-sm border border-border bg-muted px-3 py-2 text-sm font-medium text-foreground">
                  {collection.name}
                </div>
              }
              isPending={deleteCollectionMutation.isPending}
              open={deleteOpen}
              title={t('collections.deleteTitle')}
              onConfirm={() => {
                if (!deleteCollectionMutation.isPending) deleteCollectionMutation.mutate(collection.id);
              }}
              onOpenChange={setDeleteOpen}
            />
          </div>
        </div>
      </div>

      <CollectionItemRail
        hasNextPage={itemsQuery.hasNextPage}
        isDeleting={deleteItemMutation.isPending}
        isError={itemsQuery.isError}
        isFetching={itemsQuery.isFetching}
        isFetchingNextPage={itemsQuery.isFetchingNextPage}
        isLoading={itemsQuery.isLoading}
        isSaving={updateItemsMutation.isPending}
        itemCount={itemCount}
        loadedItems={loadedItems}
        onDelete={(itemId) => {
          if (collectionId !== null && !deleteItemMutation.isPending) {
            deleteItemMutation.mutate({ collectionId, itemId });
          }
        }}
        onLoadMore={() => {
          void itemsQuery.fetchNextPage();
        }}
        onSave={(items) => {
          if (collectionId !== null && !updateItemsMutation.isPending) {
            updateItemsMutation.mutate({ collectionId, items });
          }
        }}
      />
      {isError ? <ErrorState title={t('collections.errorTitle')} description={t('search.errorBody')} /> : null}
    </div>
  );
}
