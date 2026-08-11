import { describe, expect, it } from 'vitest';
import type { SubjectCharacter, SubjectDetail, SubjectEpisode, SubjectRelation, SubjectStaff } from '@/shared/api';
import { buildGraph, defaultGraphSections, type GraphSections } from './graph';

const subject: SubjectDetail = {
  id: 'subject-1',
  title: 'Subject',
  title_cn: null,
  subject_type: 'anime',
  date: '2026-01-01',
  platform: 'TV',
  nsfw: false,
  episode_count: 1,
  staff_count: 1,
  character_count: 1,
  tags: ['science fiction', 'science fiction'],
};

const episode: SubjectEpisode = {
  id: 1,
  title: 'Episode 1',
  type: 'EP',
  ep_num: 1,
  sort: 1,
  date: null,
};

const staff: SubjectStaff = { id: 10, name: 'Actor' };
const character: SubjectCharacter = { id: 20, name: 'Character', role: 'Main', actors: [staff] };
const relation: SubjectRelation = {
  relation: 'sequel',
  subject: {
    id: 'subject-2',
    title: 'Related',
    title_cn: null,
    subject_type: 'anime',
    date: null,
    platform: null,
    nsfw: false,
  },
};

function graph(sections: GraphSections = defaultGraphSections) {
  return buildGraph({
    subject,
    episodes: [episode, episode],
    staff: [staff, staff],
    characters: [character, character],
    relations: [relation, relation],
    sections,
    fallback: 'Untitled',
  });
}

describe('buildGraph', () => {
  it('deduplicates repeated nodes and edges', () => {
    const result = graph();

    expect(result.nodes.map((node) => node.id)).toEqual([
      'subject:subject-1',
      'tag:science fiction',
      'meta:TV',
      'meta:2026-01-01',
      'meta:anime',
      'episode:1',
      'staff:10',
      'character:20',
      'relation:subject-2',
    ]);
    expect(new Set(result.edges.map((edge) => `${edge.source}:${edge.target}:${edge.label}`)).size).toBe(
      result.edges.length,
    );
  });

  it('links character actors to their character and subjects to their relations', () => {
    const result = graph();

    expect(result.edges).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ source: 'character:20', target: 'staff:10', label: 'voice' }),
        expect.objectContaining({ source: 'subject:subject-1', target: 'relation:subject-2', label: 'sequel' }),
      ]),
    );
  });

  it('honors every section switch even when stale payload data is present', () => {
    const result = graph({ episodes: false, staff: false, characters: false, relations: false, meta: false });

    expect(result.nodes).toEqual([expect.objectContaining({ id: 'subject:subject-1' })]);
    expect(result.edges).toEqual([]);
  });

  it('does not leak voice-actor nodes into a character-only graph', () => {
    const result = graph({ episodes: false, staff: false, characters: true, relations: false, meta: false });

    expect(result.nodes.map((node) => node.id)).toEqual(['subject:subject-1', 'character:20']);
  });

  it('caps extreme graphs while preserving high-value nodes and valid edges', () => {
    const episodes = Array.from({ length: 1_000 }, (_, index): SubjectEpisode => ({
      id: index + 1,
      title: `Episode ${index + 1}`,
      type: 'EP',
      ep_num: index + 1,
      sort: index + 1,
      date: null,
    }));
    const result = buildGraph({
      subject,
      episodes,
      staff: [staff],
      characters: [character],
      relations: [relation],
      sections: defaultGraphSections,
      fallback: 'Untitled',
    });
    const nodeIds = new Set(result.nodes.map((node) => node.id));

    expect(result.nodes).toHaveLength(900);
    expect(result.truncated).toBe(true);
    expect(nodeIds.has('subject:subject-1')).toBe(true);
    expect(nodeIds.has('relation:subject-2')).toBe(true);
    expect(nodeIds.has('character:20')).toBe(true);
    expect(result.edges.every((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))).toBe(true);
  });
});
