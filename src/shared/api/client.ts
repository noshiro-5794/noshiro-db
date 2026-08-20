import { env } from '@/shared/config/env';

export const API_BASE_URL = env.apiBaseUrl;

type QueryPrimitive = string | number | boolean;
export type QueryParams = Record<string, QueryPrimitive | QueryPrimitive[] | null | undefined>;
type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

type ApiEnvelope<T> = {
  code: number;
  message: string;
  data: T;
};

type ProblemDetails = {
  type?: string | undefined;
  title?: string | undefined;
  status?: number | undefined;
  detail?: string | undefined;
  instance?: string | undefined;
  trace_id?: string | undefined;
  code?: string | undefined;
  errors?: unknown;
};

type ApiResponseDecoder<TData> = (value: unknown) => TData;

export type ApiRequestOptions<TBody = unknown, TData = unknown> = Omit<RequestInit, 'body' | 'method'> & {
  method?: HttpMethod;
  query?: QueryParams;
  body?: TBody;
  decode?: ApiResponseDecoder<TData>;
  skipAuth?: boolean;
  retryOnUnauthorized?: boolean;
};

export type ApiRequestContext = Pick<RequestInit, 'signal'>;

let accessToken: string | null = null;
let accessTokenRevision = 0;
let accessTokenRefresher: (() => Promise<string>) | null = null;
let sessionExpiredHandler: (() => void) | null = null;
let pendingRefresh: Promise<string> | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
  accessTokenRevision += 1;
}

export function getAccessToken() {
  return accessToken;
}

export function setAccessTokenRefresher(refresher: (() => Promise<string>) | null) {
  accessTokenRefresher = refresher;
}

