import { queryOptions } from '@tanstack/react-query';
import { indexApi, type SubjectListQuery } from '@/features/subjects/api';
import type { UUID, WeekdayEn } from '@/lib/api/types';

export const subjectQueryKeys = {
  all: ['subjects'] as const,
  lists: () => [...subjectQueryKeys.all, 'list'] as const,
  list: (query: SubjectListQuery) => [...subjectQueryKeys.lists(), query] as const,
  details: () => [...subjectQueryKeys.all, 'detail'] as const,
  detail: (subjectId: UUID) => [...subjectQueryKeys.details(), subjectId] as const,
  episodes: (subjectId: UUID) => [...subjectQueryKeys.detail(subjectId), 'episodes'] as const,
  relations: (subjectId: UUID) => [...subjectQueryKeys.detail(subjectId), 'relations'] as const,
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

  episodes: (subjectId: UUID) =>
    queryOptions({
      queryKey: subjectQueryKeys.episodes(subjectId),
      queryFn: () => indexApi.listSubjectEpisodes(subjectId),
    }),

  relations: (subjectId: UUID) =>
    queryOptions({
      queryKey: subjectQueryKeys.relations(subjectId),
      queryFn: () => indexApi.listSubjectRelations(subjectId),
    }),

  calendar: (weekday?: WeekdayEn) =>
    queryOptions({
      queryKey: subjectQueryKeys.calendar(weekday),
      queryFn: () => indexApi.getCalendar(weekday ? { weekday_en: weekday } : undefined),
    }),
};
