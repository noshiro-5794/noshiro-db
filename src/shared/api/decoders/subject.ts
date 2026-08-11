import type {
  CalendarGroup,
  CalendarSubjectItem,
  SubjectCharacter,
  SubjectDetail,
  SubjectEpisode,
  SubjectRelation,
  SubjectStaff,
  SubjectSummary,
  WeekdayEn,
} from '../contracts/subject';

const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isInteger(value: unknown, minimum = Number.MIN_SAFE_INTEGER): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= minimum;
}

function isNullableString(value: unknown) {
  return value === null || typeof value === 'string';
}

function isOptionalNullableString(value: unknown) {
  return value === undefined || isNullableString(value);
}

function isWeekday(value: unknown): value is WeekdayEn {
  return typeof value === 'string' && weekdays.some((weekday) => weekday === value);
}

function isSubjectSummary(value: unknown): value is SubjectSummary & Record<string, unknown> {
  return (
    isRecord(value) &&
    typeof value['id'] === 'string' &&
    Boolean(value['id']) &&
    typeof value['title'] === 'string' &&
    isNullableString(value['title_cn']) &&
    typeof value['subject_type'] === 'string' &&
    isNullableString(value['date']) &&
    isNullableString(value['platform']) &&
    typeof value['nsfw'] === 'boolean' &&
    isOptionalNullableString(value['image_thumbnail'])
  );
}

function isSubjectDetail(value: unknown): value is SubjectDetail {
  return (
    isSubjectSummary(value) &&
    isInteger(value['episode_count'], 0) &&
    isInteger(value['staff_count'], 0) &&
    isInteger(value['character_count'], 0)
  );
}

function isSubjectEpisode(value: unknown): value is SubjectEpisode {
  return (
    isRecord(value) &&
    isInteger(value['id'], 1) &&
    typeof value['title'] === 'string' &&
    typeof value['type'] === 'string' &&
    (value['ep_num'] === null || isInteger(value['ep_num'])) &&
    (value['sort'] === null || isInteger(value['sort'])) &&
    isNullableString(value['date']) &&
    isOptionalNullableString(value['duration']) &&
    (value['description'] === undefined || typeof value['description'] === 'string')
  );
}

function isSubjectStaff(value: unknown): value is SubjectStaff {
  return (
    isRecord(value) &&
    isInteger(value['id'], 1) &&
    typeof value['name'] === 'string' &&
    (value['role'] === undefined || isNullableString(value['role'])) &&
    (value['description'] === undefined || typeof value['description'] === 'string') &&
    isOptionalNullableString(value['image_original']) &&
    isOptionalNullableString(value['image_thumbnail'])
  );
}

function isSubjectCharacter(value: unknown): value is SubjectCharacter {
  return (
    isRecord(value) &&
    isInteger(value['id'], 1) &&
    typeof value['name'] === 'string' &&
    (value['role'] === undefined || isNullableString(value['role'])) &&
    (value['description'] === undefined || typeof value['description'] === 'string') &&
    isOptionalNullableString(value['image_original']) &&
    isOptionalNullableString(value['image_thumbnail']) &&
    (value['actors'] === undefined || (Array.isArray(value['actors']) && value['actors'].every(isSubjectStaff)))
  );
}

function isSubjectRelation(value: unknown): value is SubjectRelation {
  return (
    isRecord(value) &&
    (value['direction'] === undefined || value['direction'] === 'outgoing' || value['direction'] === 'incoming') &&
    typeof value['relation'] === 'string' &&
    isSubjectSummary(value['subject'])
  );
}

function isCalendarItem(value: unknown): value is CalendarSubjectItem {
  return (
    isRecord(value) &&
    typeof value['subject_id'] === 'string' &&
    Boolean(value['subject_id']) &&
    typeof value['subject_type'] === 'string' &&
    typeof value['title'] === 'string' &&
    isNullableString(value['title_cn']) &&
    isOptionalNullableString(value['date']) &&
    isNullableString(value['image_thumbnail']) &&
    isNullableString(value['platform']) &&
    typeof value['nsfw'] === 'boolean' &&
    isWeekday(value['weekday_en']) &&
    isInteger(value['doing'], 0)
  );
}

function isCalendarGroup(value: unknown): value is CalendarGroup {
  return (
    isRecord(value) &&
    isRecord(value['weekday']) &&
    (value['weekday']['id'] === null || isInteger(value['weekday']['id'], 1)) &&
    isWeekday(value['weekday']['en']) &&
    Array.isArray(value['items']) &&
    value['items'].every(isCalendarItem)
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

export const decodeSubjectSummary = (value: unknown) =>
  decodeValue(value, isSubjectSummary, 'Invalid subject summary response');
export const decodeSubjectDetail = (value: unknown) =>
  decodeValue(value, isSubjectDetail, 'Invalid subject detail response');
export const decodeSubjectEpisode = (value: unknown) =>
  decodeValue(value, isSubjectEpisode, 'Invalid subject episode response');
export const decodeSubjectStaff = (value: unknown) =>
  decodeValue(value, isSubjectStaff, 'Invalid subject staff response');
export const decodeSubjectCharacter = (value: unknown) =>
  decodeValue(value, isSubjectCharacter, 'Invalid subject character response');
export const decodeSubjectRelation = (value: unknown) =>
  decodeValue(value, isSubjectRelation, 'Invalid subject relation response');

export function decodeSubjectStaffRoles(value: unknown): { roles: string[] } {
  if (!isRecord(value) || !Array.isArray(value['roles']) || !value['roles'].every((role) => typeof role === 'string')) {
    throw new TypeError('Invalid subject staff roles response');
  }
  return { roles: value['roles'] };
}

export const decodeCalendarGroups = (value: unknown) =>
  decodeArray(
    value,
    (group) => decodeValue(group, isCalendarGroup, 'Invalid calendar group'),
    'Invalid calendar response',
  );
