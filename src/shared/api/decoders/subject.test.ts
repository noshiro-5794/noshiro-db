import { describe, expect, it } from 'vitest';
import {
  decodeCalendarGroups,
  decodeSubjectDetail,
  decodeSubjectEpisode,
  decodeSubjectRelation,
  decodeSubjectStaffRoles,
} from './subject';

const subject = {
  id: '01980f00-0000-7000-8000-000000000001',
  title: 'Subject',
  title_cn: null,
  subject_type: 'anime',
  date: null,
  platform: null,
  nsfw: false,
};

describe('subject response decoders', () => {
  it('validates detail counters and episode identifiers', () => {
    expect(decodeSubjectDetail({ ...subject, episode_count: 12, staff_count: 3, character_count: 4 })).toMatchObject({
      episode_count: 12,
    });
    expect(() => decodeSubjectDetail({ ...subject, episode_count: -1, staff_count: 3, character_count: 4 })).toThrow(
      TypeError,
    );
    expect(decodeSubjectEpisode({ id: 1, title: 'Episode', type: 'EP', ep_num: 1, sort: 1, date: null })).toMatchObject(
      { id: 1 },
    );
  });

  it('validates relation direction and staff role lists', () => {
    expect(decodeSubjectRelation({ direction: 'outgoing', relation: 'sequel', subject })).toMatchObject({
      relation: 'sequel',
    });
    expect(() => decodeSubjectRelation({ direction: 'sideways', relation: 'sequel', subject })).toThrow(TypeError);
    expect(decodeSubjectStaffRoles({ roles: ['director', 'writer'] })).toEqual({ roles: ['director', 'writer'] });
  });

  it('validates calendar grouping and weekday consistency', () => {
    const item = {
      subject_id: subject.id,
      subject_type: 'anime',
      title: 'Subject',
      title_cn: null,
      image_thumbnail: null,
      platform: null,
      nsfw: false,
      weekday_en: 'Mon',
      doing: 3,
    };
    expect(decodeCalendarGroups([{ weekday: { id: 1, en: 'Mon' }, items: [item] }])).toHaveLength(1);
    expect(() => decodeCalendarGroups([{ weekday: { id: 8, en: 'Someday' }, items: [item] }])).toThrow(TypeError);
  });
});
