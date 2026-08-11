import type { Collection, CollectionItem, UserSubject } from '@/shared/api';

export function collectionRatingLabel(value: number | null | undefined, fallback: string) {
  return value ? `${value}/5` : fallback;
}

export function collectionTitle(collection: Collection | null, fallback: string) {
  return collection?.name || fallback;
}

export function collectionItemTitle(item: CollectionItem, fallback: string) {
  return item.subject.display_title || item.subject.title || item.subject.title_cn || fallback;
}

export function collectionItemSubtitle(item: CollectionItem, fallback: string) {
  const parts = [
    item.subject.subject_type,
    item.subject.date,
    item.subject.platform,
    item.user_subject.status ? item.user_subject.status.replaceAll('_', ' ') : null,
  ].filter(Boolean);
  return parts.join(' / ') || fallback;
}

export function collectionItemImage(item: CollectionItem) {
  return item.subject.images?.thumbnail || item.subject.image_thumbnail || item.subject.image || null;
}

export function userSubjectTitle(item: UserSubject, fallback: string) {
  return item.subject.display_title || item.subject.title || item.subject.title_cn || fallback;
}

export function userSubjectSubtitle(item: UserSubject, fallback: string) {
  const parts = [
    item.subject.subject_type,
    item.subject.date,
    item.subject.platform,
    item.status.replaceAll('_', ' '),
  ].filter(Boolean);
  return parts.join(' / ') || fallback;
}

export function userSubjectImage(item: UserSubject) {
  return item.subject.images?.thumbnail || item.subject.image_thumbnail || item.subject.image || null;
}
