import type { ISODateString, OpenString, UUID } from './common';
import type { SubjectType } from './subject';

export type ImportJobProvider = 'bangumi' | 'vndb' | OpenString;
export type ImportJobStatus = 'queued' | 'running' | 'succeeded' | 'failed' | OpenString;

export type ImportJobProgress = {
  current_label: string;
  total: number;
  processed: number;
  synced: number;
  skipped: number;
  failed: number;
};

export type ImportJob = {
  id: UUID;
  provider: ImportJobProvider;
  external_id: string | null;
  status: ImportJobStatus;
  parameters: Record<string, unknown>;
  result: Record<string, unknown> | null;
  error: string | null;
  progress: ImportJobProgress;
  created_at: ISODateString;
  started_at: ISODateString | null;
  finished_at: ISODateString | null;
  updated_at: ISODateString;
};

export type ImportJobCreate = {
  provider: 'vndb';
  external_id: string;
  include_related?: boolean;
};

export type SyncTaskStatus = {
  task_name: string;
  shard: string;
  current_id: number;
  end_id: number;
  status: string;
  fail_count: number;
  updated_at: ISODateString;
};

export type QueuedTask = {
  task_id: string;
  status: 'queued' | OpenString;
  job_id?: UUID;
};

export type IncrementalSyncResult = {
  task_name: string;
  shard: string;
  start_id: number;
  end_id: number;
  processed_count: number;
  synced_count: number;
  skipped_count: number;
  failed_count: number;
  frontier_reached?: boolean;
};

export type CalendarSyncResult = {
  weekday_count: number;
  item_count: number;
  synced_subject_count: number;
  failed_subject_count: number;
  detail_synced_count: number;
  detail_failed_count: number;
};

export type IncrementalSyncRunResult =
  | QueuedTask
  | IncrementalSyncResult
  | {
      results: IncrementalSyncResult[];
    };

export type SyncJob = {
  id: UUID;
  job_type: 'subject_bangumi' | 'subject_resync' | 'calendar' | 'incremental' | OpenString;
  status: 'queued' | 'running' | 'succeeded' | 'failed' | OpenString;
  celery_task_id: string;
  parameters: Record<string, unknown>;
  result: Record<string, unknown> | null;
  error: string;
  current_label: string;
  total_count: number;
  processed_count: number;
  synced_count: number;
  skipped_count: number;
  failed_count: number;
  started_at: ISODateString | null;
  finished_at: ISODateString | null;
  created_at: ISODateString;
  updated_at: ISODateString;
};

export type SubjectResyncResult = {
  subject_id: UUID;
  bangumi_id: number;
  title: string;
  subject_type: SubjectType;
  episode_synced: boolean;
  staff_count: number;
  character_count: number;
  related_subject_count: number;
};
