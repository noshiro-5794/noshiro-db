import { placeholderImagePaths } from '@/shared/assets/public-assets';
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

export function metaOf(subject: SubjectDetail) {
  return [subject.subject_type, subject.platform, subject.date].filter(Boolean).join(' · ');
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
