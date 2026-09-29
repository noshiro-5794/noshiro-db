import { placeholderImagePaths } from '@/shared/assets/public-assets';
import type { MessageKey } from '@/shared/i18n';
import type { SubjectDetail, SubjectEpisode, SubjectRelation, SubjectStaff } from '@/shared/api';

export const coverPlaceholder = placeholderImagePaths.subjectCover;

const relationVisualPageBudget = 6.4;
const relationChunkSize = 9;
const maxUnknownValueDepth = 5;

const importantInfoboxKeys = [
  '话数',
  '放送开始',
  '放送星期',
  '上映年度',
  '发售日',
  '开发',
  '发行',
  '平台',
  '游戏类型',
  '原作',
  '导演',
  '監督',
  '脚本',
  '音乐',
  '音楽',
  '动画制作',
  '製作',
];

const importantStaffRoles = [
  '監督',
  '导演',
  'director',
  '原作',
  '脚本',
  '系列构成',
  'シリーズ構成',
  'キャラクターデザイン',
  '角色设计',
  '音楽',
  '音乐',
  '动画制作',
];

export type InfoboxRow = {
  key: string;
  value: string;
};

export type RelationDisplayGroup = {
  key: string;
  label: string;
  tier: 'primary' | 'other';
  items: SubjectRelation[];
  totalCount: number;
};

export function titleOf(subject: SubjectDetail, fallback = 'Untitled') {
  return subject.display_title || subject.title || subject.title_cn || fallback;
}

/**
 * One-line summary under the title: what it is, when it started, whether it is
 * still running. Built from the same normalised attributes as the sidebar, so
 * the page never shows a raw provider slug like `anime` or `currently_airing`.
 */
export function metaOf(subject: SubjectDetail, t?: (key: MessageKey) => string) {
  const attributes = subjectAttributes(subject);
  const value = (key: string) => {
    const item = attributes.find((attribute) => attribute.key === key);
    if (!item) return '';
    const valueKey = attributeValueKey(item.key, item.value);
    if (valueKey && t) return t(valueKey);
    return item.key === 'format' || item.key === 'type' ? item.value.toUpperCase() : item.value;
  };
  return (
    [value('format') || value('type') || subject.subject_type, value('release-date'), value('status')]
      .filter(Boolean)
      .join(' · ') || subject.subject_type
  );
}

export function seoDescriptionOf(subject: SubjectDetail) {
  return (
    subject.description_excerpt ||
    subject.summary ||
    subject.description ||
    metaOf(subject) ||
    'Open anime and galgame details on Noshiro DB.'
  );
}

export function seoImageOf(subject: SubjectDetail) {
  return (
    subject.images?.original ||
    subject.images?.poster ||
    subject.image_original ||
    subject.images?.thumbnail ||
    subject.image_thumbnail ||
    null
  );
}

export function bangumiSubjectIdOf(subject?: SubjectDetail | null) {
  const source = subject?.source;
  const sourceId = source ? (source.provider === 'bangumi' ? source.id : null) : (subject?.source_id ?? null);
  const value = typeof sourceId === 'string' && /^\d+$/u.test(sourceId) ? Number(sourceId) : sourceId;
  return typeof value === 'number' && Number.isSafeInteger(value) && value > 0 ? value : null;
}

export function episodeTitle(episode: SubjectEpisode) {
  return episode.title || (episode.ep_num ? `Episode ${episode.ep_num}` : `Episode ${episode.id}`);
}

export function episodeLabel(episode: SubjectEpisode) {
  if (episode.type === 'EP') return `EP ${episode.ep_num ?? episode.sort ?? episode.id}`;

  return [episode.type, episode.sort ?? episode.ep_num].filter((item) => item !== null && item !== '').join(' ');
}

function formatInfoboxValue(value: unknown): string {
  if (typeof value === 'string') return value;

  if (Array.isArray(value)) {
    return value
      .map((item) => {
        if (typeof item === 'string') return item;
        if (item && typeof item === 'object') {
          const record = item as Record<string, unknown>;
          return [record['v'], record['name'], record['title']].find((entry) => typeof entry === 'string');
        }
        return '';
      })
      .filter(Boolean)
      .join(' / ');
  }

  if (value && typeof value === 'object') {
    return Object.values(value as Record<string, unknown>)
      .filter((entry): entry is string => typeof entry === 'string' && Boolean(entry))
      .join(' / ');
  }

  return '';
}

