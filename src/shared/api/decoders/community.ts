import type {
  Activity,
  CommunityBookmark,
  CommunityCommentSummary,
  CommunityNotification,
  CommunityNotificationReadAllResult,
  CommunityNotificationUnreadCount,
  CommunityPostSummary,
  CommunityReaction,
  CommunityRelationship,
  CommunityReport,
} from '../contracts/community';
import type { FollowRelation, PublicUserSummary } from '../contracts/user';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isInteger(value: unknown, minimum = Number.MIN_SAFE_INTEGER): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= minimum;
}

function isOptionalInteger(value: unknown, minimum = Number.MIN_SAFE_INTEGER) {
  return value === undefined || isInteger(value, minimum);
}

function isNullableString(value: unknown) {
  return value === null || typeof value === 'string';
}

function isUser(value: unknown): value is PublicUserSummary {
  return (
    isRecord(value) &&
    isInteger(value['id'], 1) &&
    typeof value['nickname'] === 'string' &&
    isNullableString(value['avatar'])
  );
}

function isTargetReference(value: unknown) {
  return isRecord(value) && typeof value['type'] === 'string' && isInteger(value['id'], 1);
}

function isFollowRelation(value: unknown): value is FollowRelation {
  return isRecord(value) && isUser(value['user']) && typeof value['followed_at'] === 'string';
}

function isRelationship(value: unknown): value is CommunityRelationship {
  return (
    isRecord(value) &&
    isUser(value['user']) &&
    typeof value['reason'] === 'string' &&
    typeof value['created_at'] === 'string'
  );
}

function isActivity(value: unknown): value is Activity {
  if (
    !isRecord(value) ||
    !isInteger(value['id'], 1) ||
    typeof value['activity_type'] !== 'string' ||
    typeof value['created_at'] !== 'string' ||
    !isOptionalInteger(value['reaction_count'], 0) ||
    !isOptionalInteger(value['reply_count'], 0) ||
    (value['user'] !== undefined && value['user'] !== null && !isUser(value['user'])) ||
    (value['target_user'] !== undefined && value['target_user'] !== null && !isUser(value['target_user']))
  ) {
    return false;
  }

  const viewerState = value['viewer_state'];
  return viewerState === undefined || (isRecord(viewerState) && typeof viewerState['has_liked'] === 'boolean');
}

function isPost(value: unknown): value is CommunityPostSummary {
  if (
    !isRecord(value) ||
    !isInteger(value['id'], 1) ||
    typeof value['content'] !== 'string' ||
    typeof value['visibility'] !== 'string' ||
    typeof value['is_spoiler'] !== 'boolean' ||
    typeof value['is_nsfw'] !== 'boolean' ||
    !isOptionalInteger(value['reply_count'], 0) ||
    !isOptionalInteger(value['reaction_count'], 0) ||
    (value['author'] !== undefined && value['author'] !== null && !isUser(value['author']))
  ) {
    return false;
  }

  const viewerState = value['viewer_state'];
  return (
    viewerState === undefined ||
    (isRecord(viewerState) &&
      typeof viewerState['has_liked'] === 'boolean' &&
      typeof viewerState['has_bookmarked'] === 'boolean' &&
      typeof viewerState['is_following_author'] === 'boolean')
  );
}

function isComment(value: unknown): value is CommunityCommentSummary {
  if (
    !isRecord(value) ||
    !isInteger(value['id'], 1) ||
    (value['parent_id'] !== undefined && value['parent_id'] !== null && !isInteger(value['parent_id'], 1)) ||
    typeof value['content'] !== 'string' ||
    typeof value['visibility'] !== 'string' ||
    typeof value['is_spoiler'] !== 'boolean' ||
    !isOptionalInteger(value['reply_count'], 0) ||
    !isOptionalInteger(value['reaction_count'], 0) ||
    (value['target'] !== undefined && value['target'] !== null && !isTargetReference(value['target'])) ||
    (value['author'] !== undefined && value['author'] !== null && !isUser(value['author']))
  ) {
    return false;
  }

  const viewerState = value['viewer_state'];
  return (
    viewerState === undefined ||
    (isRecord(viewerState) &&
      typeof viewerState['has_liked'] === 'boolean' &&
      typeof viewerState['is_following_author'] === 'boolean')
  );
}

