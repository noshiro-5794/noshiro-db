import { mutationOptions, queryOptions } from '@tanstack/react-query';
import { operationsApi } from '../api/sync-api';
import type { ImportJobCreate } from '@/shared/api';

export const syncQueryKeys = {
  all: ['sync'] as const,
  importJobs: () => [...syncQueryKeys.all, 'import-jobs'] as const,
  importJobList: (query: { cursor?: string; page_size?: number; provider?: string; status?: string } = {}) =>
    [...syncQueryKeys.importJobs(), 'list', query] as const,
  importJob: (jobId: string) => [...syncQueryKeys.importJobs(), 'detail', jobId] as const,
};

export const syncQueries = {
  importJobs: (query: { cursor?: string; page_size?: number; provider?: string; status?: string } = {}) =>
    queryOptions({
      queryKey: syncQueryKeys.importJobList(query),
      queryFn: ({ signal }) => operationsApi.listImportJobs(query, { signal }),
    }),

  importJob: (jobId: string) =>
    queryOptions({
      queryKey: syncQueryKeys.importJob(jobId),
      queryFn: ({ signal }) => operationsApi.getImportJob(jobId, { signal }),
    }),
};

export const syncMutations = {
  createImportJob: () =>
    mutationOptions({
      mutationFn: (body: ImportJobCreate) => operationsApi.createImportJob(body),
    }),
};
