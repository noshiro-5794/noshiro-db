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

export type SubjectStaffQuery = PageQuery & {
  role?: string;
};

export type SubjectEpisodeQuery = PageQuery & {
  type?: string;
};

export type BangumiSubjectSnapshot = {
  id: number;
  name?: string;
  name_cn?: string;
  rank?: number | null;
  rating?: {
    rank?: number | null;
    total?: number;
    score?: number;
    count?: Record<string, number>;
  };
  collection?: {
    doing?: number;
    collect?: number;
    wish?: number;
    on_hold?: number;
    dropped?: number;
  };
};

async function getBangumiSubject(subjectId: number) {
  const response = await fetch(`https://api.bgm.tv/v0/subjects/${encodeURIComponent(String(subjectId))}`, {
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Bangumi request failed: ${response.status}`);
  }

  return response.json() as Promise<BangumiSubjectSnapshot>;
}

export const indexApi = {
  listSubjects: (query: SubjectListQuery = {}) => api.get<ApiPage<SubjectSummary>>('/api/index/subjects/', { query }),

  getSubject: (subjectId: UUID) => api.get<SubjectDetail>(`/api/index/subjects/${encodePath(subjectId)}/`),

  listSubjectEpisodes: (subjectId: UUID, query: SubjectEpisodeQuery = { page_size: 96 }) =>
    api.get<ApiPage<SubjectEpisode>>(`/api/index/subjects/${encodePath(subjectId)}/episodes/`, { query }),

  getSubjectEpisode: (subjectId: UUID, episodeId: number) =>
    api.get<SubjectEpisode>(`/api/index/subjects/${encodePath(subjectId)}/episodes/${encodePath(episodeId)}/`),

  listSubjectStaff: (subjectId: UUID, query: SubjectStaffQuery = {}) =>
    api.get<ApiPage<SubjectStaff>>(`/api/index/subjects/${encodePath(subjectId)}/staff/`, { query }),

  listSubjectStaffRoles: (subjectId: UUID) =>
    api.get<{ roles: string[] }>(`/api/index/subjects/${encodePath(subjectId)}/staff/roles/`),

  listSubjectCharacters: (subjectId: UUID, query: PageQuery = {}) =>
    api.get<ApiPage<SubjectCharacter>>(`/api/index/subjects/${encodePath(subjectId)}/characters/`, { query }),

  listSubjectRelations: (subjectId: UUID, query: PageQuery = {}) =>
    api.get<ApiPage<SubjectRelation>>(`/api/index/subjects/${encodePath(subjectId)}/relations/`, { query }),

  getCalendar: (query: { weekday_en?: WeekdayEn } = {}) => api.get<CalendarGroup[]>('/api/index/calendar/', { query }),

  getBangumiSubject,
};
