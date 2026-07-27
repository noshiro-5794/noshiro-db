import { type DragEvent, type FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useLocation, useSearchParams } from '@/shared/routing/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Eye,
  EyeOff,
  ExternalLink,
  GripVertical,
  Layers3,
  ListOrdered,
  Pencil,
  Plus,
  Search,
  Star,
  Trash2,
} from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/entities/session';
import { libraryMutations, libraryQueries, libraryQueryKeys } from '@/entities/library';
import { useI18n } from '@/shared/i18n';
import type { Collection, CollectionItem, UserSubject } from '@/shared/api';
import { cn } from '@/shared/lib/cn';
import { routes } from '@/shared/routing/paths';
import { routeBackState } from '@/shared/routing/route-state';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/shared/ui/Dialog';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { FilterMenu } from '@/shared/ui/FilterMenu';
import { Input } from '@/shared/ui/Input';
import { Page } from '@/shared/ui/Page';
import { Pagination } from '@/shared/ui/Pagination';

const pageSize = 4;
const itemPageSize = 1000;
const emptyCollections: Collection[] = [];

type CollectionOrdering =
  'id' | '-id' | 'name' | '-name' | 'simple_rating' | '-simple_rating' | 'item_count' | '-item_count';
type DropPosition = 'before' | 'after';
type DropPreview = { itemId: number; position: DropPosition } | null;

function collectionTitle(collection: Collection | null, fallback: string) {
  return collection?.name || fallback;
}

function subjectTitle(item: CollectionItem, fallback: string) {
  return item.subject.display_title || item.subject.title || item.subject.title_cn || fallback;
}

function subjectSubtitle(item: CollectionItem, fallback: string) {
  const parts = [
    item.subject.subject_type,
    item.subject.date,
    item.subject.platform,
    item.user_subject.status ? item.user_subject.status.replaceAll('_', ' ') : null,
  ].filter(Boolean);

  return parts.join(' / ') || fallback;
}

function subjectImage(item: CollectionItem) {
  return item.subject.images?.thumbnail || item.subject.image_thumbnail || item.subject.image || null;
}

function userSubjectTitle(item: UserSubject, fallback: string) {
  return item.subject.display_title || item.subject.title || item.subject.title_cn || fallback;
}

function userSubjectSubtitle(item: UserSubject, fallback: string) {
  const parts = [
    item.subject.subject_type,
    item.subject.date,
    item.subject.platform,
    item.status.replaceAll('_', ' '),
  ].filter(Boolean);
  return parts.join(' / ') || fallback;
}

function userSubjectImage(item: UserSubject) {
  return item.subject.images?.thumbnail || item.subject.image_thumbnail || item.subject.image || null;
}

function starLabel(value: number | null | undefined, fallback: string) {
  if (!value) return fallback;
  return `${value}/5`;
}

function RatingStars({
  value,
  label,
  interactive = false,
  onChange,
}: {
  value?: number | null;
  label: string;
  interactive?: boolean;
  onChange?: (value: number | null) => void;
}) {
  return (
    <div className="flex items-center gap-0.5" aria-label={starLabel(value, label)}>
      {[1, 2, 3, 4, 5].map((rating) => {
        const filled = Boolean(value && rating <= value);
        const star = (
          <Star
            className={cn(
              'size-4',
              filled
                ? 'fill-[var(--color-accent)] text-[var(--color-accent)]'
                : 'text-neutral-300 dark:text-neutral-700',
            )}
          />
        );

        if (!interactive || !onChange) {
          return <span key={rating}>{star}</span>;
        }

        return (
          <button
            aria-label={`Set ${rating} stars`}
            className="rounded-full p-0.5 transition hover:bg-neutral-100 dark:hover:bg-neutral-900"
            key={rating}
            type="button"
            onClick={() => onChange(value === rating ? null : rating)}
          >
            {star}
          </button>
        );
      })}
    </div>
  );
}

function moveItemToDrop<T>(items: T[], fromIndex: number, targetIndex: number, position: DropPosition) {
  const nextItems = [...items];
  const [movedItem] = nextItems.splice(fromIndex, 1);
  let insertIndex = position === 'after' ? targetIndex + 1 : targetIndex;
  if (fromIndex < insertIndex) insertIndex -= 1;
  nextItems.splice(Math.max(0, Math.min(insertIndex, nextItems.length)), 0, movedItem);
  return nextItems;
}

function moveItemToPosition(items: CollectionItem[], itemId: number, position: number) {
  const fromIndex = items.findIndex((item) => item.id === itemId);
  if (fromIndex < 0) return items;

  const nextItems = [...items];
  const [movedItem] = nextItems.splice(fromIndex, 1);
  const insertIndex = Math.max(0, Math.min(position - 1, nextItems.length));
  nextItems.splice(insertIndex, 0, movedItem);
  return nextItems;
}

