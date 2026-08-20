import type {
  CalendarEvent,
  CalendarGroup,
  CalendarSubjectItem,
  EntityCharacter,
  EntityCredit,
  EntityDetail,
  EntityEpisode,
  EntityMedia,
  EntityRelation,
  EntitySummary,
  FieldProvenance,
  FactEvidence,
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

function isString(value: unknown): value is string {
  return typeof value === 'string';
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === 'string';
}

function isInteger(value: unknown, minimum = Number.MIN_SAFE_INTEGER): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= minimum;
}

function isFieldProvenance(value: unknown): value is FieldProvenance {
  return (
    isRecord(value) &&
    typeof value['provider'] === 'string' &&
    typeof value['namespace'] === 'string' &&
    typeof value['external_id'] === 'string' &&
    isNullableString(value['observation_id']) &&
    isNullableString(value['revision_id']) &&
    isNullableString(value['observed_at'])
  );
}

function isEntityMedia(value: unknown): value is EntityMedia {
  return (
    isRecord(value) &&
    typeof value['url'] === 'string' &&
    typeof value['purpose'] === 'string' &&
    typeof value['safety'] === 'string' &&
    (value['provenance'] === null || isFieldProvenance(value['provenance']))
  );
}

function isEntitySummary(value: unknown): value is EntitySummary & Record<string, unknown> {
  return (
    isRecord(value) &&
    typeof value['id'] === 'string' &&
    Boolean(value['id']) &&
    typeof value['entity_type'] === 'string' &&
    typeof value['lifecycle'] === 'string' &&
    typeof value['audience'] === 'string' &&
    (value['work_type'] === null || typeof value['work_type'] === 'string') &&
    typeof value['display_name'] === 'string' &&
    Array.isArray(value['collections']) &&
    value['collections'].every(isString) &&
    Array.isArray(value['media']) &&
    value['media'].every(isEntityMedia)
  );
}

function isEntityDetail(value: unknown): value is EntityDetail {
  return (
    isEntitySummary(value) &&
    Array.isArray(value['names']) &&
    Array.isArray(value['descriptions']) &&
    Array.isArray(value['facts']) &&
    Array.isArray(value['external_links']) &&
    Array.isArray(value['content_ratings']) &&
    Array.isArray(value['sources'])
  );
}

function mediaByPurpose(media: EntityMedia[], purpose: string) {
  return media.find((item) => item.purpose.toLowerCase() === purpose.toLowerCase())?.url ?? null;
}

function firstMediaUrl(media: EntityMedia[]) {
  return media[0]?.url ?? null;
}

function buildSubjectImages(media: EntityMedia[]) {
  const poster = mediaByPurpose(media, 'poster') ?? mediaByPurpose(media, 'cover') ?? firstMediaUrl(media);
  const thumbnail = mediaByPurpose(media, 'thumbnail') ?? poster;
  const original = mediaByPurpose(media, 'original') ?? poster;

  return {
    poster,
    thumbnail,
    original,
  };
}

function buildSubjectSummary(value: EntitySummary): SubjectSummary {
  const subjectType = value.work_type ?? value.entity_type;
  const images = buildSubjectImages(value.media);
  const nsfw = value.audience === 'adult';
  const platform = null;
  const sourceId = undefined;
  const displayMeta = [value.work_type, value.entity_type, value.lifecycle, value.audience].filter(
    (item): item is string => typeof item === 'string' && Boolean(item),
  );

  return {
    ...value,
    title: value.display_name,
    title_cn: null,
    display_title: value.display_name,
    display_meta: displayMeta,
    ...(value.collections[0] ? { display_subtitle: value.collections[0] } : {}),
    subject_type: subjectType,
    date: null,
    platform,
    nsfw,
    ...(images.poster ? { image: images.poster } : {}),
    ...(images.thumbnail ? { image_thumbnail: images.thumbnail } : {}),
    images,
    ...(images.original ? { image_original: images.original } : {}),
    ...(sourceId === undefined ? {} : { source_id: sourceId }),
  };
}

export const subjectSummaryFromEntity = buildSubjectSummary;

function preferredName(names: Array<{ text: string; language: string; kind: string }>) {
  return (
    names.find((name) => /^zh\b/iu.test(name.language))?.text ??
    names.find((name) => ['official', 'original'].includes(name.kind))?.text ??
    names[0]?.text ??
    null
  );
}

function buildSubjectDetail(value: EntityDetail): SubjectDetail {
  const summary = buildSubjectSummary(value);
  const firstDescription = value.descriptions.find((description) => description.is_official) ?? value.descriptions[0];
  const descriptionText = firstDescription?.text;
  const titleCn = preferredName(value.names as Array<{ text: string; language: string; kind: string }>);

  return {
    ...summary,
    names: value.names,
    descriptions: value.descriptions,
    facts: value.facts,
    external_links: value.external_links,
    content_ratings: value.content_ratings,
    sources: value.sources,
    title_cn: titleCn ?? summary.title_cn,
    ...(descriptionText ? { summary: descriptionText } : {}),
    ...(descriptionText ? { description: descriptionText } : {}),
    ...(descriptionText ? { description_excerpt: descriptionText.slice(0, 240) } : {}),
    episode_count: 0,
    staff_count: 0,
    character_count: 0,
    infobox: value.facts.map((fact) => ({ key: fact.predicate, value: fact.value })),
    tags: value.collections,
    ...(value.sources[0] ? { source: { provider: value.sources[0].provider, id: value.sources[0].external_id } } : {}),
    ...(value.sources[0] ? { source_id: value.sources[0].external_id } : {}),
  };
}

