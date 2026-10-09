import type {
  Collection,
  CollectionItem,
  EpisodeProgress,
  LibraryEntry,
  ProgressSummary,
  RatingDetail,
  Review,
  Tag,
  UserSubject,
  UserSubjectContext,
} from '../contracts/library';
import type { PublicUserSummary } from '../contracts/user';
import { subjectSummaryFromEntity } from './subject';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isInteger(value: unknown, minimum = Number.MIN_SAFE_INTEGER): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= minimum;
}

function isNullableString(value: unknown) {
  return value === null || typeof value === 'string';
}

function isPublicUserSummary(value: unknown): value is PublicUserSummary {
  return (
    isRecord(value) &&
    isInteger(value['id'], 1) &&
    typeof value['nickname'] === 'string' &&
    isNullableString(value['avatar'])
  );
}

function isTag(value: unknown): value is Tag {
  return isRecord(value) && isInteger(value['id'], 1) && typeof value['name'] === 'string';
}

function isRatingDetail(value: unknown): value is RatingDetail {
  return isRecord(value) && typeof value['key'] === 'string' && typeof value['value'] === 'string';
}

function isLibraryEntry(value: unknown): value is LibraryEntry & Record<string, unknown> {
  if (
    !isRecord(value) ||
    !isInteger(value['id'], 1) ||
    typeof value['status'] !== 'string' ||
    (value['simple_rating'] !== null && !isInteger(value['simple_rating'], 1)) ||
    !isNullableString(value['rating']) ||
    typeof value['comment'] !== 'string' ||
    !isNullableString(value['watch_start_date']) ||
    !isNullableString(value['watch_end_date']) ||
    typeof value['is_public'] !== 'boolean' ||
    !Array.isArray(value['releases'])
  ) {
    return false;
  }

  const entity = value['entity'];
  return isRecord(entity) && typeof entity['id'] === 'string' && Boolean(entity['id']);
}

function isReviewEntity(value: unknown): boolean {
  return isRecord(value) && typeof value['id'] === 'string' && Boolean(value['id']);
}

function isReview(value: unknown): value is Review & Record<string, unknown> {
  if (
    !isRecord(value) ||
    !isInteger(value['id'], 1) ||
    typeof value['title'] !== 'string' ||
    typeof value['content'] !== 'string' ||
    typeof value['is_public'] !== 'boolean' ||
    typeof value['is_spoiler'] !== 'boolean' ||
    !isInteger(value['reaction_count'], 0) ||
    typeof value['created_at'] !== 'string' ||
    typeof value['updated_at'] !== 'string' ||
    !isReviewEntity(value['entity']) ||
    !isInteger(value['library_entry_id'], 0) ||
    !isPublicUserSummary(value['user']) ||
    !isRecord(value['viewer_state']) ||
    typeof value['viewer_state']['has_liked'] !== 'boolean' ||
    typeof value['viewer_state']['has_bookmarked'] !== 'boolean'
  ) {
    return false;
  }

  return true;
}

function isProgressEpisode(value: unknown) {
  return (
    isRecord(value) &&
    typeof value['id'] === 'string' &&
    typeof value['title'] === 'string' &&
    typeof value['type'] === 'string' &&
    typeof value['is_finished'] === 'boolean'
  );
}

function isProgressSummary(value: unknown): value is EpisodeProgress & Record<string, unknown> {
  return (
    isRecord(value) &&
    isInteger(value['library_entry_id'], 0) &&
    typeof value['entity_id'] === 'string' &&
    isInteger(value['total_episodes'], 0) &&
    isInteger(value['finished_count'], 0) &&
    Array.isArray(value['finished_episode_ids']) &&
    value['finished_episode_ids'].every((id) => typeof id === 'string') &&
    Array.isArray(value['episodes']) &&
    value['episodes'].every(isProgressEpisode)
  );
}

function isCollection(value: unknown): value is Collection {
  return (
    isRecord(value) &&
    isInteger(value['id'], 1) &&
    typeof value['name'] === 'string' &&
    (value['simple_rating'] === null || isInteger(value['simple_rating'], 1)) &&
    typeof value['note'] === 'string' &&
    typeof value['is_public'] === 'boolean'
  );
}

function isCollectionItem(value: unknown): value is CollectionItem & Record<string, unknown> {
  return (
    isRecord(value) &&
    isInteger(value['id'], 1) &&
    isInteger(value['library_entry_id'], 0) &&
    isReviewEntity(value['entity']) &&
    isInteger(value['order'], 0) &&
    typeof value['relation'] === 'string'
  );
}

