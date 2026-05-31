import { api } from '@/lib/api/client';
import { encodePath } from '@/lib/api/path';
import type {
  ApiPage,
  CalendarGroup,
  PageQuery,
  PrimarySubjectType,
  SubjectCharacter,
  SubjectDetail,
  SubjectEpisode,
  SubjectRelationList,
  SubjectStaff,
  SubjectSummary,
  UUID,
  WeekdayEn,
} from '@/lib/api/types';

export type SubjectListQuery = PageQuery & {
  keyword?: string;
  subject_type?: PrimarySubjectType;
  nsfw?: boolean;
  year?: number;
  season?: 'winter' | 'spring' | 'summer' | 'fall';
  platform?: string;
  date_from?: string;
  date_to?: string;
  episodes_min?: number;
  episodes_max?: number;
  ordering?: 'date' | '-date' | 'title' | '-title' | 'updated_at' | '-updated_at' | 'created_at' | '-created_at';
};

export type SubjectOrdering = NonNullable<SubjectListQuery['ordering']>;

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
    api.get<SubjectRelationList>(`/api/index/subjects/${encodePath(subjectId)}/relations/`),

  getCalendar: (query: { weekday_en?: WeekdayEn } = {}) => api.get<CalendarGroup[]>('/api/index/calendar/', { query }),
};
