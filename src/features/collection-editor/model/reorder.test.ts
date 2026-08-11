import { describe, expect, it } from 'vitest';
import { moveItemToDrop, moveItemToPosition, parseCollectionOrdering } from './reorder';

const items = [{ id: 1 }, { id: 2 }, { id: 3 }, { id: 4 }];

describe('collection ordering', () => {
  it('accepts known URL ordering values and rejects arbitrary input', () => {
    expect(parseCollectionOrdering('name')).toBe('name');
    expect(parseCollectionOrdering('-item_count')).toBe('-item_count');
    expect(parseCollectionOrdering('drop table')).toBe('-id');
    expect(parseCollectionOrdering(null)).toBe('-id');
  });

  it('moves items before or after a drop target without mutating the source', () => {
    expect(moveItemToDrop(items, 0, 2, 'after').map(({ id }) => id)).toEqual([2, 3, 1, 4]);
    expect(moveItemToDrop(items, 3, 1, 'before').map(({ id }) => id)).toEqual([1, 4, 2, 3]);
    expect(items.map(({ id }) => id)).toEqual([1, 2, 3, 4]);
  });

  it('moves an item to a one-based explicit position and clamps the result', () => {
    expect(moveItemToPosition(items, 4, 2).map(({ id }) => id)).toEqual([1, 4, 2, 3]);
    expect(moveItemToPosition(items, 1, 99).map(({ id }) => id)).toEqual([2, 3, 4, 1]);
    expect(moveItemToPosition(items, 999, 1)).toBe(items);
  });
});
