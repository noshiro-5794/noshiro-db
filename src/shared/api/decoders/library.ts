import type {
  Collection,
  CollectionItem,
  ProgressSummary,
  RatingDetail,
  Review,
  Tag,
  UserSubject,
  UserSubjectContext,
} from '../contracts/library';
import type { PublicUserSummary } from '../contracts/user';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isInteger(value: unknown, minimum = Number.MIN_SAFE_INTEGER): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= minimum;
}

function isOptionalString(value: unknown) {
  return value === undefined || typeof value === 'string';
}

function isNullableString(value: unknown) {
  return value === null || typeof value === 'string';
}

function isOptionalNonNegativeInteger(value: unknown) {
  return value === undefined || isInteger(value, 0);
}

function isPublicUserSummary(value: unknown): value is PublicUserSummary {
  return (
    isRecord(value) &&
    isInteger(value['id'], 1) &&
    typeof value['nickname'] === 'string' &&
    isNullableString(value['avatar'])
  );
}

function isReviewSubject(value: unknown): value is NonNullable<Review['subject']> {
  return (
    isRecord(value) &&
    typeof value['id'] === 'string' &&
    Boolean(value['id']) &&
    typeof value['title'] === 'string' &&
    isNullableString(value['title_cn']) &&
    typeof value['subject_type'] === 'string' &&
    isNullableString(value['date']) &&
    typeof value['nsfw'] === 'boolean' &&
    (value['image_thumbnail'] === undefined || isNullableString(value['image_thumbnail']))
  );
}

function isSubjectSummary(value: unknown): value is UserSubject['subject'] {
  return (
    isReviewSubject(value) &&
    isNullableString(value['platform']) &&
    (value['image'] === undefined || isNullableString(value['image']))
  );
}

function isTag(value: unknown): value is Tag {
  return isRecord(value) && isInteger(value['id'], 1) && typeof value['name'] === 'string';
}

function isRatingDetail(value: unknown): value is RatingDetail {
  return isRecord(value) && typeof value['key'] === 'string' && typeof value['value'] === 'string';
}

function isUserSubjectBase(value: unknown): value is CollectionItem['user_subject'] & Record<string, unknown> {
  return (
    isRecord(value) &&
    isInteger(value['id'], 1) &&
    typeof value['status'] === 'string' &&
    (value['simple_rating'] === null || isInteger(value['simple_rating'], 1)) &&
    isNullableString(value['rating']) &&
    typeof value['comment'] === 'string' &&
    isNullableString(value['watch_start_date']) &&
    isNullableString(value['watch_end_date']) &&
    typeof value['is_public'] === 'boolean'
  );
}

function isUserSubject(value: unknown): value is UserSubject {
  return isUserSubjectBase(value) && isSubjectSummary(value['subject']);
}

function isReview(value: unknown): value is Review {
  if (
    !isRecord(value) ||
    !isInteger(value['id'], 1) ||
    typeof value['title'] !== 'string' ||
    typeof value['content'] !== 'string' ||
    typeof value['is_public'] !== 'boolean' ||
    typeof value['is_spoiler'] !== 'boolean' ||
    !isOptionalNonNegativeInteger(value['reaction_count']) ||
    !isOptionalString(value['created_at']) ||
    !isOptionalString(value['updated_at']) ||
    (value['subject'] !== undefined && !isReviewSubject(value['subject'])) ||
    (value['user'] !== undefined && !isPublicUserSummary(value['user']))
  ) {
    return false;
  }

  const viewerState = value['viewer_state'];
  return (
    viewerState === undefined ||
    (isRecord(viewerState) &&
      typeof viewerState['has_liked'] === 'boolean' &&
      typeof viewerState['has_bookmarked'] === 'boolean')
  );
}

function isProgressEpisode(value: unknown) {
  return (
    isRecord(value) &&
    isInteger(value['id'], 1) &&
    typeof value['title'] === 'string' &&
    typeof value['type'] === 'string' &&
    (value['ep_num'] === null || isInteger(value['ep_num'])) &&
    (value['sort'] === null || isInteger(value['sort'])) &&
    isNullableString(value['date']) &&
    typeof value['is_finished'] === 'boolean'
  );
}

function isProgressSummary(value: unknown): value is ProgressSummary {
  return (
    isRecord(value) &&
    (value['subject_id'] === undefined || typeof value['subject_id'] === 'string') &&
    (value['user_subject_id'] === undefined ||
      value['user_subject_id'] === null ||
      isInteger(value['user_subject_id'], 1)) &&
    isOptionalNonNegativeInteger(value['total_episodes']) &&
    isInteger(value['finished_count'], 0) &&
    Array.isArray(value['finished_episode_ids']) &&
    value['finished_episode_ids'].every((episodeId) => isInteger(episodeId, 1)) &&
    (value['episodes'] === undefined ||
      (Array.isArray(value['episodes']) && value['episodes'].every(isProgressEpisode)))
  );
}

function isCollection(value: unknown): value is Collection {
  if (
    !isRecord(value) ||
    !isInteger(value['id'], 1) ||
    typeof value['name'] !== 'string' ||
    (value['simple_rating'] !== null && !isInteger(value['simple_rating'], 1)) ||
    typeof value['note'] !== 'string' ||
    typeof value['is_public'] !== 'boolean' ||
    !isOptionalNonNegativeInteger(value['item_count']) ||
    !isOptionalNonNegativeInteger(value['reaction_count'])
  ) {
    return false;
  }

  const viewerState = value['viewer_state'];
  return (
    viewerState === undefined ||
    (isRecord(viewerState) &&
      typeof viewerState['has_liked'] === 'boolean' &&
      typeof viewerState['has_bookmarked'] === 'boolean')
  );
}

function isCollectionItem(value: unknown): value is CollectionItem {
  return (
    isRecord(value) &&
    isInteger(value['id'], 1) &&
    isUserSubjectBase(value['user_subject']) &&
    isSubjectSummary(value['subject']) &&
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
export const decodeUserSubject = (value: unknown) => decodeValue(value, isUserSubject, 'Invalid user subject response');
export const decodeReview = (value: unknown) => decodeValue(value, isReview, 'Invalid review response');
export const decodeReviews = (value: unknown) => decodeArray(value, decodeReview, 'Invalid review list response');
export const decodeProgressSummary = (value: unknown) =>
  decodeValue(value, isProgressSummary, 'Invalid progress response');
export const decodeCollection = (value: unknown) => decodeValue(value, isCollection, 'Invalid collection response');
export const decodeCollectionItem = (value: unknown) =>
  decodeValue(value, isCollectionItem, 'Invalid collection item response');
export const decodeCollectionItems = (value: unknown) =>
  decodeArray(value, decodeCollectionItem, 'Invalid collection item list response');

export function decodePublicUserSubject(value: unknown): UserSubject {
  if (!isRecord(value) || value['is_public'] !== undefined) return decodeUserSubject(value);
  return decodeUserSubject({ ...value, is_public: true });
}

export function decodePublicReview(value: unknown): Review {
  if (!isRecord(value) || value['is_public'] !== undefined) return decodeReview(value);
  return decodeReview({ ...value, is_public: true });
}

export function decodePublicCollection(value: unknown): Collection {
  if (!isRecord(value) || value['is_public'] !== undefined) return decodeCollection(value);
  return decodeCollection({ ...value, is_public: true });
}

function isUserSubjectContext(value: unknown): value is UserSubjectContext {
  return (
    isRecord(value) &&
    typeof value['is_marked'] === 'boolean' &&
    (value['user_subject'] === null || isUserSubject(value['user_subject'])) &&
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
