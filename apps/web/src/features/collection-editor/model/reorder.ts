const collectionOrderings = [
  'id',
  '-id',
  'name',
  '-name',
  'simple_rating',
  '-simple_rating',
  'item_count',
  '-item_count',
] as const;

export type CollectionOrdering = (typeof collectionOrderings)[number];
export type DropPosition = 'before' | 'after';
export type DropPreview = { itemId: number; position: DropPosition } | null;

export function parseCollectionOrdering(value: string | null): CollectionOrdering {
  return collectionOrderings.includes(value as CollectionOrdering) ? (value as CollectionOrdering) : '-id';
}

export function moveItemToDrop<T>(items: T[], fromIndex: number, targetIndex: number, position: DropPosition) {
  const movedItem = items[fromIndex];
  if (movedItem === undefined || targetIndex < 0 || targetIndex >= items.length || fromIndex === targetIndex) {
    return items;
  }

  const nextItems = [...items];
  nextItems.splice(fromIndex, 1);
  let insertIndex = position === 'after' ? targetIndex + 1 : targetIndex;
  if (fromIndex < insertIndex) insertIndex -= 1;
  nextItems.splice(Math.max(0, Math.min(insertIndex, nextItems.length)), 0, movedItem);
  return nextItems;
}

export function moveItemToPosition<T extends { id: number }>(items: T[], itemId: number, position: number) {
  const fromIndex = items.findIndex((item) => item.id === itemId);
  const movedItem = items[fromIndex];
  if (fromIndex < 0 || movedItem === undefined || !Number.isSafeInteger(position)) return items;

  const nextItems = [...items];
  nextItems.splice(fromIndex, 1);
  const insertIndex = Math.max(0, Math.min(position - 1, nextItems.length));
  nextItems.splice(insertIndex, 0, movedItem);
  return nextItems;
}
