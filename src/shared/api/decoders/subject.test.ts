import { describe, expect, it } from 'vitest';
import {
  decodeCalendarGroups,
  decodeSubjectDetail,
  decodeSubjectEpisode,
  decodeSubjectRelation,
  decodeSubjectStaffRoles,
} from './subject';

const entity = {
  id: '01980f00-0000-7000-8000-000000000001',
  entity_type: 'work',
  lifecycle: 'active',
  audience: 'general',
  work_type: 'anime',
  display_name: 'Subject',
  collections: [],
  media: [],
};

const detail = {
  ...entity,
  names: [],
  descriptions: [],
  facts: [],
  external_links: [],
  content_ratings: [],
  sources: [],
};

describe('subject response decoders', () => {
  it('validates detail and episode identifiers', () => {
    expect(decodeSubjectDetail(detail)).toMatchObject({ id: entity.id });
    expect(() => decodeSubjectDetail({ ...detail, id: '' })).toThrow(TypeError);
    expect(
      decodeSubjectEpisode({
        id: '1',
        title: 'Episode',
        title_cn: '',
        type: 'EP',
        number: '1',
        sort: '1',
        disc: 0,
        duration: '',
        raw_duration: '',
        air_date: '',
        comment_count: 0,
        description: '',
        provenance: null,
      }),
    ).toMatchObject({ id: '1', ep_num: 1 });
  });

  it('validates relation and staff role lists', () => {
    expect(decodeSubjectRelation({ relation_type: 'sequel', target: entity, qualifiers: {}, evidence: [] })).toMatchObject(
      { relation: 'sequel' },
    );
    expect(() => decodeSubjectRelation({ relation_type: 1, target: entity })).toThrow(TypeError);
    expect(decodeSubjectStaffRoles({ roles: ['director', 'writer'] })).toEqual({ roles: ['director', 'writer'] });
  });

  it('validates calendar events and weekday consistency', () => {
    const event = {
      id: 1,
      work_id: entity.id,
      episode_id: null,
      starts_at: '2026-07-29T00:00:00Z',
      timezone: 'UTC',
      region: 'JP',
      weekday: 1,
      precision: 'day',
      raw_value: 'Subject',
      provenance: null,
    };
    expect(decodeCalendarGroups([event])).toHaveLength(7);
    expect(() => decodeCalendarGroups([{ ...event, weekday: 8 }])).toThrow(TypeError);
  });
});
