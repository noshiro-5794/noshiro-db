import { api } from '@/shared/api';
import { encodePath } from '@/shared/api';
import type {
  ApiPage,
  CalendarSyncResult,
  IncrementalSyncResult,
  PageQuery,
  QueuedTask,
  SubjectResyncResult,
  SyncJob,
  SyncTaskStatus,
  UUID,
} from '@/shared/api';

export const syncApi = {
  getIncrementalStatus: () => api.get<{ tasks: SyncTaskStatus[] }>('/api/sync/incremental/status/'),

  getJobs: (query: PageQuery & { status?: string; job_type?: string } = {}) =>
    api.get<ApiPage<SyncJob>>('/api/sync/jobs/', { query }),

  runIncremental: (body: { run_async?: boolean; batch_size?: number; task_name?: string } = {}) =>
    api.post<QueuedTask | { results: IncrementalSyncResult[] }, typeof body>('/api/sync/incremental/run/', body),

  runCalendar: (body: { run_async?: boolean; sync_subject_details?: boolean } = {}) =>
    api.post<QueuedTask | CalendarSyncResult, typeof body>('/api/sync/calendar/run/', body),

  syncBangumiSubject: (body: { bangumi_id: number; run_async?: boolean }) =>
    api.post<(QueuedTask & { bangumi_id: number }) | SubjectResyncResult, typeof body>(
      '/api/sync/subjects/bangumi/',
      body,
    ),

  resyncSubject: (subjectId: UUID, body: { run_async?: boolean } = {}) =>
    api.post<(QueuedTask & { subject_id: UUID }) | SubjectResyncResult, typeof body>(
      `/api/sync/subjects/${encodePath(subjectId)}/resync/`,
      body,
    ),
};
