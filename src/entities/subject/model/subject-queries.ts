import { queryOptions } from '@tanstack/react-query';
import { indexApi, type SubjectEpisodeQuery, type SubjectListQuery, type SubjectStaffQuery } from '../api/subject-api';
import { collectApiPages, type UUID, type WeekdayEn } from '@/shared/api';

const defaultPageSize = 64;
const episodePageSize = 96;

const subjectQueryKeys = {
  all: ['subjects'] as const,
  lists: () => [...subjectQueryKeys.all, 'list'] as const,
  list: (query: SubjectListQuery) => [...subjectQueryKeys.lists(), query] as const,
  details: () => [...subjectQueryKeys.all, 'detail'] as const,
  detail: (subjectId: UUID) => [...subjectQueryKeys.details(), subjectId] as const,
  episodes: (subjectId: UUID, query?: object) =>
    [...subjectQueryKeys.detail(subjectId), 'episodes', query ?? 'default'] as const,
  episode: (subjectId: UUID, episodeId: number) =>
    [...subjectQueryKeys.detail(subjectId), 'episodes', episodeId] as const,
  staff: (subjectId: UUID, query?: SubjectStaffQuery) =>
    [...subjectQueryKeys.detail(subjectId), 'staff', query ?? 'default'] as const,
  staffRoles: (subjectId: UUID) => [...subjectQueryKeys.detail(subjectId), 'staff', 'roles'] as const,
  characters: (subjectId: UUID, query?: object) =>
    [...subjectQueryKeys.detail(subjectId), 'characters', query ?? 'default'] as const,
  relations: (subjectId: UUID, query?: object) =>
    [...subjectQueryKeys.detail(subjectId), 'relations', query ?? 'default'] as const,
  allEpisodes: (subjectId: UUID) => [...subjectQueryKeys.episodes(subjectId), 'all'] as const,
  allRelations: (subjectId: UUID) => [...subjectQueryKeys.relations(subjectId), 'all'] as const,
  bangumiSnapshot: (bangumiSubjectId: number) => [...subjectQueryKeys.all, 'bangumi', bangumiSubjectId] as const,
  calendar: (weekday?: WeekdayEn) => ['calendar', weekday ?? 'all'] as const,
};

export const subjectQueries = {
  list: (query: SubjectListQuery) =>
    queryOptions({
      queryKey: subjectQueryKeys.list(query),
      queryFn: ({ signal }) => indexApi.listSubjects(query, { signal }),
    }),

  detail: (subjectId: UUID) =>
    queryOptions({
      queryKey: subjectQueryKeys.detail(subjectId),
      queryFn: ({ signal }) => indexApi.getSubject(subjectId, { signal }),
    }),

  episodes: (subjectId: UUID, query?: SubjectEpisodeQuery) =>
    queryOptions({
      queryKey: subjectQueryKeys.episodes(subjectId, query),
      queryFn: ({ signal }) => indexApi.listSubjectEpisodes(subjectId, query, { signal }),
    }),

  episode: (subjectId: UUID, episodeId: number) =>
    queryOptions({
      queryKey: subjectQueryKeys.episode(subjectId, episodeId),
      queryFn: ({ signal }) => indexApi.getSubjectEpisode(subjectId, episodeId, { signal }),
    }),

  allEpisodes: (subjectId: UUID) =>
    queryOptions({
      queryKey: subjectQueryKeys.allEpisodes(subjectId),
      queryFn: ({ signal }) =>
        collectApiPages((query) => indexApi.listSubjectEpisodes(subjectId, query, { signal }), {
          pageSize: episodePageSize,
          signal,
        }),
    }),

  staff: (subjectId: UUID, query?: SubjectStaffQuery) =>
    queryOptions({
      queryKey: subjectQueryKeys.staff(subjectId, query),
      queryFn: ({ signal }) => indexApi.listSubjectStaff(subjectId, query, { signal }),
    }),

  staffRoles: (subjectId: UUID) =>
    queryOptions({
      queryKey: subjectQueryKeys.staffRoles(subjectId),
      queryFn: ({ signal }) => indexApi.listSubjectStaffRoles(subjectId, { signal }),
    }),

  characters: (subjectId: UUID, query?: { page?: number; page_size?: number }) =>
    queryOptions({
      queryKey: subjectQueryKeys.characters(subjectId, query),
      queryFn: ({ signal }) => indexApi.listSubjectCharacters(subjectId, query, { signal }),
    }),

  relations: (subjectId: UUID, query?: { page?: number; page_size?: number }) =>
    queryOptions({
      queryKey: subjectQueryKeys.relations(subjectId, query),
      queryFn: ({ signal }) => indexApi.listSubjectRelations(subjectId, query, { signal }),
    }),

  allRelations: (subjectId: UUID) =>
    queryOptions({
      queryKey: subjectQueryKeys.allRelations(subjectId),
      queryFn: ({ signal }) =>
        collectApiPages((query) => indexApi.listSubjectRelations(subjectId, query, { signal }), {
          pageSize: defaultPageSize,
          signal,
        }),
    }),

  bangumiSnapshot: (bangumiSubjectId: number) =>
    queryOptions({
      queryKey: subjectQueryKeys.bangumiSnapshot(bangumiSubjectId),
      queryFn: ({ signal }) => indexApi.getBangumiSubject(bangumiSubjectId, { signal }),
      staleTime: 5 * 60 * 1000,
    }),

  calendar: (weekday?: WeekdayEn) =>
    queryOptions({
      queryKey: subjectQueryKeys.calendar(weekday),
      queryFn: ({ signal }) => indexApi.getCalendar(weekday ? { weekday_en: weekday } : {}, { signal }),
    }),
};