export function setSessionExpiredHandler(handler: (() => void) | null) {
  sessionExpiredHandler = handler;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string | number | null;
  readonly type: string | null;
  readonly title: string | null;
  readonly detail: string | null;
  readonly instance: string | null;
  readonly traceId: string | null;
  readonly errors: unknown;
  readonly data: unknown;
  readonly url: string;

  constructor(
    message: string,
    options: {
      status: number;
      code?: string | number | null;
      data?: unknown;
      url: string;
      type?: string | null;
      title?: string | null;
      detail?: string | null;
      instance?: string | null;
      traceId?: string | null;
      errors?: unknown;
    },
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = options.status;
    this.code = options.code ?? null;
    this.type = options.type ?? null;
    this.title = options.title ?? null;
    this.detail = options.detail ?? null;
    this.instance = options.instance ?? null;
    this.traceId = options.traceId ?? null;
    this.errors = options.errors;
    this.data = options.data;
    this.url = options.url;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function parseEnvelope(text: string): ApiEnvelope<unknown> | null {
  if (!text) {
    return null;
  }

  try {
    const value: unknown = JSON.parse(text);

    if (
      !isRecord(value) ||
      typeof value['code'] !== 'number' ||
      !Number.isFinite(value['code']) ||
      typeof value['message'] !== 'string' ||
      !Object.hasOwn(value, 'data')
    ) {
      return null;
    }

    return {
      code: value['code'],
      message: value['message'],
      data: value['data'],
    };
  } catch {
    return null;
  }
}

function parseProblemDetails(value: unknown): ProblemDetails | null {
  if (!isRecord(value) || typeof value['status'] !== 'number') {
    return null;
  }

  const optionalString = (key: string): string | undefined => {
    const candidate = value[key];
    return typeof candidate === 'string' ? candidate : undefined;
  };

  return {
    ...(optionalString('type') === undefined ? {} : { type: optionalString('type') }),
    ...(optionalString('title') === undefined ? {} : { title: optionalString('title') }),
    status: value['status'],
    ...(optionalString('detail') === undefined ? {} : { detail: optionalString('detail') }),
    ...(optionalString('instance') === undefined ? {} : { instance: optionalString('instance') }),
    ...(optionalString('trace_id') === undefined ? {} : { trace_id: optionalString('trace_id') }),
    ...(optionalString('code') === undefined ? {} : { code: optionalString('code') }),
    ...(value['errors'] === undefined ? {} : { errors: value['errors'] }),
  };
}

function parseSuccessPayload(text: string): { kind: 'empty' | 'payload'; data: unknown } | null {
  if (!text) return { kind: 'empty', data: null };

  try {
    const value: unknown = JSON.parse(text);
    if (isRecord(value) && typeof value['code'] === 'number' && typeof value['message'] === 'string' && Object.hasOwn(value, 'data')) {
      return { kind: 'payload', data: value['data'] };
    }
    return { kind: 'payload', data: value };
  } catch {
    return null;
  }
}

function errorPayload(text: string): {
  problem: ProblemDetails | null;
  legacy: ApiEnvelope<unknown> | null;
} {
  let value: unknown = null;
  try {
    value = text ? JSON.parse(text) : null;
  } catch {
    value = null;
  }

  return {
    problem: parseProblemDetails(value),
    legacy: parseEnvelope(text),
  };
}

function isBodyInit(value: unknown): value is BodyInit {
  return (
    value instanceof Blob ||
    value instanceof FormData ||
    value instanceof URLSearchParams ||
    value instanceof ArrayBuffer ||
    ArrayBuffer.isView(value)
  );
}

function toSearchParams(query?: QueryParams) {
  const params = new URLSearchParams();

  for (const [key, value] of Object.entries(query ?? {})) {
    if (value === null || value === undefined || value === '') {
      continue;
    }

    const values = Array.isArray(value) ? value : [value];
    for (const item of values) {
      params.append(key, String(item));
    }
  }

  return params;
}

function containsControlCharacter(value: string) {
  for (const character of value) {
    const codePoint = character.codePointAt(0);
    if (codePoint !== undefined && (codePoint <= 0x1f || codePoint === 0x7f)) {
      return true;
    }
  }

  return false;
}

function buildUrl(path: string, query?: QueryParams) {
  if (!path.startsWith('/') || path.startsWith('//') || path.includes('\\') || containsControlCharacter(path)) {
    throw new TypeError('API paths must be safe same-service absolute paths beginning with a single slash');
  }

  const url = `${API_BASE_URL}${path}`;
  const params = toSearchParams(query).toString();

  if (!params) {
    return url;
  }

  return `${url}${url.includes('?') ? '&' : '?'}${params}`;
}

function createRequestBody<TBody>(body: TBody | undefined, headers: Headers) {
  if (body === undefined || body === null) {
    return undefined;
  }

  if (isBodyInit(body)) {
    return body;
  }

  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  return JSON.stringify(body);
}

class SupersededTokenRefreshError extends Error {
  constructor() {
    super('The session changed while the access token was refreshing');
    this.name = 'SupersededTokenRefreshError';
  }
}

async function refreshAccessTokenOnce() {
  if (!accessTokenRefresher) {
    throw new Error('Access token refresher is not registered');
  }

  const refreshRevision = accessTokenRevision;
  pendingRefresh ??= accessTokenRefresher()
    .then((nextAccessToken) => {
      if (!nextAccessToken.trim()) {
        throw new Error('Access token refresher returned an empty token');
      }
      if (accessTokenRevision !== refreshRevision) {
        throw new SupersededTokenRefreshError();
      }

      setAccessToken(nextAccessToken);
      return nextAccessToken;
    })
    .catch((error: unknown) => {
      if (!(error instanceof SupersededTokenRefreshError)) {
        setAccessToken(null);
        sessionExpiredHandler?.();
      }
      throw error;
    })
    .finally(() => {
      pendingRefresh = null;
    });

  return pendingRefresh;
}

export async function apiRequest<TData, TBody = unknown>(path: string, options: ApiRequestOptions<TBody, TData> = {}) {
  const { body, decode, query, skipAuth = false, retryOnUnauthorized = true, ...requestInit } = options;
  const url = buildUrl(path, query);
  const headers = new Headers(requestInit.headers);

  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }

  const requestAccessToken = skipAuth ? null : accessToken;
  if (requestAccessToken) {
    headers.set('Authorization', `Bearer ${requestAccessToken}`);
  }

  const response = await fetch(url, {
    ...requestInit,
    body: createRequestBody(body, headers) ?? null,
    headers,
    credentials: requestInit.credentials ?? 'include',
  });

  const responseText = await response.text();
  const parsedSuccess = parseSuccessPayload(responseText);

  if (response.status === 204) {
    return null as TData;
  }

  if (!response.ok || parsedSuccess === null) {
    if (response.status === 401 && requestAccessToken && accessToken === requestAccessToken) {
      if (retryOnUnauthorized && accessTokenRefresher) {
        await refreshAccessTokenOnce();
        return apiRequest<TData, TBody>(path, {
          ...options,
          retryOnUnauthorized: false,
        });
      }

      if (!retryOnUnauthorized) {
        setAccessToken(null);
        sessionExpiredHandler?.();
      }
    }

    const { problem, legacy } = errorPayload(responseText);
    const data = problem ? null : legacy?.data ?? (responseText.slice(0, 1600) || null);
    const message =
      problem?.detail ||
      problem?.title ||
      legacy?.message ||
      response.statusText ||
      (response.ok ? 'Invalid API response' : 'Request failed');

    throw new ApiError(message, {
      status: response.status,
      code: problem?.code ?? legacy?.code ?? (problem ? null : -1),
      data,
      url,
      type: problem?.type ?? null,
      title: problem?.title ?? null,
      detail: problem?.detail ?? null,
      instance: problem?.instance ?? null,
      traceId: problem?.trace_id ?? null,
      errors: problem?.errors,
    });
  }

  const payloadData = parsedSuccess.kind === 'empty' ? null : parsedSuccess.data;

  if (!decode) return payloadData as TData;

  try {
    return decode(payloadData);
  } catch {
    throw new ApiError('Invalid API response data', {
      status: response.status,
      code: -1,
      data: null,
      url,
    });
  }
}

export const api = {
  get: <TData>(path: string, options?: Omit<ApiRequestOptions<unknown, TData>, 'method' | 'body'>) =>
    apiRequest<TData>(path, { ...options, method: 'GET' }),

  post: <TData, TBody = unknown>(
    path: string,
    body?: TBody,
    options?: Omit<ApiRequestOptions<TBody, TData>, 'method' | 'body'>,
  ) => apiRequest<TData, TBody>(path, { ...options, method: 'POST', ...(body === undefined ? {} : { body }) }),

  put: <TData, TBody = unknown>(
    path: string,
    body?: TBody,
    options?: Omit<ApiRequestOptions<TBody, TData>, 'method' | 'body'>,
  ) => apiRequest<TData, TBody>(path, { ...options, method: 'PUT', ...(body === undefined ? {} : { body }) }),

  patch: <TData, TBody = unknown>(
    path: string,
    body?: TBody,
    options?: Omit<ApiRequestOptions<TBody, TData>, 'method' | 'body'>,
  ) => apiRequest<TData, TBody>(path, { ...options, method: 'PATCH', ...(body === undefined ? {} : { body }) }),

  delete: <TData>(path: string, options?: Omit<ApiRequestOptions<unknown, TData>, 'method' | 'body'>) =>
    apiRequest<TData>(path, { ...options, method: 'DELETE' }),
};
