import { type DragEvent, type SyntheticEvent, useEffect, useId, useState } from 'react';
import { GripVertical, ListOrdered, Trash2 } from 'lucide-react';
import { Link } from '@tanstack/react-router';
import { useI18n } from '@/shared/i18n';
import type { CollectionItem } from '@/shared/api';
import { cn } from '@/shared/lib/cn';
import { routes } from '@/shared/routing/paths';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/shared/ui/Dialog';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Field, FieldLabel } from '@/shared/ui/Field';
import { Input } from '@/shared/ui/Input';
import { collectionItemImage, collectionItemSubtitle, collectionItemTitle } from '../model/presentation';
import { moveItemToDrop, moveItemToPosition, type DropPosition, type DropPreview } from '../model/reorder';
import { useHorizontalDragScroll } from '../model/use-horizontal-drag-scroll';
import { CollectionRatingStars } from './CollectionRatingStars';

type CollectionItemRailProps = {
  itemCount: number;
  loadedItems: CollectionItem[];
  hasNextPage: boolean;
  isDeleting: boolean;
  isError: boolean;
  isFetching: boolean;
  isFetchingNextPage: boolean;
  isLoading: boolean;
  isSaving: boolean;
  onDelete: (itemId: number) => void;
  onLoadMore: () => void;
  onSave: (items: Array<{ id: number; order: number; relation: string }>) => void;
};

