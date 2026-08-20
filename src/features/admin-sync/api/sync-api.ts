import { api, decodeCursorPage, encodePath } from '@/shared/api';
import type { ApiRequestContext, CursorPage, ImportJob, ImportJobCreate } from '@/shared/api';
import { decodeImportJob } from './sync-decoders';

export const operationsApi = {
  listImportJobs: (
    query: { cursor?: string; page_size?: number; provider?: string; status?: string } = {},
    context: ApiRequestContext = {},
  ) =>
    api.get<CursorPage<ImportJob>>('/api/v1/operations/import-jobs/', {
      ...context,
      decode: (value) => decodeCursorPage(value, decodeImportJob),
      query,
    }),

  getImportJob: (jobId: string, context: ApiRequestContext = {}) =>
    api.get<ImportJob>(`/api/v1/operations/import-jobs/${encodePath(jobId)}/`, {
      ...context,
      decode: decodeImportJob,
    }),

  createImportJob: (body: ImportJobCreate) =>
    api.post<ImportJob, ImportJobCreate>('/api/v1/operations/import-jobs/', body, {
      decode: decodeImportJob,
    }),
};

export const syncApi = operationsApi;
