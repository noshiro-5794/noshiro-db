import { queryOptions } from '@tanstack/react-query';
import { indexApi, type SubjectEpisodeQuery, type SubjectListQuery, type SubjectStaffQuery } from '../api/subject-api';
import type { UUID, WeekdayEn } from '@/shared/api';

export const subjectQueryKeys = {
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
  bangumiSnapshot: (bangumiSubjectId: number) => [...subjectQueryKeys.all, 'bangumi', bangumiSubjectId] as const,
  calendar: (weekday?: WeekdayEn) => ['calendar', weekday ?? 'all'] as const,
};

export const subjectQueries = {
  list: (query: SubjectListQuery) =>
    queryOptions({
      queryKey: subjectQueryKeys.list(query),
      queryFn: () => indexApi.listSubjects(query),
    }),

  detail: (subjectId: UUID) =>
    queryOptions({
      queryKey: subjectQueryKeys.detail(subjectId),
      queryFn: () => indexApi.getSubject(subjectId),
    }),

  episodes: (subjectId: UUID, query?: SubjectEpisodeQuery) =>
    queryOptions({
      queryKey: subjectQueryKeys.episodes(subjectId, query),
      queryFn: () => indexApi.listSubjectEpisodes(subjectId, query),
    }),

  episode: (subjectId: UUID, episodeId: number) =>
    queryOptions({
      queryKey: subjectQueryKeys.episode(subjectId, episodeId),
      queryFn: () => indexApi.getSubjectEpisode(subjectId, episodeId),
    }),

  staff: (subjectId: UUID, query?: SubjectStaffQuery) =>
    queryOptions({
      queryKey: subjectQueryKeys.staff(subjectId, query),
      queryFn: () => indexApi.listSubjectStaff(subjectId, query),
    }),

  staffRoles: (subjectId: UUID) =>
    queryOptions({
      queryKey: subjectQueryKeys.staffRoles(subjectId),
      queryFn: () => indexApi.listSubjectStaffRoles(subjectId),
    }),

  characters: (subjectId: UUID, query?: { page?: number; page_size?: number }) =>
    queryOptions({
      queryKey: subjectQueryKeys.characters(subjectId, query),
      queryFn: () => indexApi.listSubjectCharacters(subjectId, query),
    }),

  relations: (subjectId: UUID, query?: { page?: number; page_size?: number }) =>
    queryOptions({
      queryKey: subjectQueryKeys.relations(subjectId, query),
      queryFn: () => indexApi.listSubjectRelations(subjectId, query),
    }),

  bangumiSnapshot: (bangumiSubjectId: number) =>
    queryOptions({
      queryKey: subjectQueryKeys.bangumiSnapshot(bangumiSubjectId),
      queryFn: () => indexApi.getBangumiSubject(bangumiSubjectId),
      staleTime: 5 * 60 * 1000,
    }),

  calendar: (weekday?: WeekdayEn) =>
    queryOptions({
      queryKey: subjectQueryKeys.calendar(weekday),
      queryFn: () => indexApi.getCalendar(weekday ? { weekday_en: weekday } : undefined),
    }),
};
