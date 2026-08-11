import type { AccessTokenPayload, CurrentUserProfile, ProfileStats } from '@/shared/api';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isOptionalString(value: unknown) {
  return value === undefined || typeof value === 'string';
}

function isOneOf<TValue extends string>(value: unknown, values: readonly TValue[]): value is TValue {
  return typeof value === 'string' && values.some((candidate) => candidate === value);
}

function isInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value);
}

function isNonNegativeInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
}

function isPositiveInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value > 0;
}

function isMarkCalendarEntry(value: unknown): value is ProfileStats['mark_calendar'][number] {
  return (
    isRecord(value) &&
    typeof value['date'] === 'string' &&
    /^\d{4}-\d{2}-\d{2}$/.test(value['date']) &&
    isNonNegativeInteger(value['count'])
  );
}

export function decodeAccessTokenPayload(value: unknown): AccessTokenPayload {
  if (!isRecord(value) || typeof value['access'] !== 'string' || !value['access'].trim()) {
    throw new TypeError('Invalid access token response');
  }

  return { access: value['access'] };
}

export function decodeAvatarUpload(value: unknown): { avatar: string } {
  if (!isRecord(value) || typeof value['avatar'] !== 'string' || !value['avatar'].trim()) {
    throw new TypeError('Invalid avatar upload response');
  }

  return { avatar: value['avatar'] };
}

export function decodeCurrentUserProfile(value: unknown): CurrentUserProfile {
  if (
    !isRecord(value) ||
    !isPositiveInteger(value['user_id']) ||
    typeof value['email'] !== 'string' ||
    typeof value['nickname'] !== 'string' ||
    typeof value['is_staff'] !== 'boolean' ||
    typeof value['is_superuser'] !== 'boolean' ||
    (value['avatar'] !== null && typeof value['avatar'] !== 'string') ||
    !isOptionalString(value['bio']) ||
    (value['language'] !== undefined && !isOneOf(value['language'], ['auto', 'en-US', 'zh-CN', 'ja-JP'])) ||
    (value['appearance'] !== undefined && !isOneOf(value['appearance'], ['auto', 'light', 'dark']))
  ) {
    throw new TypeError('Invalid current user profile response');
  }

  return {
    user_id: value['user_id'],
    email: value['email'],
    is_staff: value['is_staff'],
    is_superuser: value['is_superuser'],
    nickname: value['nickname'],
    avatar: value['avatar'],
    ...(value['bio'] === undefined ? {} : { bio: value['bio'] }),
    ...(value['language'] === undefined ? {} : { language: value['language'] }),
    ...(value['appearance'] === undefined ? {} : { appearance: value['appearance'] }),
  };
}

export function decodeProfileStats(value: unknown): ProfileStats {
  if (!isRecord(value) || !isRecord(value['totals']) || !Array.isArray(value['available_years'])) {
    throw new TypeError('Invalid profile stats response');
  }

  const totals = value['totals'];
  const markCalendar = value['mark_calendar'];
  if (
    !isInteger(value['year']) ||
    !value['available_years'].every(isInteger) ||
    !isNonNegativeInteger(totals['subjects']) ||
    !isNonNegativeInteger(totals['reviews']) ||
    !isNonNegativeInteger(totals['collections']) ||
    !isNonNegativeInteger(totals['marks_in_year']) ||
    !Array.isArray(markCalendar) ||
    !markCalendar.every(isMarkCalendarEntry)
  ) {
    throw new TypeError('Invalid profile stats response');
  }

  return {
    year: value['year'],
    available_years: value['available_years'],
    totals: {
      subjects: totals['subjects'],
      reviews: totals['reviews'],
      collections: totals['collections'],
      marks_in_year: totals['marks_in_year'],
    },
    mark_calendar: markCalendar,
  };
}