function toNullableDecimal(value: string): number | null {
  if (value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function decodeEntityEpisode(value: unknown): SubjectEpisode {
  if (
    !isRecord(value) ||
    typeof value['id'] !== 'string' ||
    typeof value['title'] !== 'string' ||
    typeof value['title_cn'] !== 'string' ||
    typeof value['type'] !== 'string' ||
    typeof value['number'] !== 'string' ||
    typeof value['sort'] !== 'string' ||
    typeof value['air_date'] !== 'string'
  ) {
    throw new TypeError('Invalid entity episode response');
  }

  return {
    ...(value as unknown as EntityEpisode),
    ep_num: toNullableDecimal(value['number']),
    date: value['air_date'],
  };
}

function decodeEntityCredit(value: unknown): SubjectStaff {
  if (!isRecord(value) || !isEntitySummary(value['contributor'])) {
    throw new TypeError('Invalid entity credit response');
  }

  const contributor = buildSubjectSummary(value['contributor'] as EntitySummary);
  return {
    ...contributor,
    name: contributor.display_name,
    role: typeof value['role'] === 'string' ? value['role'] : null,
    type: typeof value['credited_as'] === 'string' ? value['credited_as'] : null,
  };
}

function decodeEntityCharacter(value: unknown): SubjectCharacter {
  if (!isRecord(value) || !isEntitySummary(value['character'])) {
    throw new TypeError('Invalid entity character response');
  }

  const character = buildSubjectSummary(value['character'] as EntitySummary);
  return {
    ...character,
    name: character.display_name,
    role: typeof value['role'] === 'string' ? value['role'] : null,
    type: character.entity_type,
    actors: [],
  };
}

function decodeEntityRelation(value: unknown): SubjectRelation {
  if (!isRecord(value) || typeof value['relation_type'] !== 'string' || !isEntitySummary(value['target'])) {
    throw new TypeError('Invalid entity relation response');
  }

  return {
    relation: value['relation_type'],
    subject: buildSubjectSummary(value['target'] as EntitySummary),
    ...(Array.isArray(value['evidence']) ? { evidence: value['evidence'] as FactEvidence[] } : {}),
  };
}

function weekdayFromNumber(value: number | null): WeekdayEn | null {
  if (value === null || !Number.isInteger(value) || value < 1 || value > 7) return null;
  return weekdays[value - 1] ?? null;
}

function calendarEventToItem(value: CalendarEvent): CalendarSubjectItem {
  const weekday = weekdayFromNumber(value.weekday);
  return {
    subject_id: value.work_id,
    subject_type: 'anime',
    title: value.raw_value,
    title_cn: null,
    display_title: value.raw_value,
    date: value.starts_at?.slice(0, 10) ?? null,
    image_url: null,
    image: null,
    image_thumbnail: null,
    platform: value.region || value.timezone,
    nsfw: false,
    weekday_en: weekday ?? 'Mon',
    doing: 0,
  };
}

export function decodeCalendarEvents(value: unknown): CalendarEvent[] {
  if (
    !Array.isArray(value) ||
    !value.every(
      (item) =>
        isRecord(item) &&
        isInteger(item['id'], 0) &&
        typeof item['work_id'] === 'string' &&
        isNullableString(item['episode_id']) &&
        isNullableString(item['starts_at']) &&
        typeof item['timezone'] === 'string' &&
        typeof item['region'] === 'string' &&
        (item['weekday'] === null || (isInteger(item['weekday']) && item['weekday'] >= 1 && item['weekday'] <= 7)) &&
        typeof item['precision'] === 'string' &&
        typeof item['raw_value'] === 'string',
    )
  ) {
    throw new TypeError('Invalid calendar events response');
  }

  return value as unknown as CalendarEvent[];
}

export function decodeCalendarEventsToGroups(value: unknown): CalendarGroup[] {
  const events = decodeCalendarEvents(value);
  const groups = new Map<WeekdayEn, CalendarSubjectItem[]>();

  for (const event of events) {
    const item = calendarEventToItem(event);
    const weekday = item.weekday_en;
    const items = groups.get(weekday) ?? [];
    items.push(item);
    groups.set(weekday, items);
  }

  return weekdays.map((weekday) => ({
    weekday: { id: weekdays.indexOf(weekday) + 1, en: weekday },
    items: groups.get(weekday) ?? [],
  }));
}

function decodeValue<T>(value: unknown, predicate: (candidate: unknown) => candidate is T, message: string): T {
  if (!predicate(value)) throw new TypeError(message);
  return value;
}

export const decodeSubjectSummary = (value: unknown) =>
  buildSubjectSummary(decodeValue(value, isEntitySummary, 'Invalid entity summary response'));
export const decodeSubjectDetail = (value: unknown) =>
  buildSubjectDetail(decodeValue(value, isEntityDetail, 'Invalid entity detail response'));
export const decodeSubjectEpisode = decodeEntityEpisode;
export const decodeSubjectStaff = decodeEntityCredit;
export const decodeSubjectCharacter = decodeEntityCharacter;
export const decodeSubjectRelation = decodeEntityRelation;

export function decodeSubjectStaffRoles(value: unknown): { roles: string[] } {
  if (!isRecord(value) || !Array.isArray(value['roles']) || !value['roles'].every(isString)) {
    throw new TypeError('Invalid staff roles response');
  }
  return { roles: value['roles'] };
}

export const decodeCalendarGroups = decodeCalendarEventsToGroups;

export type { EntityCharacter, EntityCredit, EntityRelation };