export function CollectionItemRail({
  itemCount,
  loadedItems,
  hasNextPage,
  isDeleting,
  isError,
  isFetching,
  isFetchingNextPage,
  isLoading,
  isSaving,
  onDelete,
  onLoadMore,
  onSave,
}: CollectionItemRailProps) {
  const { t } = useI18n();
  const positionId = useId();
  const [items, setItems] = useState<CollectionItem[]>(loadedItems);
  const [draggingItemId, setDraggingItemId] = useState<number | null>(null);
  const [dropPreview, setDropPreview] = useState<DropPreview>(null);
  const [quickSortItem, setQuickSortItem] = useState<CollectionItem | null>(null);
  const [quickSortPosition, setQuickSortPosition] = useState('');
  const [isOrderDirty, setIsOrderDirty] = useState(false);
  const { move: moveDrag, railRef, start: startDrag, stop: stopDrag } = useHorizontalDragScroll();
  const allItemsLoaded = items.length >= itemCount && !hasNextPage;
  const canSave = isOrderDirty && allItemsLoaded && !isFetching && !isSaving;

  useEffect(() => {
    setItems(loadedItems);
    setIsOrderDirty(false);
    setDropPreview(null);
  }, [loadedItems]);

  function handleDragOver(event: DragEvent<HTMLDivElement>, targetItemId: number) {
    event.preventDefault();
    moveDrag(event.clientX);
    if (!draggingItemId || draggingItemId === targetItemId) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const position: DropPosition = event.clientX < rect.left + rect.width / 2 ? 'before' : 'after';
    setDropPreview((current) =>
      current?.itemId === targetItemId && current.position === position ? current : { itemId: targetItemId, position },
    );
  }

  function finishDrag() {
    setDraggingItemId(null);
    setDropPreview(null);
    stopDrag();
  }

  function handleDrop(event: DragEvent<HTMLDivElement>, targetItemId: number) {
    event.preventDefault();
    if (!draggingItemId || draggingItemId === targetItemId) return;
    const fromIndex = items.findIndex((item) => item.id === draggingItemId);
    const targetIndex = items.findIndex((item) => item.id === targetItemId);
    if (fromIndex < 0 || targetIndex < 0) return;

    setItems(moveItemToDrop(items, fromIndex, targetIndex, dropPreview?.position ?? 'before'));
    setIsOrderDirty(true);
    finishDrag();
  }

  function openQuickSort(item: CollectionItem, index: number) {
    setQuickSortItem(item);
    setQuickSortPosition(String(index + 1));
  }

  function submitQuickSort(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (!quickSortItem) return;
    const position = Number(quickSortPosition);
    if (!Number.isSafeInteger(position) || position < 1 || position > items.length) return;
    setItems(moveItemToPosition(items, quickSortItem.id, position));
    setQuickSortItem(null);
    setQuickSortPosition('');
    setDropPreview(null);
    setIsOrderDirty(true);
  }

  function saveOrder() {
    if (!canSave) return;
    onSave(
      items.map((item, index) => ({
        id: item.id,
        order: index + 1,
        relation: item.relation || '',
      })),
    );
  }

  return (
    <div className="collection-editor-surface min-w-0">
      <div className="collection-editor-section-header">
        <h3 className="text-sm font-semibold text-[var(--ui-text)]">{t('collections.itemsTitle')}</h3>
        {isOrderDirty ? (
          <Button disabled={!canSave} size="sm" type="button" onClick={saveOrder}>
            {t('collections.saveOrder')}
          </Button>
        ) : null}
      </div>

      {isLoading ? <LoadingState title={t('collections.loadingItems')} /> : null}
      {isError ? <ErrorState title={t('collections.itemsErrorTitle')} description={t('search.errorBody')} /> : null}
      {!isLoading && !isError && items.length === 0 ? (
        <EmptyState title={t('collections.emptyItemsTitle')} description={t('collections.emptyItemsBody')} />
      ) : null}
      {hasNextPage ? (
        <div className="px-4 pb-3">
          <Button
            disabled={isFetchingNextPage || isOrderDirty}
            size="sm"
            type="button"
            variant="secondary"
            onClick={onLoadMore}
          >
            {isFetchingNextPage
              ? t('common.loading')
              : `${t('collections.loadMoreItems')} (${items.length}/${itemCount})`}
          </Button>
        </div>
      ) : null}

      <div
        className={cn('collection-rail', draggingItemId ? 'is-sorting' : '')}
        ref={railRef}
        aria-label={t('collections.itemsTitle')}
        onDragOver={(event) => {
          event.preventDefault();
          moveDrag(event.clientX);
        }}
      >
        {items.map((item, index) => (
          <div
            className={cn(
              'collection-rail-card group',
              draggingItemId === item.id ? 'is-dragging' : '',
              dropPreview?.itemId === item.id && dropPreview.position === 'before' ? 'is-drop-before' : '',
              dropPreview?.itemId === item.id && dropPreview.position === 'after' ? 'is-drop-after' : '',
            )}
            draggable={allItemsLoaded}
            key={item.id}
            onDrag={(event) => {
              moveDrag(event.clientX);
            }}
            onDragEnd={finishDrag}
            onDragOver={(event) => {
              handleDragOver(event, item.id);
            }}
            onDragStart={(event) => {
              event.dataTransfer.effectAllowed = 'move';
              event.dataTransfer.setData('text/plain', String(item.id));
              setDraggingItemId(item.id);
              startDrag();
            }}
            onDrop={(event) => {
              handleDrop(event, item.id);
            }}
          >
            <div className="collection-rail-card-top">
              <span>{index + 1}</span>
              <GripVertical className="size-4 cursor-grab" aria-label={t('collections.dragHandle')} />
            </div>
            <Link className="collection-rail-poster" to={routes.subject(item.subject.id)}>
              {collectionItemImage(item) ? (
                <img
                  alt=""
                  decoding="async"
                  loading="lazy"
                  referrerPolicy="no-referrer"
                  src={collectionItemImage(item) ?? ''}
                />
              ) : (
                <span />
              )}
            </Link>
            <div className="collection-rail-body">
              <Link className="collection-rail-title" to={routes.subject(item.subject.id)}>
                {collectionItemTitle(item, t('common.untitledSubject'))}
              </Link>
              <p>{collectionItemSubtitle(item, t('common.noMetadata'))}</p>
              <div className="collection-rail-badges">
                {item.relation ? <Badge variant="accent">{item.relation}</Badge> : null}
                {item.user_subject.rating ? <Badge>{item.user_subject.rating}/10</Badge> : null}
              </div>
              {item.user_subject.simple_rating ? (
                <CollectionRatingStars label={t('common.unrated')} value={item.user_subject.simple_rating} />
              ) : null}
              {item.user_subject.comment ? (
                <p className="collection-rail-comment">{item.user_subject.comment}</p>
              ) : null}
            </div>
            <div className="collection-rail-actions">
              <Button
                aria-label={t('collections.quickSort')}
                disabled={!allItemsLoaded}
                size="icon"
                tooltip={t('collections.quickSort')}
                type="button"
                variant="ghost"
                onClick={() => {
                  openQuickSort(item, index);
                }}
              >
                <ListOrdered className="size-4" />
              </Button>
              <Button
                aria-label={t('collections.removeItem')}
                disabled={isDeleting}
                size="icon"
                tooltip={t('collections.removeItem')}
                type="button"
                variant="ghost"
                onClick={() => {
                  onDelete(item.id);
                }}
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
          <form className="grid gap-4" onSubmit={submitQuickSort}>
            <div className="rounded-sm bg-muted px-3 py-2.5 text-sm font-medium text-foreground">
              {quickSortItem ? collectionItemTitle(quickSortItem, t('common.untitledSubject')) : null}
            </div>
            <Field>
              <FieldLabel htmlFor={positionId}>{t('collections.position')}</FieldLabel>
              <Input
                id={positionId}
                inputMode="numeric"
                max={items.length}
                min={1}
                type="number"
                value={quickSortPosition}
                onChange={(event) => {
                  setQuickSortPosition(event.target.value);
                }}
              />
            </Field>
            <DialogFooter>
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setQuickSortItem(null);
                  setQuickSortPosition('');
                }}
              >
                {t('common.cancel')}
              </Button>
              <Button type="submit" disabled={!quickSortItem || !quickSortPosition}>
                {t('collections.moveItem')}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