function decodeValue<T>(value: unknown, predicate: (candidate: unknown) => candidate is T, message: string): T {
  if (!predicate(value)) throw new TypeError(message);
  return value;
}

function decodeArray<T>(value: unknown, decodeItem: (item: unknown) => T, message: string): T[] {
  if (!Array.isArray(value)) throw new TypeError(message);
  return value.map(decodeItem);
}

export const decodeTag = (value: unknown) => decodeValue(value, isTag, 'Invalid tag response');
export const decodeTags = (value: unknown) => decodeArray(value, decodeTag, 'Invalid tag list response');
const decodeRatingDetail = (value: unknown) => decodeValue(value, isRatingDetail, 'Invalid rating detail response');
export const decodeRatingDetails = (value: unknown) =>
  decodeArray(value, decodeRatingDetail, 'Invalid rating detail list response');

export const decodeUserSubject = (value: unknown) => {
  const entry = decodeValue(value, isLibraryEntry, 'Invalid library entry response');
  const subject = subjectSummaryFromEntity(entry.entity);
  return {
    ...entry,
    subject,
  } as unknown as UserSubject;
};

export const decodeReview = (value: unknown) => {
  const review = decodeValue(value, isReview, 'Invalid review response');
  return {
    ...review,
    subject: subjectSummaryFromEntity(review.entity),
  } as unknown as Review;
};

export const decodeReviews = (value: unknown) => decodeArray(value, decodeReview, 'Invalid review list response');

export const decodeProgressSummary = (value: unknown) => {
  const progress = decodeValue(value, isProgressSummary, 'Invalid progress response');
  return {
    subject_id: progress.entity_id,
    user_subject_id: progress.library_entry_id,
    entity_id: progress.entity_id,
    library_entry_id: progress.library_entry_id,
    total_episodes: progress.total_episodes,
    finished_count: progress.finished_count,
    finished_episode_ids: progress.finished_episode_ids,
    episodes: progress.episodes.map((episode) => ({
      id: episode.id,
      title: episode.title,
      title_cn: episode.title_cn,
      type: episode.type,
      number: episode.number,
      sort: episode.sort,
      disc: 0,
      duration: '',
      raw_duration: '',
      air_date: episode.air_date,
      comment_count: 0,
      description: '',
      provenance: null,
      ep_num: episode.number === '' ? null : Number(episode.number),
      date: episode.air_date,
      is_finished: episode.is_finished,
    })),
  } satisfies ProgressSummary;
};

export const decodeCollection = (value: unknown) => decodeValue(value, isCollection, 'Invalid collection response');
export const decodeCollectionItem = (value: unknown) => {
  const item = decodeValue(value, isCollectionItem, 'Invalid collection item response');
  const subject = subjectSummaryFromEntity(item.entity);
  return {
    ...item,
    subject,
    user_subject: {
      id: item.library_entry_id,
      entity: item.entity,
      status: 'wish',
      simple_rating: null,
      rating: null,
      comment: '',
      watch_start_date: null,
      watch_end_date: null,
      is_public: true,
      releases: [],
      created_at: new Date(0).toISOString(),
      updated_at: new Date(0).toISOString(),
      subject,
    },
  } satisfies CollectionItem;
};
export const decodeCollectionItems = (value: unknown) =>
  decodeArray(value, decodeCollectionItem, 'Invalid collection item list response');

export function decodePublicUserSubject(value: unknown): UserSubject {
  const userSubject = decodeUserSubject(value);
  return userSubject;
}

export function decodePublicReview(value: unknown): Review {
  return decodeReview(value);
}

export function decodePublicCollection(value: unknown): Collection {
  return decodeCollection(value);
}

function isUserSubjectContext(value: unknown): value is UserSubjectContext {
  return (
    isRecord(value) &&
    typeof value['is_marked'] === 'boolean' &&
    (value['user_subject'] === null || isLibraryEntry(value['user_subject'])) &&
    Array.isArray(value['tags']) &&
    value['tags'].every(isTag) &&
    Array.isArray(value['rating_details']) &&
    value['rating_details'].every(isRatingDetail) &&
    Array.isArray(value['reviews']) &&
    value['reviews'].every(isReview) &&
    isProgressSummary(value['progress'])
  );
}

export function decodeUserSubjectContext(value: unknown): UserSubjectContext {
  return decodeValue(value, isUserSubjectContext, 'Invalid user subject context response');
}
