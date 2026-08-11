import { describe, expect, it } from 'vitest';
import type { SubjectDetail, SubjectRelation } from '@/shared/api';
import { formatDate } from '@/shared/lib/date';
import {
  bangumiSubjectIdOf,
  formatUnknownValue,
  getInfoboxRows,
  groupRelationsForDisplay,
  paginateRelationGroups,
} from './subject-detail';

function subject(sourceId: string | number | undefined): SubjectDetail {
  return {
    id: 'subject-1',
    title: 'Subject',
    title_cn: null,
    subject_type: 'anime',
    date: null,
    platform: null,
    nsfw: false,
    episode_count: 0,
    staff_count: 0,
    character_count: 0,
    ...(sourceId === undefined ? {} : { source_id: sourceId }),
  };
}

function relation(id: string, label: string, type = 'anime'): SubjectRelation {
  return {
    relation: label,
    subject: {
      id,
      title: id,
      title_cn: null,
      subject_type: type,
      date: null,
      platform: null,
      nsfw: false,
    },
  };
}

describe('subject detail model', () => {
  it('accepts only positive safe Bangumi IDs', () => {
    expect(bangumiSubjectIdOf(subject('4255'))).toBe(4255);
    expect(bangumiSubjectIdOf(subject(4255))).toBe(4255);
    expect(bangumiSubjectIdOf(subject('12.5'))).toBeNull();
    expect(bangumiSubjectIdOf(subject(-1))).toBeNull();
    expect(bangumiSubjectIdOf(subject(Number.MAX_SAFE_INTEGER + 1))).toBeNull();
  });

  it('does not throw for malformed dates', () => {
    expect(formatDate('not-a-date')).toBe('');
    expect(formatDate()).toBe('');
  });

  it('normalizes infobox rows and safely stops circular unknown values', () => {
    expect(getInfoboxRows([{ key: ' Platform ', value: ['TV', { name: 'Web' }] }, null])).toEqual([
      { key: 'Platform', value: 'TV / Web' },
    ]);
    const circular: Record<string, unknown> = { name: 'value' };
    circular['self'] = circular;
    expect(formatUnknownValue(circular)).toBe('name: value');
  });

  it('groups primary relations first and chunks large groups without dropping items', () => {
    const relations = [
      relation('other', 'adaptation', 'book'),
      ...Array.from({ length: 11 }, (_, index) => relation(`sequel-${index}`, 'sequel')),
      relation('prequel', 'prequel'),
    ];
    const groups = groupRelationsForDisplay(relations, 'Related');
    const pages = paginateRelationGroups(groups);

    expect(groups[0]?.label).toBe('prequel');
    expect(groups.at(-1)?.tier).toBe('other');
    expect(pages.flatMap((page) => page).flatMap((group) => group.items)).toHaveLength(relations.length);
    expect(pages.flatMap((page) => page).every((group) => group.items.length <= 9)).toBe(true);
  });
});