function formatUnknownValueInner(value: unknown, depth: number, seen: WeakSet<object>): string {
  if (value === null || value === undefined || value === '') return '';
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (typeof value !== 'object' || depth >= maxUnknownValueDepth || seen.has(value)) return '';

  seen.add(value);
  const formatted = Array.isArray(value)
    ? value
        .map((item) => formatUnknownValueInner(item, depth + 1, seen))
        .filter(Boolean)
        .join(' / ')
    : Object.entries(value)
        .map(([key, item]) => {
          const itemValue = formatUnknownValueInner(item, depth + 1, seen);
          return itemValue ? `${key}: ${itemValue}` : '';
        })
        .filter(Boolean)
        .join(' / ');
  seen.delete(value);
  return formatted;
}

export function formatUnknownValue(value: unknown) {
  return formatUnknownValueInner(value, 0, new WeakSet());
}

export function compactText(value: string | null | undefined, fallback: string) {
  return value?.trim() || fallback;
}

export function detailRows(rows: Array<[string, unknown]>) {
  return rows
    .map(([label, value]) => [label, formatUnknownValue(value)] as const)
    .filter(([, value]) => Boolean(value));
}

export function getInfoboxRows(infobox: unknown): InfoboxRow[] {
  if (!Array.isArray(infobox)) return [];

  return infobox
    .map((item) => {
      if (!item || typeof item !== 'object') return null;
      const record = item as Record<string, unknown>;
      const key = typeof record['key'] === 'string' ? record['key'].trim() : '';
      const value = formatInfoboxValue(record['value']).trim();
      return key && value ? { key, value } : null;
    })
    .filter((row): row is InfoboxRow => Boolean(row));
}

export function sortInfoboxRows(rows: InfoboxRow[]) {
  return [...rows].sort((a, b) => {
    const aIndex = importantInfoboxKeys.findIndex((key) => a.key.includes(key));
    const bIndex = importantInfoboxKeys.findIndex((key) => b.key.includes(key));
    return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex);
  });
}

/**
 * Facts arrive as provider-scoped predicates (`anilist-season`, `mal-status`),
 * which is internal vocabulary a visitor cannot read. Normalise them into a
 * short, ordered list of attributes the page can label in the reader's
 * language, and drop provider bookkeeping such as cross-source ids.
 */
export type SubjectAttribute = {
  /** Stable key the UI maps to a translated label. */
  key: string;
  /** Raw value, already normalised where the vocabulary is known. */
  value: string;
  /** Which provider the value came from, for the small source hint. */
  provider: string;
};

const providerPrefix = /^(anilist|mal|bangumi|vndb|jikan)-/u;

/** Predicates worth showing, in the order a reader looks for them. */
const attributeOrder = [
  'type',
  'format',
  'episodes',
  'release-date',
  'end-date',
  'broadcast-day',
  'broadcast-time',
  'broadcast-timezone',
  'season',
  'status',
];

const weekdayLabels: Record<string, string> = {
  monday: 'mon',
  tuesday: 'tue',
  wednesday: 'wed',
  thursday: 'thu',
  friday: 'fri',
  saturday: 'sat',
  sunday: 'sun',
};

export function subjectAttributes(subject: SubjectDetail): SubjectAttribute[] {
  const rows = getInfoboxRows(subject.infobox);
  const byKey = new Map<string, SubjectAttribute>();

  for (const row of rows) {
    const provider = providerPrefix.exec(row.key)?.[1] ?? '';
    const key = row.key.replace(providerPrefix, '');
    if (/-id-|^id$/u.test(key)) continue;
    const index = attributeOrder.indexOf(key);
    if (index === -1) continue;
    const value = normaliseAttributeValue(key, row.value);
    if (!value) continue;
    // First writer wins: the order above already encodes which source is
    // authoritative for a given attribute.
    if (!byKey.has(key)) byKey.set(key, { key, value, provider });
  }

  return [...byKey.values()].sort((a, b) => attributeOrder.indexOf(a.key) - attributeOrder.indexOf(b.key));
}

