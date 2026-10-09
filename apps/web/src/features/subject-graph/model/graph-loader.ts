import { indexApi } from '@/entities/subject';
import {
  collectApiPages,
  type SubjectCharacter,
  type SubjectEpisode,
  type SubjectRelation,
  type SubjectStaff,
  type UUID,
} from '@/shared/api';
import type { GraphMode, GraphSections } from './graph';

export type GraphPayload = {
  episodes: SubjectEpisode[];
  staff: SubjectStaff[];
  characters: SubjectCharacter[];
  relations: SubjectRelation[];
};

const maxCompleteGraphPages = 20;

export async function loadGraphPayload(
  subjectId: UUID,
  mode: GraphMode,
  sections: GraphSections,
  signal: AbortSignal,
): Promise<GraphPayload> {
  const pageSize = mode === 'complete' ? 96 : 64;
  const maxPages = mode === 'complete' ? maxCompleteGraphPages : 1;
  const [episodes, staff, characters, relations] = await Promise.all([
    sections.episodes
      ? collectApiPages((query) => indexApi.listSubjectEpisodes(subjectId, query, { signal }), {
          pageSize,
          maxPages,
          signal,
        })
      : Promise.resolve([]),
    sections.staff
      ? collectApiPages((query) => indexApi.listSubjectStaff(subjectId, query, { signal }), {
          pageSize: Math.min(pageSize, 64),
          maxPages,
          signal,
        })
      : Promise.resolve([]),
    sections.characters
      ? collectApiPages((query) => indexApi.listSubjectCharacters(subjectId, query, { signal }), {
          pageSize: Math.min(pageSize, 64),
          maxPages,
          signal,
        })
      : Promise.resolve([]),
    sections.relations
      ? collectApiPages((query) => indexApi.listSubjectRelations(subjectId, query, { signal }), {
          pageSize: Math.min(pageSize, 64),
          maxPages,
          signal,
        })
      : Promise.resolve([]),
  ]);

  return { episodes, staff, characters, relations };
}
