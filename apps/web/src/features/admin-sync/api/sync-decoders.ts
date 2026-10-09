import { decodeApiPage } from '@/shared/api';
import type {
  ApiPage,
  CalendarSyncResult,
  ImportJob,
  IncrementalSyncResult,
  IncrementalSyncRunResult,
  QueuedTask,
  SubjectResyncResult,
  SyncCampaign,
  SyncCampaignSummary,
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

function isNonNegativeInteger(value: unknown): value is number {
  return isInteger(value) && value >= 0;
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function isNullableString(value: unknown) {
  return value === null || isString(value);
}

function isNullableDecimal(value: unknown) {
  return value === null || typeof value === 'string';
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

export function decodeImportJob(value: unknown): ImportJob {
  if (
    !isRecord(value) ||
    !isString(value['id']) ||
    !isString(value['provider']) ||
    !isNullableString(value['external_id']) ||
    !isString(value['status']) ||
    !isRecord(value['parameters']) ||
    (value['result'] !== null && !isRecord(value['result'])) ||
    !isNullableString(value['error']) ||
    !isRecord(value['progress']) ||
    !isString(value['progress']['current_label']) ||
    !isInteger(value['progress']['total']) ||
    !isInteger(value['progress']['processed']) ||
    !isInteger(value['progress']['synced']) ||
    !isInteger(value['progress']['skipped']) ||
    !isInteger(value['progress']['failed']) ||
    !isString(value['created_at']) ||
    !isNullableString(value['started_at']) ||
    !isNullableString(value['finished_at']) ||
    !isString(value['updated_at'])
  ) {
    throw new TypeError('Invalid import job response');
  }

  return {
    id: value['id'],
    provider: value['provider'],
    external_id: value['external_id'],
    status: value['status'],
    parameters: value['parameters'],
    result: value['result'],
    error: value['error'],
    progress: {
      current_label: value['progress']['current_label'],
      total: value['progress']['total'],
      processed: value['progress']['processed'],
      synced: value['progress']['synced'],
      skipped: value['progress']['skipped'],
      failed: value['progress']['failed'],
    },
    created_at: value['created_at'],
    started_at: value['started_at'],
    finished_at: value['finished_at'],
    updated_at: value['updated_at'],
  };
}

function isSyncCampaign(value: unknown): value is SyncCampaign {
  if (
    !isRecord(value) ||
    !isString(value['id']) ||
    !isString(value['provider_slug']) ||
    !isString(value['campaign_type']) ||
    !isString(value['status']) ||
    !isString(value['ai_mode']) ||
    !isRecord(value['parameters']) ||
    !isNonNegativeInteger(value['total_items']) ||
    !isNonNegativeInteger(value['processed_items']) ||
    !isNonNegativeInteger(value['synced_items']) ||
    !isNonNegativeInteger(value['skipped_items']) ||
    !isNonNegativeInteger(value['failed_items']) ||
    !(value['quality_report'] === null || isRecord(value['quality_report'])) ||
    !isNullableDecimal(value['cost']) ||
    !isString(value['error']) ||
    !isNullableString(value['heartbeat_at']) ||
    !isNullableString(value['next_run_at']) ||
    !isString(value['created_at']) ||
    !isNullableString(value['started_at']) ||
    !isNullableString(value['finished_at']) ||
    !isString(value['updated_at']) ||
    !isRecord(value['progress'])
  ) {
    return false;
  }

  const progress = value['progress'];
  return (
    (progress['percent'] === null || isFiniteNumber(progress['percent'])) &&
    isNonNegativeInteger(progress['queued']) &&
    isNonNegativeInteger(progress['running']) &&
    isNonNegativeInteger(progress['succeeded']) &&
    isNonNegativeInteger(progress['failed']) &&
    isNonNegativeInteger(progress['retry_waiting']) &&
    (progress['throughput_items_per_second'] === null || isFiniteNumber(progress['throughput_items_per_second'])) &&
    (progress['eta_seconds'] === null || isNonNegativeInteger(progress['eta_seconds']))
  );
}

export function decodeSyncCampaign(value: unknown): SyncCampaign {
  if (!isSyncCampaign(value)) {
    throw new TypeError('Invalid sync campaign response');
  }
  return value;
}

export function decodeSyncCampaignList(value: unknown): SyncCampaign[] {
  if (!Array.isArray(value) || !value.every(isSyncCampaign)) {
    throw new TypeError('Invalid sync campaign list response');
  }
  return value;
}

function isNumberMap(value: unknown): value is Record<string, number> {
  return isRecord(value) && Object.values(value).every(isNonNegativeInteger);
}

export function decodeSyncCampaignSummary(value: unknown): SyncCampaignSummary {
  if (
    !isRecord(value) ||
    !isNumberMap(value['campaigns_by_status']) ||
    !isNumberMap(value['campaigns_by_provider']) ||
    !isNonNegativeInteger(value['stale_leases']) ||
    !isNonNegativeInteger(value['queued_items']) ||
    !isNonNegativeInteger(value['failed_items']) ||
    !isNonNegativeInteger(value['pending_ai_claims'])
  ) {
    throw new TypeError('Invalid sync campaign summary response');
  }
  return {
    campaigns_by_status: value['campaigns_by_status'],
    campaigns_by_provider: value['campaigns_by_provider'],
    stale_leases: value['stale_leases'],
    queued_items: value['queued_items'],
    failed_items: value['failed_items'],
    pending_ai_claims: value['pending_ai_claims'],
  };
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