function normaliseAttributeValue(key: string, value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return '';
  if (key === 'broadcast-day') return weekdayLabels[trimmed.toLowerCase()] ?? trimmed;
  if (key === 'status') {
    const status = trimmed.toLowerCase().replace(/\s+/gu, '_');
    if (['releasing', 'currently_airing', 'airing'].includes(status)) return 'airing';
    if (['finished', 'finished_airing'].includes(status)) return 'finished';
    if (['not_yet_aired', 'not_yet_released', 'upcoming'].includes(status)) return 'upcoming';
  }
  if (key === 'type' || key === 'format') return trimmed.toLowerCase();
  if (key === 'season') return trimmed.toLowerCase();
  return trimmed;
}

/** Attribute key -> i18n label key. */
export const attributeLabelKeys: Record<string, MessageKey> = {
  type: 'subject.attrType',
  format: 'subject.attrFormat',
  episodes: 'subject.attrEpisodes',
  'release-date': 'subject.attrReleaseDate',
  'end-date': 'subject.attrEndDate',
  'broadcast-day': 'subject.attrBroadcastDay',
  'broadcast-time': 'subject.attrBroadcastTime',
  'broadcast-timezone': 'subject.attrBroadcastTimezone',
  season: 'subject.attrSeason',
  status: 'subject.attrStatus',
};

const weekdayValueKeys: Record<string, MessageKey> = {
  mon: 'subject.weekdayMon',
  tue: 'subject.weekdayTue',
  wed: 'subject.weekdayWed',
  thu: 'subject.weekdayThu',
  fri: 'subject.weekdayFri',
  sat: 'subject.weekdaySat',
  sun: 'subject.weekdaySun',
};

const statusValueKeys: Record<string, MessageKey> = {
  airing: 'subject.statusAiring',
  finished: 'subject.statusFinished',
  upcoming: 'subject.statusUpcoming',
};

const seasonValueKeys: Record<string, MessageKey> = {
  winter: 'subject.seasonWinter',
  spring: 'subject.seasonSpring',
  summer: 'subject.seasonSummer',
  fall: 'subject.seasonFall',
};

/** Translated value for a normalised attribute, when the vocabulary is known. */
export function attributeValueKey(key: string, value: string): MessageKey | null {
  if (key === 'broadcast-day') return weekdayValueKeys[value] ?? null;
  if (key === 'status') return statusValueKeys[value] ?? null;
  if (key === 'season') return seasonValueKeys[value] ?? null;
  return null;
}

export function groupStaffByRole(staff: SubjectStaff[]) {
  const groups = new Map<string, SubjectStaff[]>();

  for (const item of staff) {
    const role = item.role?.trim() || 'Staff';
    groups.set(role, [...(groups.get(role) ?? []), item]);
  }

  return [...groups.entries()].sort(([roleA], [roleB]) => {
    const aIndex = importantStaffRoles.findIndex((role) => roleA.toLowerCase().includes(role.toLowerCase()));
    const bIndex = importantStaffRoles.findIndex((role) => roleB.toLowerCase().includes(role.toLowerCase()));
    return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex) || roleA.localeCompare(roleB);
  });
}

function relationSortWeight(relation: SubjectRelation) {
  const label = relation.relation.toLowerCase();
  if (label.includes('前') || label.includes('prequel')) return 0;
  if (label.includes('续') || label.includes('続') || label.includes('sequel')) return 1;
  if (label.includes('主') || label.includes('main')) return 2;
  if (label.includes('改编') || label.includes('adapt')) return 3;
  if (label.includes('外传') || label.includes('番外') || label.includes('side') || label.includes('spin')) return 4;
  return 20;
}

function relationSubjectTypeWeight(relation: SubjectRelation) {
  if (relation.subject.subject_type === 'anime') return 0;
  if (relation.subject.subject_type === 'galgame') return 1;
  return 2;
}

