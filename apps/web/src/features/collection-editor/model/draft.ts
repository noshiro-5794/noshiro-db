export type CollectionDraft = {
  name: string;
  note: string;
  rating: number | null;
  isPublic: boolean;
};

export function emptyCollectionDraft(): CollectionDraft {
  return { name: '', note: '', rating: null, isPublic: true };
}

export function collectionDraftOf(collection: Collection): CollectionDraft {
  return {
    name: collection.name,
    note: collection.note || '',
    rating: collection.simple_rating ?? null,
    isPublic: collection.is_public,
  };
}
import type { Collection } from '@/shared/api';
