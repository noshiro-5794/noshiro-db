import { env } from '@/shared/config/env';

export const API_BASE_URL = env.apiBaseUrl;

type QueryPrimitive = string | number | boolean;
export type QueryParams = Record<string, QueryPrimitive | QueryPrimitive[] | null | undefined>;
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export type ApiEnvelope<T> = {
  code: number;
  message: string;
  data: T;
};

export type ApiRequestOptions<TBody = unknown> = Omit<RequestInit, 'body' | 'method'> & {
  method?: HttpMethod;
  query?: QueryParams;
  body?: TBody;
  skipAuth?: boolean;
  retryOnUnauthorized?: boolean;
};

let accessToken: string | null = null;
let accessTokenRefresher: (() => Promise<string>) | null = null;
let sessionExpiredHandler: (() => void) | null = null;
let pendingRefresh: Promise<string> | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
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
  status: number;
  code: number;
  data: unknown;
  url: string;

  constructor(message: string, options: { status: number; code: number; data: unknown; url: string }) {
    super(message);
    this.name = 'ApiError';
    this.status = options.status;
    this.code = options.code;
    this.data = options.data;
    this.url = options.url;
  }
}

function parseEnvelope<TData>(text: string) {
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text) as ApiEnvelope<TData>;
  } catch {
    return null;
  }
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

function buildUrl(path: string, query?: QueryParams) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const url = /^https?:\/\//u.test(path) ? path : `${API_BASE_URL}${normalizedPath}`;
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

async function refreshAccessTokenOnce() {
  if (!accessTokenRefresher) {
    throw new Error('Access token refresher is not registered');
  }

  pendingRefresh ??= accessTokenRefresher().finally(() => {
    pendingRefresh = null;
  });

  const nextAccessToken = await pendingRefresh;
  setAccessToken(nextAccessToken);
  return nextAccessToken;
}

export async function apiRequest<TData, TBody = unknown>(path: string, options: ApiRequestOptions<TBody> = {}) {
  const { body, query, skipAuth = false, retryOnUnauthorized = true, ...requestInit } = options;
  const url = buildUrl(path, query);
  const headers = new Headers(requestInit.headers);

  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }

  if (!skipAuth && accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }

  const response = await fetch(url, {
    ...requestInit,
    body: createRequestBody(body, headers),
    headers,
    credentials: requestInit.credentials ?? 'include',
  });

  const responseText = await response.text();
  const payload = parseEnvelope<TData>(responseText);

  if (response.status === 204) {
    return null as TData;
  }

  if (!response.ok || !payload || payload.code !== 0) {
    if (response.status === 401 && !skipAuth && retryOnUnauthorized && accessTokenRefresher) {
      try {
        await refreshAccessTokenOnce();
        return apiRequest<TData, TBody>(path, {
          ...options,
          retryOnUnauthorized: false,
        });
      } catch {
        setAccessToken(null);
        sessionExpiredHandler?.();
      }
    }

    throw new ApiError((payload?.message ?? response.statusText) || 'Request failed', {
      status: response.status,
      code: payload?.code ?? -1,
      data: payload?.data ?? (responseText.slice(0, 1600) || null),
      url,
    });
  }

  return payload.data;
}

export const api = {
  get: <TData>(path: string, options?: Omit<ApiRequestOptions, 'method' | 'body'>) =>
    apiRequest<TData>(path, { ...options, method: 'GET' }),

  post: <TData, TBody = unknown>(
    path: string,
    body?: TBody,
    options?: Omit<ApiRequestOptions<TBody>, 'method' | 'body'>,
  ) => apiRequest<TData, TBody>(path, { ...options, method: 'POST', body }),

  put: <TData, TBody = unknown>(
    path: string,
    body?: TBody,
    options?: Omit<ApiRequestOptions<TBody>, 'method' | 'body'>,
  ) => apiRequest<TData, TBody>(path, { ...options, method: 'PUT', body }),

  patch: <TData, TBody = unknown>(
    path: string,
    body?: TBody,
    options?: Omit<ApiRequestOptions<TBody>, 'method' | 'body'>,
  ) => apiRequest<TData, TBody>(path, { ...options, method: 'PATCH', body }),

  delete: <TData>(path: string, options?: Omit<ApiRequestOptions, 'method' | 'body'>) =>
    apiRequest<TData>(path, { ...options, method: 'DELETE' }),
};
