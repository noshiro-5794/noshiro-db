import {
  api,
  decodeApiPage,
  decodeCalendarEventsToGroups,
  decodeSubjectCharacter,
  decodeSubjectDetail,
  decodeSubjectEpisode,
  decodeSubjectRelation,
  decodeSubjectStaff,
  decodeSubjectStaffRoles,
  decodeSubjectSummary,
  encodePath,
} from '@/shared/api';
import type {
  ApiPage,
  ApiRequestContext,
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
} from '@/shared/api';

export type SubjectListQuery = PageQuery & {
  query?: string;
  scope?: string;
  collection?: string;
  keyword?: string;
  source_id?: string;
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

type BangumiSubjectSnapshot = {
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

class BangumiApiError extends Error {
  readonly kind: 'invalid-request' | 'network' | 'timeout' | 'http' | 'invalid-response';
  readonly status: number | null;

  constructor(
    message: string,
    options: {
      kind: BangumiApiError['kind'];
      status?: number;
      cause?: unknown;
    },
  ) {
    super(message, options.cause === undefined ? undefined : { cause: options.cause });
    this.name = 'BangumiApiError';
    this.kind = options.kind;
    this.status = options.status ?? null;
  }
}

const BANGUMI_REQUEST_TIMEOUT_MS = 8_000;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isFiniteNumber(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value);
}

function hasOptionalFiniteNumber(record: Record<string, unknown>, key: string, nullable = false) {
  const value = record[key];
  return value === undefined || (nullable && value === null) || isFiniteNumber(value);
}

function hasOptionalString(record: Record<string, unknown>, key: string) {
  const value = record[key];
  return value === undefined || typeof value === 'string';
}

function isNumberMap(value: unknown) {
  return isRecord(value) && Object.values(value).every(isFiniteNumber);
}

function isBangumiRating(value: unknown) {
  if (value === undefined) return true;
  if (!isRecord(value)) return false;

  return (
    hasOptionalFiniteNumber(value, 'rank', true) &&
    hasOptionalFiniteNumber(value, 'total') &&
    hasOptionalFiniteNumber(value, 'score') &&
    (value['count'] === undefined || isNumberMap(value['count']))
  );
}

function isBangumiCollection(value: unknown) {
  if (value === undefined) return true;
  if (!isRecord(value)) return false;

  return ['doing', 'collect', 'wish', 'on_hold', 'dropped'].every((key) => hasOptionalFiniteNumber(value, key));
}

function isBangumiSubjectSnapshot(value: unknown, expectedId: number): value is BangumiSubjectSnapshot {
  return (
    isRecord(value) &&
    Number.isSafeInteger(value['id']) &&
    value['id'] === expectedId &&
    hasOptionalString(value, 'name') &&
    hasOptionalString(value, 'name_cn') &&
    hasOptionalFiniteNumber(value, 'rank', true) &&
    isBangumiRating(value['rating']) &&
    isBangumiCollection(value['collection'])
  );
}

function parseBangumiSubjectSnapshot(value: unknown, expectedId: number): BangumiSubjectSnapshot {
  if (!isBangumiSubjectSnapshot(value, expectedId)) {
    throw new BangumiApiError('Bangumi returned an invalid subject response', {
      kind: 'invalid-response',
    });
  }

  return value;
}

async function getBangumiSubject(subjectId: number, context: ApiRequestContext = {}) {
  if (!Number.isSafeInteger(subjectId) || subjectId <= 0) {
    throw new BangumiApiError('Bangumi subject ID must be a positive safe integer', {
      kind: 'invalid-request',
    });
  }

  const timeoutSignal = AbortSignal.timeout(BANGUMI_REQUEST_TIMEOUT_MS);
  const signal = context.signal ? AbortSignal.any([context.signal, timeoutSignal]) : timeoutSignal;
  let response: Response;

  try {
    response = await fetch(`https://api.bgm.tv/v0/entities/${encodeURIComponent(String(subjectId))}`, {
      headers: {
        Accept: 'application/json',
      },
      referrerPolicy: 'no-referrer',
      signal,
    });
  } catch (error) {
    if (context.signal?.aborted) {
      throw error;
    }

    if (timeoutSignal.aborted) {
      throw new BangumiApiError('Bangumi request timed out', {
        kind: 'timeout',
        cause: error,
      });
    }

    throw new BangumiApiError('Bangumi request failed', {
      kind: 'network',
      cause: error,
    });
  }

  if (!response.ok) {
    throw new BangumiApiError(`Bangumi request failed with status ${response.status}`, {
      kind: 'http',
      status: response.status,
    });
  }

  let payload: unknown;
  try {
    payload = JSON.parse(await response.text());
  } catch (error) {
    throw new BangumiApiError('Bangumi returned malformed JSON', {
      kind: 'invalid-response',
      cause: error,
    });
  }

  return parseBangumiSubjectSnapshot(payload, subjectId);
}

export const indexApi = {
  listSubjects: (query: SubjectListQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<SubjectSummary>>('/api/v1/index/entities/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeSubjectSummary),
      query: {
        ...(query.query === undefined ? {} : { query: query.query }),
        ...(query.keyword === undefined ? {} : { query: query.keyword }),
        ...(query.collection === undefined ? {} : { collection: query.collection }),
        ...(query.scope === undefined ? {} : { scope: query.scope }),
        ...(query.subject_type === undefined ? {} : { subject_type: query.subject_type }),
        ...(query.nsfw === undefined ? {} : { nsfw: query.nsfw }),
        ...(query.page === undefined ? {} : { page: query.page }),
        ...(query.page_size === undefined ? {} : { page_size: query.page_size }),
      },
    }),

  getSubject: (subjectId: UUID, context: ApiRequestContext = {}) =>
    api.get<SubjectDetail>(`/api/v1/index/entities/${encodePath(subjectId)}/`, {
      ...context,
      decode: decodeSubjectDetail,
    }),

  listSubjectEpisodes: (
    subjectId: UUID,
    query: SubjectEpisodeQuery = { page_size: 96 },
    context: ApiRequestContext = {},
  ) =>
    api.get<ApiPage<SubjectEpisode>>(`/api/v1/index/entities/${encodePath(subjectId)}/episodes/`, {
      ...context,
      decode: (value) => decodeApiPage(value, decodeSubjectEpisode),
      query,
    }),

  getSubjectEpisode: (subjectId: UUID, episodeId: string | number, context: ApiRequestContext = {}) =>
    indexApi
      .listSubjectEpisodes(subjectId, { page: 1, page_size: 100 }, context)
      .then((page) => page.results.find((episode) => episode.id === String(episodeId)) ?? null),

  listSubjectStaff: (subjectId: UUID, query: SubjectStaffQuery = {}, context: ApiRequestContext = {}) =>
    api
      .get<SubjectStaff[]>(`/api/v1/index/entities/${encodePath(subjectId)}/credits/`, {
        ...context,
        decode: (value) => {
          if (!Array.isArray(value)) throw new TypeError('Invalid entity credits response');
          return value.map(decodeSubjectStaff);
        },
      })
      .then((staff) => {
        const role = query.role;
        const filtered = role ? staff.filter((item) => item.role === role) : staff;
        const page = query.page ?? 1;
        const pageSize = query.page_size ?? (filtered.length || 1);
        const start = (page - 1) * pageSize;
        return {
          count: filtered.length,
          next: null,
          previous: null,
          results: filtered.slice(start, start + pageSize),
        };
      }),

  listSubjectStaffRoles: (subjectId: UUID, context: ApiRequestContext = {}) =>
    indexApi.listSubjectStaff(subjectId, { page: 1, page_size: 1_000 }, context).then((page) =>
      decodeSubjectStaffRoles({
        roles: [
          ...new Set(
            page.results
              .map((item) => item.role)
              .filter((role): role is string => typeof role === 'string' && Boolean(role)),
          ),
        ],
      }),
    ),

  listSubjectCharacters: (subjectId: UUID, query: PageQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<SubjectCharacter>>(`/api/v1/index/entities/${encodePath(subjectId)}/characters/`, {
      ...context,
      decode: (value) => decodeApiPage(value, decodeSubjectCharacter),
      query,
    }),

  listSubjectRelations: (subjectId: UUID, query: PageQuery = {}, context: ApiRequestContext = {}) =>
    api
      .get<SubjectRelation[]>(`/api/v1/index/entities/${encodePath(subjectId)}/relations/`, {
        ...context,
        decode: (value) => {
          if (!Array.isArray(value)) throw new TypeError('Invalid entity relations response');
          return value.map(decodeSubjectRelation);
        },
      })
      .then((relations) => {
        const page = query.page ?? 1;
        const pageSize = query.page_size ?? (relations.length || 1);
        const start = (page - 1) * pageSize;
        return {
          count: relations.length,
          next: null,
          previous: null,
          results: relations.slice(start, start + pageSize),
        };
      }),

  getCalendar: (_query: { weekday_en?: WeekdayEn } = {}, context: ApiRequestContext = {}) => {
    void _query;
    return api.get<CalendarGroup[]>('/api/v1/index/calendar/events/', {
      ...context,
      decode: decodeCalendarEventsToGroups,
      query: { include_work: true },
    });
  },

  getBangumiSubject,
};