function CollectionPackCover({ collectionId }: { collectionId: number }) {
  const previewQuery = useQuery({
    ...libraryQueries.collectionItems(collectionId, { page: 1, page_size: 4 }),
  });
  const previewItems = previewQuery.data?.results ?? [];

  return (
    <div className="collection-pack-cover" aria-hidden>
      {[0, 1, 2, 3].map((slot) => {
        const coverItem = previewItems[slot];
        return (
          <span className="collection-pack-layer" data-slot={slot} key={slot}>
            {coverItem && subjectImage(coverItem) ? (
              <img alt="" src={subjectImage(coverItem) ?? ''} loading="lazy" />
            ) : null}
          </span>
        );
      })}
    </div>
  );
}

export function CollectionsPage() {
  const { t } = useI18n();
  const { profile } = useAuth();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const keyword = searchParams.get('keyword') ?? '';
  const ordering = (searchParams.get('ordering') ?? '-id') as CollectionOrdering;
  const currentPage = Math.max(1, Number(searchParams.get('page') ?? '1') || 1);
  const selectedCollectionId = Number(searchParams.get('collection') ?? '') || null;
  const [draftKeyword, setDraftKeyword] = useState(keyword);
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [addKeyword, setAddKeyword] = useState('');
  const [newName, setNewName] = useState('');
  const [newNote, setNewNote] = useState('');
  const [newRating, setNewRating] = useState<number | null>(null);
  const [newIsPublic, setNewIsPublic] = useState(true);
  const [editName, setEditName] = useState('');
  const [editNote, setEditNote] = useState('');
  const [editRating, setEditRating] = useState<number | null>(null);
  const [editIsPublic, setEditIsPublic] = useState(true);
  const [items, setItems] = useState<CollectionItem[]>([]);
  const [draggingItemId, setDraggingItemId] = useState<number | null>(null);
  const [dropPreview, setDropPreview] = useState<DropPreview>(null);
  const [quickSortItem, setQuickSortItem] = useState<CollectionItem | null>(null);
  const [quickSortPosition, setQuickSortPosition] = useState('');
  const [isOrderDirty, setIsOrderDirty] = useState(false);
  const railRef = useRef<HTMLDivElement | null>(null);
  const autoScrollFrameRef = useRef<number | null>(null);
  const autoScrollVelocityRef = useRef(0);
  const isDraggingRef = useRef(false);
  const lastDragClientXRef = useRef<number | null>(null);
  const queryClient = useQueryClient();
  const orderingOptions: Array<{ label: string; value: CollectionOrdering }> = [
    { label: t('collections.sortNewest'), value: '-id' },
    { label: t('collections.sortOldest'), value: 'id' },
    { label: t('collections.sortNameAsc'), value: 'name' },
    { label: t('collections.sortNameDesc'), value: '-name' },
    { label: t('collections.sortMostItems'), value: '-item_count' },
    { label: t('collections.sortHighestRating'), value: '-simple_rating' },
  ];

  const collectionQuery = useMemo(
    () => ({
      keyword: keyword || undefined,
      ordering,
      page: currentPage,
      page_size: pageSize,
    }),
    [currentPage, keyword, ordering],
  );
  const collectionsQuery = useQuery(libraryQueries.collections(collectionQuery));
  const collections = collectionsQuery.data?.results ?? emptyCollections;
  const selectedCollectionFromList = collections.find((collection) => collection.id === selectedCollectionId) ?? null;
  const selectedCollectionQuery = useQuery({
    ...libraryQueries.collection(selectedCollectionId || 0),
    enabled: Boolean(selectedCollectionId),
  });
  const selectedCollection = selectedCollectionQuery.data ?? selectedCollectionFromList;
  const itemsQuery = useQuery({
    ...libraryQueries.collectionItems(selectedCollectionId || 0, { page: 1, page_size: itemPageSize }),
    enabled: Boolean(selectedCollectionId),
  });
  const librarySearchQuery = useQuery({
    ...libraryQueries.userSubjects({
      keyword: addKeyword.trim() || undefined,
      ordering: '-updated_at',
      page_size: 12,
    }),
    enabled: addOpen && Boolean(selectedCollectionId),
  });

  const totalCount = collectionsQuery.data?.count ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const itemCount = itemsQuery.data?.count ?? selectedCollection?.item_count ?? 0;
  const canSaveOrder = isOrderDirty && Boolean(selectedCollectionId) && !itemsQuery.isFetching;
  const publicProfileUserId = Number(profile?.user_id ?? 0);

  const createCollectionMutation = useMutation({
    ...libraryMutations.createCollection(),
    onSuccess: async (collection) => {
      setNewName('');
      setNewNote('');
      setNewRating(null);
      setNewIsPublic(true);
      setCreateOpen(false);
      await queryClient.invalidateQueries({ queryKey: libraryQueryKeys.collections() });
      setSearchParams((currentParams) => {
        const nextParams = new URLSearchParams(currentParams);
        nextParams.set('collection', String(collection.id));
        nextParams.delete('page');
        return nextParams;
      });
      toast.success(t('collections.created'));
    },
  });
  const updateCollectionMutation = useMutation({
    ...libraryMutations.updateCollection(),
    onSuccess: async () => {
      setEditOpen(false);
      await queryClient.invalidateQueries({ queryKey: libraryQueryKeys.collections() });
      toast.success(t('collections.updated'));
    },
  });
  const deleteCollectionMutation = useMutation({
    ...libraryMutations.deleteCollection(),
    onSuccess: async () => {
      setDeleteOpen(false);
      await queryClient.invalidateQueries({ queryKey: libraryQueryKeys.collections() });
      setSearchParams((currentParams) => {
        const nextParams = new URLSearchParams(currentParams);
        nextParams.delete('collection');
        return nextParams;
      });
      toast.success(t('collections.deleted'));
    },
  });
  const updateItemsMutation = useMutation({
    ...libraryMutations.updateCollectionItems(),
    onSuccess: async () => {
      setIsOrderDirty(false);
      await queryClient.invalidateQueries({ queryKey: libraryQueryKeys.collections() });
      await queryClient.invalidateQueries({ queryKey: libraryQueryKeys.collectionItems(selectedCollectionId || 0) });
      toast.success(t('collections.orderSaved'));
    },
  });
  const addItemMutation = useMutation({
    ...libraryMutations.addCollectionItem(),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: libraryQueryKeys.collections() });
      await queryClient.invalidateQueries({ queryKey: libraryQueryKeys.collectionItems(selectedCollectionId || 0) });
      toast.success(t('collections.addedItem'));
    },
  });
  const deleteItemMutation = useMutation({
    ...libraryMutations.deleteCollectionItem(),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: libraryQueryKeys.collections() });
      await queryClient.invalidateQueries({ queryKey: libraryQueryKeys.collectionItems(selectedCollectionId || 0) });
    },
  });

  useEffect(() => {
    setDraftKeyword(keyword);
  }, [keyword]);

  useEffect(() => {
    if (!selectedCollectionId && collections.length > 0) {
      setSearchParams((currentParams) => {
        const nextParams = new URLSearchParams(currentParams);
        nextParams.set('collection', String(collections[0].id));
        return nextParams;
      });
    }
  }, [collections, selectedCollectionId, setSearchParams]);

  useEffect(() => {
    if (collectionsQuery.data && currentPage > totalPages) {
      setSearchParams((currentParams) => {
        const nextParams = new URLSearchParams(currentParams);
        nextParams.set('page', String(totalPages));
        return nextParams;
      });
    }
  }, [collectionsQuery.data, currentPage, setSearchParams, totalPages]);

  useEffect(() => {
    const nextItems = itemsQuery.data?.results ?? [];
    setItems(nextItems);
    setIsOrderDirty(false);
    setDropPreview(null);
  }, [itemsQuery.data?.results]);

  useEffect(() => {
    if (!selectedCollection) return;
    setEditName(selectedCollection.name);
    setEditNote(selectedCollection.note || '');
    setEditRating(selectedCollection.simple_rating ?? null);
    setEditIsPublic(selectedCollection.is_public);
  }, [selectedCollection]);

  function updateSearchParam(key: string, value: string) {
    setSearchParams((currentParams) => {
      const nextParams = new URLSearchParams(currentParams);
      if (value) nextParams.set(key, value);
      else nextParams.delete(key);
      if (key === 'keyword' || key === 'ordering') {
        nextParams.delete('page');
        nextParams.delete('collection');
      }
      return nextParams;
    });
  }

  function selectCollection(collectionId: number) {
    updateSearchParam('collection', String(collectionId));
  }

  function handleSearchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    updateSearchParam('keyword', draftKeyword.trim());
  }

  function handleCreateCollection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = newName.trim();
    if (!name) return;

    createCollectionMutation.mutate({
      name,
      note: newNote.trim(),
      simple_rating: newRating ?? undefined,
      is_public: newIsPublic,
    });
  }

  function handleUpdateCollection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedCollection) return;
    const name = editName.trim();
    if (!name) return;

    updateCollectionMutation.mutate({
      collectionId: selectedCollection.id,
      body: {
        name,
        note: editNote.trim(),
        simple_rating: editRating ?? undefined,
        is_public: editIsPublic,
      },
    });
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>, targetItemId: number) {
    event.preventDefault();
    handleDragMove(event.clientX);
    if (!draggingItemId || draggingItemId === targetItemId) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const position: DropPosition = event.clientX < rect.left + rect.width / 2 ? 'before' : 'after';
    setDropPreview((current) =>
      current?.itemId === targetItemId && current.position === position ? current : { itemId: targetItemId, position },
    );
  }

  const stopRailAutoScroll = useCallback(() => {
    autoScrollVelocityRef.current = 0;
    lastDragClientXRef.current = null;
    if (autoScrollFrameRef.current !== null) {
      window.cancelAnimationFrame(autoScrollFrameRef.current);
      autoScrollFrameRef.current = null;
    }
  }, []);

  const runRailAutoScroll = useCallback(function runRailAutoScroll() {
    if (!railRef.current || !isDraggingRef.current || autoScrollVelocityRef.current === 0) {
      autoScrollFrameRef.current = null;
      return;
    }

    railRef.current.scrollLeft += autoScrollVelocityRef.current;
    autoScrollFrameRef.current = window.requestAnimationFrame(runRailAutoScroll);
  }, []);

  const updateRailAutoScroll = useCallback(
    (clientX: number) => {
      if (!railRef.current || !isDraggingRef.current) return;
      const rail = railRef.current;
      const rect = rail.getBoundingClientRect();
      const threshold = 120;
      const maxVelocity = 22;
      const leftDistance = clientX - rect.left;
      const rightDistance = rect.right - clientX;
      let velocity = 0;

      if (leftDistance < threshold) {
        velocity = -Math.max(4, Math.round(((threshold - Math.max(0, leftDistance)) / threshold) * maxVelocity));
      } else if (rightDistance < threshold) {
        velocity = Math.max(4, Math.round(((threshold - Math.max(0, rightDistance)) / threshold) * maxVelocity));
      }

      autoScrollVelocityRef.current = velocity;
      if (velocity !== 0 && autoScrollFrameRef.current === null) {
        autoScrollFrameRef.current = window.requestAnimationFrame(runRailAutoScroll);
      }
      if (velocity === 0 && autoScrollFrameRef.current !== null) {
        stopRailAutoScroll();
      }
    },
    [runRailAutoScroll, stopRailAutoScroll],
  );

  const handleDragMove = useCallback(
    (clientX: number) => {
      const nextClientX = clientX > 0 ? clientX : lastDragClientXRef.current;
      if (!nextClientX) return;
      lastDragClientXRef.current = nextClientX;
      updateRailAutoScroll(nextClientX);
      if (railRef.current && autoScrollVelocityRef.current !== 0) {
        railRef.current.scrollLeft += autoScrollVelocityRef.current;
      }
    },
    [updateRailAutoScroll],
  );

  useEffect(() => {
    function handleWindowDragOver(event: globalThis.DragEvent) {
      handleDragMove(event.clientX);
    }

    window.addEventListener('dragover', handleWindowDragOver);
    return () => {
      window.removeEventListener('dragover', handleWindowDragOver);
      stopRailAutoScroll();
    };
  }, [handleDragMove, stopRailAutoScroll]);

  function handleRailDragOver(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    handleDragMove(event.clientX);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>, targetItemId: number) {
    event.preventDefault();
    if (!draggingItemId || draggingItemId === targetItemId) return;

    const fromIndex = items.findIndex((item) => item.id === draggingItemId);
    const toIndex = items.findIndex((item) => item.id === targetItemId);
    if (fromIndex < 0 || toIndex < 0) return;

    setItems(moveItemToDrop(items, fromIndex, toIndex, dropPreview?.position ?? 'before'));
    setDraggingItemId(null);
    isDraggingRef.current = false;
    stopRailAutoScroll();
    setDropPreview(null);
    setIsOrderDirty(true);
  }

  function saveOrder() {
    if (!selectedCollectionId || !canSaveOrder) return;

    updateItemsMutation.mutate({
      collectionId: selectedCollectionId,
      items: items.map((item, index) => ({
        id: item.id,
        order: index + 1,
        relation: item.relation || '',
      })),
    });
  }

  function openQuickSort(item: CollectionItem, index: number) {
    setQuickSortItem(item);
    setQuickSortPosition(String(index + 1));
  }

  function handleQuickSortSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!quickSortItem) return;
    const position = Number(quickSortPosition);
    if (!Number.isInteger(position) || position < 1 || position > items.length) return;
    setItems(moveItemToPosition(items, quickSortItem.id, position));
    setQuickSortItem(null);
    setQuickSortPosition('');
    setDropPreview(null);
    setIsOrderDirty(true);
  }

  function addLibraryItem(userSubjectId: number) {
    if (!selectedCollectionId) return;
    addItemMutation.mutate({
      collectionId: selectedCollectionId,
      body: {
        user_subject_id: userSubjectId,
        order: itemCount + 1,
      },
    });
  }

  function deleteItem(itemId: number) {
    if (!selectedCollectionId) return;
    deleteItemMutation.mutate({ collectionId: selectedCollectionId, itemId });
  }

  function goToPage(page: number) {
    updateSearchParam('page', String(Math.min(Math.max(page, 1), totalPages)));
  }

  return (
    <Page
      title={t('collections.title')}
      eyebrow={t('nav.groupLibrary')}
      actions={
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button type="button">
              <Plus className="size-4" />
              {t('collections.new')}
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t('collections.createTitle')}</DialogTitle>
              <DialogDescription>{t('collections.createDescription')}</DialogDescription>
            </DialogHeader>
            <form className="grid gap-4" onSubmit={handleCreateCollection}>
              <label className="grid gap-2 text-sm font-medium text-neutral-700 dark:text-neutral-300">
                {t('collections.name')}
                <Input
                  value={newName}
                  placeholder={t('collections.namePlaceholder')}
                  onChange={(event) => setNewName(event.target.value)}
                />
              </label>
              <label className="grid gap-2 text-sm font-medium text-neutral-700 dark:text-neutral-300">
                {t('collections.note')}
                <textarea
                  className="min-h-28 rounded-xl border-0 bg-white px-4 py-3 text-sm shadow-sm outline-none ring-1 ring-neutral-200 transition placeholder:text-neutral-400 focus:ring-4 focus:ring-neutral-200 dark:bg-neutral-950 dark:ring-neutral-800 dark:focus:ring-neutral-800"
                  value={newNote}
                  placeholder={t('collections.notePlaceholder')}
                  onChange={(event) => setNewNote(event.target.value)}
                />
              </label>
              <div className="flex items-center justify-between gap-4 rounded-xl border border-neutral-200 px-4 py-3 dark:border-neutral-800">
                <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
                  {t('collections.rating')}
                </span>
                <RatingStars interactive label={t('common.unrated')} value={newRating} onChange={setNewRating} />
              </div>
              <button
                className="flex items-center justify-between gap-4 rounded-xl border border-neutral-200 px-4 py-3 text-left text-sm font-medium text-neutral-700 transition hover:bg-neutral-50 dark:border-neutral-800 dark:text-neutral-300 dark:hover:bg-neutral-900"
                type="button"
                onClick={() => setNewIsPublic((value) => !value)}
              >
                <span>{newIsPublic ? t('collections.publicCollection') : t('collections.privateCollection')}</span>
                {newIsPublic ? <Eye className="size-4" /> : <EyeOff className="size-4" />}
              </button>
              <Button disabled={createCollectionMutation.isPending || !newName.trim()} type="submit">
                {t('collections.createAction')}
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      }
    >
      <div className="grid min-w-0 gap-5 xl:grid-cols-[340px_minmax(0,1fr)]">
        <aside className="grid content-start gap-5">
          <form className="content-toolbar" onSubmit={handleSearchSubmit}>
            <div className="content-toolbar-grid is-collection">
              <div className="content-toolbar-search">
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-neutral-400" />
                <Input
                  className="pl-9"
                  value={draftKeyword}
                  placeholder={t('collections.searchPlaceholder')}
                  onChange={(event) => setDraftKeyword(event.target.value)}
                />
              </div>
              <FilterMenu
                label={t('common.sort')}
                options={orderingOptions}
                value={ordering}
                onChange={(value) => updateSearchParam('ordering', value)}
              />
              <Button type="submit" variant="secondary">
                {t('common.search')}
              </Button>
            </div>
          </form>

          <div className="content-summary-bar">
            <div className="content-summary-count">
              <span className="content-summary-number">{totalCount}</span>
              <span>{t('nav.collections')}</span>
            </div>
            <div className="content-summary-side">
              {collectionsQuery.isFetching ? <span>{t('common.loading')}</span> : null}
              <span className="content-summary-page">
                {t('common.page')} {currentPage} / {totalPages}
              </span>
            </div>
          </div>

          {collectionsQuery.isLoading ? <LoadingState title={t('calendar.loading')} /> : null}
          {collectionsQuery.isError ? (
            <ErrorState title={t('reviews.errorTitle')} description={t('search.errorBody')} />
          ) : null}
          {!collectionsQuery.isLoading && !collectionsQuery.isError && collections.length === 0 ? (
            <EmptyState title={t('collections.emptyTitle')} description={t('collections.emptyBody')} />
          ) : null}

          <div className="grid gap-2">
            {collections.map((collection) => {
              const isSelected = collection.id === selectedCollectionId;
              return (
                <button
                  className={cn('collection-pack-card group text-left transition', isSelected ? 'is-selected' : '')}
                  key={collection.id}
                  type="button"
                  onClick={() => selectCollection(collection.id)}
                >
                  <CollectionPackCover collectionId={collection.id} />
                  <div className="flex items-start justify-between gap-3">
                    <h2 className="min-w-0 truncate text-sm font-semibold">{collection.name}</h2>
                    <span
                      className={cn(
                        'rounded-full px-2 py-0.5 text-xs font-semibold',
                        isSelected
                          ? 'bg-[var(--color-surface-elevated)] text-[var(--color-text-muted)]'
                          : 'bg-neutral-100 text-neutral-500 dark:bg-neutral-900 dark:text-neutral-400',
                      )}
                    >
                      {collection.item_count ?? 0}
                    </span>
                  </div>
                  {collection.note ? (
                    <p className="mt-2 line-clamp-2 text-xs leading-5 text-neutral-500 dark:text-neutral-400">
                      {collection.note}
                    </p>
                  ) : null}
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <RatingStars label={t('common.unrated')} value={collection.simple_rating} />
                    {collection.is_public ? (
                      <Eye className="size-4 opacity-60" />
                    ) : (
                      <EyeOff className="size-4 opacity-60" />
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={goToPage} />
        </aside>

        <section className="min-w-0">
          {!selectedCollection ? (
            <div className="collection-empty-state">
              <div className="max-w-sm">
                <div className="collection-empty-icon">
                  <Layers3 className="size-5" />
                </div>
                <h2 className="mt-4 text-lg font-semibold tracking-tight text-neutral-950 dark:text-white">
                  {t('collections.chooseTitle')}
                </h2>
              </div>
            </div>
          ) : (
            <div className="grid min-w-0 gap-5">
              <div className="content-list-panel min-w-0 p-5">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={selectedCollection.is_public ? 'accent' : 'secondary'}>
                        {selectedCollection.is_public ? t('common.public') : t('common.private')}
                      </Badge>
                      <Badge>
                        {itemCount} {t('common.items')}
                      </Badge>
                    </div>
                    <h2 className="mt-3 text-2xl font-semibold tracking-tight text-neutral-950 dark:text-white">
                      {collectionTitle(selectedCollection, t('collections.chooseTitle'))}
                    </h2>
                    {selectedCollection.note ? (
                      <p className="mt-2 max-w-3xl text-sm leading-6 text-neutral-500 dark:text-neutral-400">
                        {selectedCollection.note}
                      </p>
                    ) : (
                      <p className="mt-2 text-sm text-neutral-400 dark:text-neutral-500">{t('common.noNote')}</p>
                    )}
                    <div className="mt-4 flex items-center gap-3">
                      <RatingStars label={t('common.unrated')} value={selectedCollection.simple_rating} />
                      <span className="text-sm text-neutral-500 dark:text-neutral-400">
                        {starLabel(selectedCollection.simple_rating, t('common.unrated'))}
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {selectedCollection.is_public && Number.isFinite(publicProfileUserId) && publicProfileUserId > 0 ? (
                      <Button asChild type="button" variant="secondary">
                        <Link
                          state={routeBackState(location, t('collections.title'))}
                          to={routes.userCollection(publicProfileUserId, selectedCollection.id)}
                        >
                          <ExternalLink className="size-4" />
                          {t('collections.viewPublic')}
                        </Link>
                      </Button>
                    ) : null}

                    <Dialog open={addOpen} onOpenChange={setAddOpen}>
                      <DialogTrigger asChild>
                        <Button type="button">
                          <Plus className="size-4" />
                          {t('collections.addFromLibrary')}
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="max-h-[calc(100dvh-2rem)] max-w-3xl overflow-hidden p-0">
                        <DialogHeader className="border-b border-neutral-200 px-5 py-4 pr-12 dark:border-neutral-800">
                          <DialogTitle>{t('collections.addFromLibraryTitle')}</DialogTitle>
                          <DialogDescription>{t('collections.addFromLibraryDescription')}</DialogDescription>
                        </DialogHeader>
                        <div className="grid max-h-[calc(100dvh-9rem)] gap-4 overflow-y-auto p-5">
                          <div className="relative">
                            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-neutral-400" />
                            <Input
                              className="pl-9"
                              placeholder={t('collections.librarySearchPlaceholder')}
                              value={addKeyword}
                              onChange={(event) => setAddKeyword(event.target.value)}
                            />
                          </div>
                          {librarySearchQuery.isLoading ? <LoadingState title={t('library.loading')} /> : null}
                          {librarySearchQuery.isError ? (
                            <ErrorState title={t('library.errorTitle')} description={t('search.errorBody')} />
                          ) : null}
                          <div className="collection-library-results">
                            {(librarySearchQuery.data?.results ?? []).map((item) => (
                              <article className="collection-library-item" key={item.id}>
                                <img
                                  alt=""
                                  src={userSubjectImage(item) || '/assets/placeholders/subject-cover.png'}
                                  loading="lazy"
                                />
                                <div className="min-w-0">
                                  <h3>{userSubjectTitle(item, t('common.untitledSubject'))}</h3>
                                  <p>{userSubjectSubtitle(item, t('common.noMetadata'))}</p>
                                </div>
                                <Button
                                  disabled={addItemMutation.isPending}
                                  size="sm"
                                  type="button"
                                  onClick={() => addLibraryItem(item.id)}
                                >
                                  <Plus className="size-4" />
                                  {t('common.add')}
                                </Button>
                              </article>
                            ))}
                          </div>
                          {!librarySearchQuery.isFetching && (librarySearchQuery.data?.results.length ?? 0) === 0 ? (
                            <EmptyState title={t('library.emptyTitle')} description={t('library.emptyBody')} />
                          ) : null}
                        </div>
                      </DialogContent>
                    </Dialog>

                    <Dialog open={editOpen} onOpenChange={setEditOpen}>
                      <DialogTrigger asChild>
                        <Button type="button" variant="secondary">
                          <Pencil className="size-4" />
                          {t('common.edit')}
                        </Button>
                      </DialogTrigger>
                      <DialogContent>
                        <DialogHeader>
                          <DialogTitle>{t('collections.editTitle')}</DialogTitle>
                          <DialogDescription>{t('collections.editDescription')}</DialogDescription>
                        </DialogHeader>
                        <form className="grid gap-4" onSubmit={handleUpdateCollection}>
                          <label className="grid gap-2 text-sm font-medium text-neutral-700 dark:text-neutral-300">
                            {t('collections.name')}
                            <Input value={editName} onChange={(event) => setEditName(event.target.value)} />
                          </label>
                          <label className="grid gap-2 text-sm font-medium text-neutral-700 dark:text-neutral-300">
                            {t('collections.note')}
                            <textarea
                              className="min-h-32 rounded-xl border-0 bg-white px-4 py-3 text-sm shadow-sm outline-none ring-1 ring-neutral-200 transition placeholder:text-neutral-400 focus:ring-4 focus:ring-neutral-200 dark:bg-neutral-950 dark:ring-neutral-800 dark:focus:ring-neutral-800"
                              value={editNote}
                              onChange={(event) => setEditNote(event.target.value)}
                            />
                          </label>
                          <div className="flex items-center justify-between gap-4 rounded-xl border border-neutral-200 px-4 py-3 dark:border-neutral-800">
                            <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
                              {t('collections.rating')}
                            </span>
                            <RatingStars
                              interactive
                              label={t('common.unrated')}
                              value={editRating}
                              onChange={setEditRating}
                            />
                          </div>
                          <button
                            className="flex items-center justify-between gap-4 rounded-xl border border-neutral-200 px-4 py-3 text-left text-sm font-medium text-neutral-700 transition hover:bg-neutral-50 dark:border-neutral-800 dark:text-neutral-300 dark:hover:bg-neutral-900"
                            type="button"
                            onClick={() => setEditIsPublic((value) => !value)}
                          >
                            <span>
                              {editIsPublic ? t('collections.publicCollection') : t('collections.privateCollection')}
                            </span>
                            {editIsPublic ? <Eye className="size-4" /> : <EyeOff className="size-4" />}
                          </button>
                          <Button disabled={updateCollectionMutation.isPending || !editName.trim()} type="submit">
                            {t('common.save')}
                          </Button>
                        </form>
                      </DialogContent>
                    </Dialog>

                    <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
                      <DialogTrigger asChild>
                        <Button type="button" variant="ghost">
                          <Trash2 className="size-4" />
                          {t('common.delete')}
                        </Button>
                      </DialogTrigger>
                      <DialogContent>
                        <DialogHeader>
                          <DialogTitle>{t('collections.deleteTitle')}</DialogTitle>
                          <DialogDescription>{t('collections.deleteDescription')}</DialogDescription>
                        </DialogHeader>
                        <div className="rounded-xl bg-neutral-100 p-4 text-sm font-medium text-neutral-700 dark:bg-neutral-900 dark:text-neutral-300">
                          {selectedCollection.name}
                        </div>
                        <div className="flex justify-end gap-2">
                          <Button type="button" variant="secondary" onClick={() => setDeleteOpen(false)}>
                            {t('common.cancel')}
                          </Button>
                          <Button
                            disabled={deleteCollectionMutation.isPending}
                            type="button"
                            onClick={() => deleteCollectionMutation.mutate(selectedCollection.id)}
                          >
                            {t('common.delete')}
                          </Button>
                        </div>
                      </DialogContent>
                    </Dialog>
                  </div>
                </div>
              </div>

              <div className="content-list-panel min-w-0">
                <div className="content-section-header">
                  <div>
                    <h3 className="text-sm font-semibold text-neutral-950 dark:text-white">
                      {t('collections.itemsTitle')}
                    </h3>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {isOrderDirty ? (
                      <Button
                        disabled={!canSaveOrder || updateItemsMutation.isPending}
                        size="sm"
                        type="button"
                        onClick={saveOrder}
                      >
                        {t('collections.saveOrder')}
                      </Button>
                    ) : null}
                  </div>
                </div>

                {itemsQuery.isLoading ? <LoadingState title={t('collections.loadingItems')} /> : null}
                {itemsQuery.isError ? (
                  <ErrorState title={t('collections.itemsErrorTitle')} description={t('search.errorBody')} />
                ) : null}
                {!itemsQuery.isLoading && !itemsQuery.isError && items.length === 0 ? (
                  <EmptyState title={t('collections.emptyItemsTitle')} description={t('collections.emptyItemsBody')} />
                ) : null}

                <div
                  className={cn('collection-rail', draggingItemId ? 'is-sorting' : '')}
                  ref={railRef}
                  aria-label={t('collections.itemsTitle')}
                  onDragOver={handleRailDragOver}
                >
                  {items.map((item, index) => (
                    <div
                      className={cn(
                        'collection-rail-card group',
                        draggingItemId === item.id ? 'is-dragging' : '',
                        dropPreview?.itemId === item.id && dropPreview.position === 'before' ? 'is-drop-before' : '',
                        dropPreview?.itemId === item.id && dropPreview.position === 'after' ? 'is-drop-after' : '',
                      )}
                      draggable
                      key={item.id}
                      onDragEnd={() => {
                        setDraggingItemId(null);
                        isDraggingRef.current = false;
                        stopRailAutoScroll();
                        setDropPreview(null);
                      }}
                      onDragOver={(event) => handleDragOver(event, item.id)}
                      onDrag={(event) => handleDragMove(event.clientX)}
                      onDragStart={(event) => {
                        event.dataTransfer.effectAllowed = 'move';
                        event.dataTransfer.setData('text/plain', String(item.id));
                        setDraggingItemId(item.id);
                        isDraggingRef.current = true;
                      }}
                      onDrop={(event) => handleDrop(event, item.id)}
                    >
                      <div className="collection-rail-card-top">
                        <span>{index + 1}</span>
                        <GripVertical className="size-4 cursor-grab" aria-label={t('collections.dragHandle')} />
                      </div>
                      <Link className="collection-rail-poster" to={routes.subject(item.subject.id)}>
                        {subjectImage(item) ? <img src={subjectImage(item) ?? ''} alt="" loading="lazy" /> : <span />}
                      </Link>
                      <div className="collection-rail-body">
                        <Link className="collection-rail-title" to={routes.subject(item.subject.id)}>
                          {subjectTitle(item, t('common.untitledSubject'))}
                        </Link>
                        <p>{subjectSubtitle(item, t('common.noMetadata'))}</p>
                        <div className="collection-rail-badges">
                          {item.relation ? <Badge variant="accent">{item.relation}</Badge> : null}
                          {item.user_subject.rating ? <Badge>{item.user_subject.rating}/10</Badge> : null}
                        </div>
                        {item.user_subject.simple_rating ? (
                          <RatingStars label={t('common.unrated')} value={item.user_subject.simple_rating} />
                        ) : null}
                        {item.user_subject.comment ? (
                          <p className="collection-rail-comment">{item.user_subject.comment}</p>
                        ) : null}
                      </div>
                      <div className="collection-rail-actions">
                        <Button
                          aria-label={t('collections.quickSort')}
                          size="icon"
                          type="button"
                          variant="ghost"
                          onClick={() => openQuickSort(item, index)}
                        >
                          <ListOrdered className="size-4" />
                        </Button>
                        <Button
                          aria-label={t('collections.removeItem')}
                          disabled={deleteItemMutation.isPending}
                          size="icon"
                          type="button"
                          variant="ghost"
                          onClick={() => deleteItem(item.id)}
                        >
                          <Trash2 className="size-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
                <Dialog
                  open={Boolean(quickSortItem)}
                  onOpenChange={(open) => {
                    if (!open) {
                      setQuickSortItem(null);
                      setQuickSortPosition('');
                    }
                  }}
                >
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>{t('collections.quickSortTitle')}</DialogTitle>
                      <DialogDescription>{t('collections.quickSortDescription')}</DialogDescription>
                    </DialogHeader>
                    <form className="grid gap-4" onSubmit={handleQuickSortSubmit}>
                      <div className="rounded-xl bg-neutral-100 p-4 text-sm font-semibold text-neutral-700 dark:bg-neutral-900 dark:text-neutral-300">
                        {quickSortItem ? subjectTitle(quickSortItem, t('common.untitledSubject')) : null}
                      </div>
                      <label className="grid gap-2 text-sm font-medium text-neutral-700 dark:text-neutral-300">
                        {t('collections.position')}
                        <Input
                          inputMode="numeric"
                          max={items.length}
                          min={1}
                          type="number"
                          value={quickSortPosition}
                          onChange={(event) => setQuickSortPosition(event.target.value)}
                        />
                      </label>
                      <Button type="submit" disabled={!quickSortItem || !quickSortPosition}>
                        {t('collections.moveItem')}
                      </Button>
                    </form>
                  </DialogContent>
                </Dialog>
              </div>
            </div>
          )}
        </section>
      </div>
    </Page>
  );
}
