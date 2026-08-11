import { mutationOptions, queryOptions } from '@tanstack/react-query';
import { syncApi } from '../api/sync-api';
import type { PageQuery, UUID } from '@/shared/api';

export const syncQueryKeys = {
  all: ['sync'] as const,
  incrementalStatus: () => [...syncQueryKeys.all, 'incremental-status'] as const,
  jobs: () => [...syncQueryKeys.all, 'jobs'] as const,
  jobsList: (query: PageQuery & { status?: string; job_type?: string }) => [...syncQueryKeys.jobs(), query] as const,
};

export const syncQueries = {
  incrementalStatus: () =>
    queryOptions({
      queryKey: syncQueryKeys.incrementalStatus(),
      queryFn: ({ signal }) => syncApi.getIncrementalStatus({ signal }),
    }),

  jobs: (query: PageQuery & { status?: string; job_type?: string } = {}) =>
    queryOptions({
      queryKey: syncQueryKeys.jobsList(query),
      queryFn: ({ signal }) => syncApi.getJobs(query, { signal }),
    }),
};

export const syncMutations = {
  runIncremental: () =>
    mutationOptions({
      mutationFn: (body: { run_async?: boolean; batch_size?: number; task_name?: string } = {}) =>
        syncApi.runIncremental(body),
    }),

  runCalendar: () =>
    mutationOptions({
      mutationFn: (body: { run_async?: boolean; sync_subject_details?: boolean } = {}) => syncApi.runCalendar(body),
    }),

  syncBangumiSubject: () =>
    mutationOptions({
      mutationFn: (body: { bangumi_id: number; run_async?: boolean }) => syncApi.syncBangumiSubject(body),
    }),

  resyncSubject: () =>
    mutationOptions({
      mutationFn: ({ subjectId, body = {} }: { subjectId: UUID; body?: { run_async?: boolean } }) =>
        syncApi.resyncSubject(subjectId, body),
    }),
};
