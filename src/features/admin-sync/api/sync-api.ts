import { api, encodePath } from '@/shared/api';
import {
  decodeBangumiSubjectResult,
  decodeCalendarRunResult,
  decodeIncrementalRunResult,
  decodeIncrementalStatus,
  decodeSubjectResyncResult,
  decodeSyncJobPage,
} from './sync-decoders';
import type {
  ApiPage,
  ApiRequestContext,
  CalendarSyncResult,
  IncrementalSyncRunResult,
  PageQuery,
  QueuedTask,
  SubjectResyncResult,
  SyncJob,
  SyncTaskStatus,
  UUID,
} from '@/shared/api';

export const syncApi = {
  getIncrementalStatus: (context: ApiRequestContext = {}) =>
    api.get<{ tasks: SyncTaskStatus[] }>('/api/sync/incremental/status/', {
      ...context,
      decode: decodeIncrementalStatus,
    }),

  getJobs: (query: PageQuery & { status?: string; job_type?: string } = {}, context: ApiRequestContext = {}) =>
    api.get<ApiPage<SyncJob>>('/api/sync/jobs/', { ...context, decode: decodeSyncJobPage, query }),

  runIncremental: (body: { run_async?: boolean; batch_size?: number; task_name?: string } = {}) =>
    api.post<IncrementalSyncRunResult, typeof body>('/api/sync/incremental/run/', body, {
      decode: decodeIncrementalRunResult,
    }),

  runCalendar: (body: { run_async?: boolean; sync_subject_details?: boolean } = {}) =>
    api.post<QueuedTask | CalendarSyncResult, typeof body>('/api/sync/calendar/run/', body, {
      decode: decodeCalendarRunResult,
    }),

  syncBangumiSubject: (body: { bangumi_id: number; run_async?: boolean }) =>
    api.post<(QueuedTask & { bangumi_id: number }) | SubjectResyncResult, typeof body>(
      '/api/sync/subjects/bangumi/',
      body,
      { decode: decodeBangumiSubjectResult },
    ),

  resyncSubject: (subjectId: UUID, body: { run_async?: boolean } = {}) =>
    api.post<(QueuedTask & { subject_id: UUID }) | SubjectResyncResult, typeof body>(
      `/api/sync/subjects/${encodePath(subjectId)}/resync/`,
      body,
      { decode: decodeSubjectResyncResult },
    ),
};
