import { describe, expect, it } from 'vitest';
import type { Collection } from '@/shared/api';
import { collectionDraftOf, emptyCollectionDraft } from './draft';

describe('collection drafts', () => {
  it('creates a fresh empty draft', () => {
    const first = emptyCollectionDraft();
    const second = emptyCollectionDraft();
    expect(first).toEqual({ name: '', note: '', rating: null, isPublic: true });
    expect(first).not.toBe(second);
  });

  it('copies editable fields from a collection', () => {
    expect(
      collectionDraftOf({
        id: 7,
        name: 'Favorites',
        note: 'A note',
        simple_rating: 4,
        is_public: false,
      } satisfies Collection),
    ).toEqual({ name: 'Favorites', note: 'A note', rating: 4, isPublic: false });
  });
});