export function isPrimaryRelation(relation: SubjectRelation) {
  return relation.subject.subject_type === 'anime' || relation.subject.subject_type === 'galgame';
}

export function relationTitle(relation: SubjectRelation, fallback = 'Untitled') {
  return relation.subject.display_title || relation.subject.title || relation.subject.title_cn || fallback;
}

export function groupRelationsForDisplay(relations: SubjectRelation[], fallback: string): RelationDisplayGroup[] {
  const groups = new Map<string, RelationDisplayGroup>();

  for (const relation of relations) {
    // Episodes are part of the work, not a related work: they already have
    // their own section, and repeating all twelve here buried the real
    // relations under a second episode list.
    if (relation.subject.subject_type === 'episode') continue;
    const label = relation.relation.trim() || fallback;
    const tier = isPrimaryRelation(relation) ? 'primary' : 'other';
    const key = `${tier}:${label}`;
    const current = groups.get(key);
    groups.set(key, {
      key,
      label,
      tier,
      items: [...(current?.items ?? []), relation],
      totalCount: (current?.totalCount ?? 0) + 1,
    });
  }

  return [...groups.values()]
    .map((group) => ({
      ...group,
      items: [...group.items].sort(
        (a, b) =>
          relationSubjectTypeWeight(a) - relationSubjectTypeWeight(b) ||
          relationTitle(a).localeCompare(relationTitle(b)),
      ),
    }))
    .sort((a, b) => {
      const aRelation = a.items[0];
      const bRelation = b.items[0];
      return (
        (a.tier === 'primary' ? 0 : 1) - (b.tier === 'primary' ? 0 : 1) ||
        (aRelation ? relationSortWeight(aRelation) : Number.POSITIVE_INFINITY) -
          (bRelation ? relationSortWeight(bRelation) : Number.POSITIVE_INFINITY) ||
        a.label.localeCompare(b.label)
      );
    });
}

export function paginateRelationGroups(groups: RelationDisplayGroup[]) {
  const pages: RelationDisplayGroup[][] = [];
  let currentPage: RelationDisplayGroup[] = [];
  let currentCost = 0;

  for (const group of groups) {
    for (let index = 0; index < group.items.length; index += relationChunkSize) {
      const items = group.items.slice(index, index + relationChunkSize);
      const chunk = { ...group, key: `${group.key}:${index}`, items };
      const cost = 1 + Math.ceil(items.length / 3);

      if (currentPage.length > 0 && currentCost + cost > relationVisualPageBudget) {
        pages.push(currentPage);
        currentPage = [];
        currentCost = 0;
      }

      currentPage.push(chunk);
      currentCost += cost;
    }
  }

  if (currentPage.length > 0) pages.push(currentPage);
  return pages.length ? pages : [[]];
}

export function posterOf(subject: SubjectDetail) {
  return (
    subject.images?.original ||
    subject.image_original ||
    subject.images?.poster ||
    subject.image_thumbnail ||
    subject.image ||
    coverPlaceholder
  );
}

export function relationMeta(relation: SubjectRelation, fallback: string) {
  const subject = relation.subject;
  const displayMeta = Array.isArray(subject.display_meta) ? subject.display_meta.filter(Boolean) : [];
  const contentMeta = [
    subject.content?.episodes ? `${subject.content.episodes} EP` : '',
    subject.content?.volumes ? `${subject.content.volumes} Vol` : '',
  ].filter(Boolean);
  return (
    [...displayMeta, subject.display_subtitle, subject.date, subject.platform, ...contentMeta]
      .filter(Boolean)
      .join(' · ') || fallback
  );
}

export function subjectImage(subject: SubjectRelation['subject']) {
  return subject.images?.poster || subject.image_thumbnail || subject.image || coverPlaceholder;
}

export function episodeMeta(episode: SubjectEpisode, fallback: string) {
  return (
    [episode.date, episode.duration, episode.sort !== null ? `sort ${episode.sort}` : ''].filter(Boolean).join(' · ') ||
    fallback
  );
}