function isReaction(value: unknown): value is CommunityReaction {
  return (
    isRecord(value) &&
    isInteger(value['id'], 1) &&
    typeof value['target_type'] === 'string' &&
    isInteger(value['target_id'], 1) &&
    typeof value['reaction_type'] === 'string' &&
    typeof value['created_at'] === 'string'
  );
}

function isBookmark(value: unknown): value is CommunityBookmark {
  return (
    isRecord(value) &&
    isInteger(value['id'], 1) &&
    typeof value['target_type'] === 'string' &&
    isInteger(value['target_id'], 1) &&
    (value['target'] === undefined || value['target'] === null || isTargetReference(value['target'])) &&
    typeof value['created_at'] === 'string'
  );
}

function isNotification(value: unknown): value is CommunityNotification {
  return (
    isRecord(value) &&
    isInteger(value['id'], 1) &&
    typeof value['notification_type'] === 'string' &&
    (value['actor'] === null || isUser(value['actor'])) &&
    (value['target'] === null || isTargetReference(value['target'])) &&
    isRecord(value['metadata']) &&
    typeof value['is_read'] === 'boolean' &&
    isNullableString(value['read_at']) &&
    typeof value['created_at'] === 'string'
  );
}

function isReport(value: unknown): value is CommunityReport {
  return (
    isRecord(value) &&
    isInteger(value['id'], 1) &&
    typeof value['reason'] === 'string' &&
    typeof value['description'] === 'string' &&
    typeof value['status'] === 'string' &&
    isUser(value['reporter']) &&
    (value['reported_user'] === null || isUser(value['reported_user'])) &&
    (value['target'] === null || isTargetReference(value['target'])) &&
    (value['resolved_by'] === null || isUser(value['resolved_by'])) &&
    isNullableString(value['resolved_at']) &&
    typeof value['created_at'] === 'string'
  );
}

function decodeValue<T>(value: unknown, predicate: (candidate: unknown) => candidate is T, message: string): T {
  if (!predicate(value)) throw new TypeError(message);
  return value;
}

export const decodeFollowRelation = (value: unknown) =>
  decodeValue(value, isFollowRelation, 'Invalid follow relation response');
export const decodeCommunityRelationship = (value: unknown) =>
  decodeValue(value, isRelationship, 'Invalid community relationship response');
export const decodeActivity = (value: unknown) => decodeValue(value, isActivity, 'Invalid activity response');
export const decodeCommunityPost = (value: unknown) => decodeValue(value, isPost, 'Invalid community post response');
export const decodeCommunityComment = (value: unknown) =>
  decodeValue(value, isComment, 'Invalid community comment response');
export const decodeCommunityReaction = (value: unknown) =>
  decodeValue(value, isReaction, 'Invalid community reaction response');
export const decodeCommunityBookmark = (value: unknown) =>
  decodeValue(value, isBookmark, 'Invalid community bookmark response');
export const decodeCommunityNotification = (value: unknown) =>
  decodeValue(value, isNotification, 'Invalid community notification response');
export const decodeCommunityReport = (value: unknown) =>
  decodeValue(value, isReport, 'Invalid community report response');

export function decodeNotificationUnreadCount(value: unknown): CommunityNotificationUnreadCount {
  if (!isRecord(value) || !isInteger(value['unread_count'], 0)) {
    throw new TypeError('Invalid notification unread count response');
  }
  return { unread_count: value['unread_count'] };
}

export function decodeNotificationReadAllResult(value: unknown): CommunityNotificationReadAllResult {
  if (!isRecord(value) || !isInteger(value['updated_count'], 0)) {
    throw new TypeError('Invalid notification read-all response');
  }
  return { updated_count: value['updated_count'] };
}
