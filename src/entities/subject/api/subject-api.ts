import {
  api,
  decodeApiPage,
  decodeCalendarGroups,
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
    response = await fetch(`https://api.bgm.tv/v0/subjects/${encodeURIComponent(String(subjectId))}`, {
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
    api.get<ApiPage<SubjectSummary>>('/api/index/subjects/', {
      ...context,
      decode: (value) => decodeApiPage(value, decodeSubjectSummary),
      query,
    }),

  getSubject: (subjectId: UUID, context: ApiRequestContext = {}) =>
    api.get<SubjectDetail>(`/api/index/subjects/${encodePath(subjectId)}/`, {
      ...context,
      decode: decodeSubjectDetail,
    }),

  listSubjectEpisodes: (
    subjectId: UUID,
    query: SubjectEpisodeQuery = { page_size: 96 },
    context: ApiRequestContext = {},
  ) =>
    api.get<ApiPage<SubjectEpisode>>(`/api/index/subjects/${encodePath(subjectId)}/episodes/`, {
      ...context,
      decode: (value) => decodeApiPage(value, decodeSubjectEpisode),
      query,
    }),

  getSubjectEpisode: (subjectId: UUID, episodeId: number, context: ApiRequestContext = {}) =>
    api.get<SubjectEpisode>(`/api/index/subjects/${encodePath(subjectId)}/episodes/${encodePath(episodeId)}/`, {
      ...context,
      decode: decodeSubjectEpisode,
    }),

  listSubjectStaff: (subjectId: UUID, query: SubjectStaffQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<SubjectStaff>>(`/api/index/subjects/${encodePath(subjectId)}/staff/`, {
      ...context,
      decode: (value) => decodeApiPage(value, decodeSubjectStaff),
      query,
    }),

  listSubjectStaffRoles: (subjectId: UUID, context: ApiRequestContext = {}) =>
    api.get<{ roles: string[] }>(`/api/index/subjects/${encodePath(subjectId)}/staff/roles/`, {
      ...context,
      decode: decodeSubjectStaffRoles,
    }),

  listSubjectCharacters: (subjectId: UUID, query: PageQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<SubjectCharacter>>(`/api/index/subjects/${encodePath(subjectId)}/characters/`, {
      ...context,
      decode: (value) => decodeApiPage(value, decodeSubjectCharacter),
      query,
    }),

  listSubjectRelations: (subjectId: UUID, query: PageQuery = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<SubjectRelation>>(`/api/index/subjects/${encodePath(subjectId)}/relations/`, {
      ...context,
      decode: (value) => decodeApiPage(value, decodeSubjectRelation),
      query,
    }),

  getCalendar: (query: { weekday_en?: WeekdayEn } = {}, context: ApiRequestContext = {}) =>
    api.get<CalendarGroup[]>('/api/index/calendar/', { ...context, decode: decodeCalendarGroups, query }),

  getBangumiSubject,
};
