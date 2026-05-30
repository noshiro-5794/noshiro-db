import { api } from '@/lib/api/client';
import { encodePath } from '@/lib/api/path';
import type {
  ApiPage,
  CalendarEntry,
  PageQuery,
  PrimarySubjectType,
  SubjectCharacter,
  SubjectDetail,
  SubjectEpisode,
  SubjectRelation,
  SubjectStaff,
  SubjectSummary,
  UUID,
  WeekdayEn,
} from '@/lib/api/types';

export type SubjectListQuery = PageQuery & {
  keyword?: string;
  subject_type?: PrimarySubjectType;
  nsfw?: boolean;
  ordering?: 'date' | '-date' | 'title' | '-title' | 'updated_at' | '-updated_at' | 'created_at' | '-created_at';
};

export const indexApi = {
  listSubjects: (query: SubjectListQuery = {}) => api.get<ApiPage<SubjectSummary>>('/api/index/subjects/', { query }),

  getSubject: (subjectId: UUID) => api.get<SubjectDetail>(`/api/index/subjects/${encodePath(subjectId)}/`),

  listSubjectEpisodes: (subjectId: UUID, query: PageQuery = { page_size: 96 }) =>
    api.get<ApiPage<SubjectEpisode>>(`/api/index/subjects/${encodePath(subjectId)}/episodes/`, { query }),

  listSubjectStaff: (subjectId: UUID, query: PageQuery = {}) =>
    api.get<ApiPage<SubjectStaff>>(`/api/index/subjects/${encodePath(subjectId)}/staff/`, { query }),

  listSubjectCharacters: (subjectId: UUID, query: PageQuery = {}) =>
    api.get<ApiPage<SubjectCharacter>>(`/api/index/subjects/${encodePath(subjectId)}/characters/`, { query }),

  listSubjectRelations: (subjectId: UUID) =>
    api.get<SubjectRelation[]>(`/api/index/subjects/${encodePath(subjectId)}/relations/`),

  getCalendar: (query: { weekday_en?: WeekdayEn } = {}) => api.get<CalendarEntry[]>('/api/index/calendar/', { query }),
};
