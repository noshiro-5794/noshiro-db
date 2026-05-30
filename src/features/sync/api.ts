import { api } from '@/lib/api/client';
import { encodePath } from '@/lib/api/path';
import type { IncrementalSyncResult, QueuedTask, SubjectResyncResult, SyncTaskStatus, UUID } from '@/lib/api/types';

export const syncApi = {
  getIncrementalStatus: () => api.get<{ tasks: SyncTaskStatus[] }>('/api/sync/incremental/status/'),

  runIncremental: (body: { run_async?: boolean; batch_size?: number; task_name?: string } = {}) =>
    api.post<QueuedTask | { results: IncrementalSyncResult[] }, typeof body>('/api/sync/incremental/run/', body),

  runCalendar: (body: { run_async?: boolean; sync_subject_details?: boolean } = {}) =>
    api.post<QueuedTask | Record<string, unknown>, typeof body>('/api/sync/calendar/run/', body),

  resyncSubject: (subjectId: UUID, body: { run_async?: boolean } = {}) =>
    api.post<(QueuedTask & { subject_id: UUID }) | SubjectResyncResult, typeof body>(
      `/api/sync/subjects/${encodePath(subjectId)}/resync/`,
      body,
    ),
};
