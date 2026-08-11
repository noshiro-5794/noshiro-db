import { decodeApiPage } from '@/shared/api';
import type {
  ApiPage,
  CalendarSyncResult,
  IncrementalSyncResult,
  IncrementalSyncRunResult,
  QueuedTask,
  SubjectResyncResult,
  SyncJob,
  SyncTaskStatus,
} from '@/shared/api';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isString(value: unknown): value is string {
  return typeof value === 'string';
}

function isInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value);
}

function isNullableString(value: unknown) {
  return value === null || isString(value);
}

function isQueuedTask(value: unknown): value is QueuedTask {
  return (
    isRecord(value) &&
    isString(value['task_id']) &&
    isString(value['status']) &&
    (value['job_id'] === undefined || isString(value['job_id']))
  );
}

function isIncrementalSyncResult(value: unknown): value is IncrementalSyncResult {
  return (
    isRecord(value) &&
    isString(value['task_name']) &&
    isString(value['shard']) &&
    isInteger(value['start_id']) &&
    isInteger(value['end_id']) &&
    isInteger(value['processed_count']) &&
    isInteger(value['synced_count']) &&
    isInteger(value['skipped_count']) &&
    isInteger(value['failed_count']) &&
    (value['frontier_reached'] === undefined || typeof value['frontier_reached'] === 'boolean')
  );
}

function isCalendarSyncResult(value: unknown): value is CalendarSyncResult {
  return (
    isRecord(value) &&
    isInteger(value['weekday_count']) &&
    isInteger(value['item_count']) &&
    isInteger(value['synced_subject_count']) &&
    isInteger(value['failed_subject_count']) &&
    isInteger(value['detail_synced_count']) &&
    isInteger(value['detail_failed_count'])
  );
}

function isSubjectResyncResult(value: unknown): value is SubjectResyncResult {
  return (
    isRecord(value) &&
    isString(value['subject_id']) &&
    isInteger(value['bangumi_id']) &&
    isString(value['title']) &&
    isString(value['subject_type']) &&
    typeof value['episode_synced'] === 'boolean' &&
    isInteger(value['staff_count']) &&
    isInteger(value['character_count']) &&
    isInteger(value['related_subject_count'])
  );
}

function isSyncTaskStatus(value: unknown): value is SyncTaskStatus {
  return (
    isRecord(value) &&
    isString(value['task_name']) &&
    isString(value['shard']) &&
    isInteger(value['current_id']) &&
    isInteger(value['end_id']) &&
    isString(value['status']) &&
    isInteger(value['fail_count']) &&
    isString(value['updated_at'])
  );
}

function isSyncJob(value: unknown): value is SyncJob {
  return (
    isRecord(value) &&
    isString(value['id']) &&
    isString(value['job_type']) &&
    isString(value['status']) &&
    isString(value['celery_task_id']) &&
    isRecord(value['parameters']) &&
    (value['result'] === null || isRecord(value['result'])) &&
    isString(value['error']) &&
    isString(value['current_label']) &&
    isInteger(value['total_count']) &&
    isInteger(value['processed_count']) &&
    isInteger(value['synced_count']) &&
    isInteger(value['skipped_count']) &&
    isInteger(value['failed_count']) &&
    isNullableString(value['started_at']) &&
    isNullableString(value['finished_at']) &&
    isString(value['created_at']) &&
    isString(value['updated_at'])
  );
}

function invalidSyncResponse(): never {
  throw new TypeError('Invalid administrator sync response');
}

export function decodeIncrementalStatus(value: unknown): { tasks: SyncTaskStatus[] } {
  if (!isRecord(value) || !Array.isArray(value['tasks']) || !value['tasks'].every(isSyncTaskStatus)) {
    return invalidSyncResponse();
  }
  return { tasks: value['tasks'] };
}

export function decodeSyncJobPage(value: unknown): ApiPage<SyncJob> {
  return decodeApiPage(value, (item) => (isSyncJob(item) ? item : invalidSyncResponse()));
}

export function decodeIncrementalRunResult(value: unknown): IncrementalSyncRunResult {
  if (isQueuedTask(value)) return value;
  if (isIncrementalSyncResult(value)) return value;
  if (isRecord(value) && Array.isArray(value['results']) && value['results'].every(isIncrementalSyncResult)) {
    return { results: value['results'] };
  }
  return invalidSyncResponse();
}

export function decodeCalendarRunResult(value: unknown): QueuedTask | CalendarSyncResult {
  if (isQueuedTask(value)) return value;
  if (isCalendarSyncResult(value)) return value;
  return invalidSyncResponse();
}

export function decodeBangumiSubjectResult(
  value: unknown,
): (QueuedTask & { bangumi_id: number }) | SubjectResyncResult {
  if (isRecord(value)) {
    const bangumiId = value['bangumi_id'];
    if (isQueuedTask(value) && isInteger(bangumiId)) return { ...value, bangumi_id: bangumiId };
  }
  if (isSubjectResyncResult(value)) return value;
  return invalidSyncResponse();
}

export function decodeSubjectResyncResult(value: unknown): (QueuedTask & { subject_id: string }) | SubjectResyncResult {
  if (isRecord(value)) {
    const subjectId = value['subject_id'];
    if (isQueuedTask(value) && isString(subjectId)) return { ...value, subject_id: subjectId };
  }
  if (isSubjectResyncResult(value)) return value;
  return invalidSyncResponse();
}
