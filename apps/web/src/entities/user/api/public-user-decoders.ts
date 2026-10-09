import type { PublicUserProfile } from '@/shared/api';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isNonNegativeInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
}

export function decodePublicUserProfile(value: unknown): PublicUserProfile {
  if (!isRecord(value) || !isRecord(value['stats'])) {
    throw new TypeError('Invalid public user profile response');
  }

  const stats = value['stats'];
  if (
    !isNonNegativeInteger(value['id']) ||
    value['id'] === 0 ||
    typeof value['nickname'] !== 'string' ||
    (value['avatar'] !== null && typeof value['avatar'] !== 'string') ||
    typeof value['bio'] !== 'string' ||
    typeof value['is_following'] !== 'boolean' ||
    !isNonNegativeInteger(stats['library_entry_count']) ||
    !isNonNegativeInteger(stats['review_count']) ||
    !isNonNegativeInteger(stats['collection_count']) ||
    !isNonNegativeInteger(stats['following_count']) ||
    !isNonNegativeInteger(stats['follower_count'])
  ) {
    throw new TypeError('Invalid public user profile response');
  }

  return {
    id: value['id'],
    nickname: value['nickname'],
    avatar: value['avatar'],
    bio: value['bio'],
    is_following: value['is_following'],
    stats: {
      library_entry_count: stats['library_entry_count'],
      review_count: stats['review_count'],
      collection_count: stats['collection_count'],
      following_count: stats['following_count'],
      follower_count: stats['follower_count'],
    },
  };
}
